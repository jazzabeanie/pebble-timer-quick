"""
Shared fixtures for functional tests.

Provides emulator setup, screenshot helpers, and button simulation.
"""

import logging
import os
import shutil
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest
from PIL import Image

# Configure module logger
logger = logging.getLogger(__name__)

# Add pebble tool to path
CONDA_ENV = Path(__file__).parent.parent.parent / "conda-env"
PEBBLE_CMD = CONDA_ENV / "bin" / "pebble"
if not PEBBLE_CMD.exists():
    PEBBLE_CMD = Path("pebble")

# Make pebble_tool/libpebble2 importable in-process (emulator info, persist dirs)
sys.path.insert(0, str(CONDA_ENV / "lib" / "python3.10" / "site-packages"))

PYTHON_CMD = CONDA_ENV / "bin" / "python"
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Emulator platforms
PLATFORMS = ["aplite", "basalt", "chalk", "diorite", "emery", "gabbro"]

# Button constants (from libpebble2)
class Button:
    BACK = 1
    UP = 2
    SELECT = 4
    DOWN = 8


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--platform",
        action="store",
        default=None,
        choices=PLATFORMS,
        help="Specific platform to test (default: run on all platforms)"
    )
    parser.addoption(
        "--save-screenshots",
        action="store_true",
        default=False,
        help="Save screenshots for debugging"
    )


def pytest_generate_tests(metafunc):
    """Parameterize tests by platform if not specified."""
    if "platform" in metafunc.fixturenames:
        platform_opt = metafunc.config.getoption("--platform")
        if platform_opt:
            metafunc.parametrize("platform", [platform_opt])
        else:
            metafunc.parametrize("platform", PLATFORMS)


def pytest_sessionfinish(session, exitstatus):
    """Stop log streams and kill all emulators at end of session."""
    for platform, stream in list(_LogStream._instances.items()):
        stream.shutdown()
    # pkill any emulator processes (ours or orphaned)
    subprocess.run(["pkill", "-f", "qemu-pebble"], capture_output=True)
    subprocess.run(["pkill", "-f", "pypkjs"], capture_output=True)


class EmulatorHelper:
    """Helper class for interacting with the Pebble emulator."""

    def __init__(self, platform: str, save_screenshots: bool = False):
        self.platform = platform
        self.save_screenshots = save_screenshots
        self.screenshot_dir = Path(__file__).parent / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        self._transport = None
        self._pypkjs_port = None
        self._ws = None  # WebSocket connection to pypkjs for button presses
        self._current_test_name = None  # Current test name for screenshot prefixing
        self.last_init_state = None  # TEST_STATE:init dict captured by the last install()

    def set_test_name(self, test_name: str):
        """Set the current test name for screenshot prefixing."""
        self._current_test_name = test_name

    def _run_pebble(self, *args, check=True, capture_output=True, timeout=120):
        """Run a pebble command."""
        cmd = [str(PEBBLE_CMD)] + list(args)
        env = os.environ.copy()
        env["PEBBLE_EMULATOR"] = self.platform
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=timeout,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
        return result

    def _kill_platform_emulator(self):
        """Kill the qemu/pypkjs processes for THIS platform only.

        `pebble kill` kills every emulator of every platform, which breaks
        emulators other fixtures are still using. Kill by pid instead.
        """
        try:
            from pebble_tool.sdk.emulator import get_all_emulator_info
            info = get_all_emulator_info().get(self.platform, {})
        except Exception:
            info = {}
        for version in info.values():
            for proc in ("qemu", "pypkjs", "websockify"):
                pid = version.get(proc, {}).get("pid")
                if pid:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
        # Drop our dead connections
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._pypkjs_port = None

    def wipe(self):
        """Wipe THIS platform's emulator state for a fresh start.

        `pebble wipe` deletes the persist directories of every platform, so
        wipe only our own platform's directory instead.
        """
        logger.debug(f"[{self.platform}] Wiping emulator state")
        # Kill any existing emulator first - this is required so the wipe takes effect
        self._kill_platform_emulator()
        time.sleep(1)  # Give processes time to fully exit
        try:
            from pebble_tool.sdk import get_sdk_persist_dir
            persist_dir = get_sdk_persist_dir(self.platform)
            shutil.rmtree(persist_dir, ignore_errors=True)
            get_sdk_persist_dir(self.platform)  # recreate empty dir
        except Exception as e:
            logger.warning(f"[{self.platform}] Scoped wipe failed ({e}); falling back to pebble wipe")
            self._run_pebble("wipe", check=False)
        logger.debug(f"[{self.platform}] Wipe complete")

    def build(self):
        """Build the application."""
        result = self._run_pebble("build", timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Build failed:\n{result.stderr}")

    def install(self):
        """Install and launch the app on the emulator.

        Blocks until the app's launch is *observed* in the logs (the app emits
        a TEST_STATE:init line from prv_initialize). This both confirms the
        app is actually running and that the log pipeline is delivering lines,
        so tests fail fast with a clear error instead of timing out later on
        empty log captures. The captured init state is stored in
        self.last_init_state so fixtures can detect leaked state.
        """
        logger.info(f"[{self.platform}] Installing app on emulator")
        # Capture from before the install so the launch's init line isn't missed
        barrier = LogCapture(self.platform)
        barrier.start()
        try:
            # Install will start the emulator if needed
            self._run_install_with_retry()
            if self._ws is None:
                self._connect_transport()

            init = barrier.wait_for_state(event="init", timeout=8.0)
            if init is None:
                # The log stream may have connected after the app launched
                # (first boot) and missed the init line. Force a reconnect and
                # relaunch the app once, which re-emits init.
                logger.warning(
                    f"[{self.platform}] App launch not seen in logs; "
                    f"reconnecting log stream and relaunching"
                )
                _LogStream.get(self.platform).force_reconnect()
                self._run_install_with_retry()
                init = barrier.wait_for_state(event="init", timeout=10.0)
            self.last_init_state = init
            if init is None:
                # Kill the emulator so the next install cold-boots instead of
                # inheriting a broken instance.
                lines = len(barrier.get_all_logs())
                self.kill()
                raise RuntimeError(
                    f"[{self.platform}] App launch not observed in logs after "
                    f"reinstall ({lines} log lines captured). Emulator killed "
                    f"for a cold boot on the next install."
                )
        finally:
            barrier.stop()
        logger.info(f"[{self.platform}] App installed and launch confirmed (init: {self.last_init_state})")

    def _run_install_with_retry(self, attempts: int = 3):
        """Run `pebble install`, retrying after a scoped kill on failure.

        A cold emulator boot can take longer than the pebble tool's hard-coded
        5s connect window (10 x 0.5s in ManagedEmulatorTransport.connect),
        which surfaces as "Connection refused". Kill this platform's emulator
        and retry so a slow boot doesn't error a whole module's fixture.
        """
        last_error = None
        for attempt in range(attempts):
            try:
                result = self._run_pebble(
                    "install",
                    f"--emulator={self.platform}",
                    timeout=120,
                )
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                last_error = e
            else:
                if result.returncode == 0:
                    return
                last_error = RuntimeError(f"Install failed:\n{result.stderr}")
            if attempt < attempts - 1:
                logger.warning(
                    f"[{self.platform}] Install attempt {attempt + 1} failed "
                    f"({last_error}); killing emulator and retrying"
                )
                self._kill_platform_emulator()
                time.sleep(2)
        raise RuntimeError(
            f"Install failed after {attempts} attempts: {last_error}"
        )

    def _connect_transport(self):
        """Connect to pypkjs WebSocket for button presses."""
        from pebble_tool.sdk.emulator import get_emulator_info

        info = get_emulator_info(self.platform)
        if info is None:
            raise RuntimeError(f"Could not get emulator info for {self.platform}")

        self._pypkjs_port = info["pypkjs"]["port"]
        logger.debug(f"[{self.platform}] Got pypkjs port {self._pypkjs_port}")

        # Establish WebSocket connection to pypkjs
        self._ensure_websocket()

        # Make sure the log stream for this platform is running; it maintains
        # its own connection and reconnects as emulators come and go.
        _LogStream.get(self.platform)

    def _ensure_websocket(self):
        """Ensure we have an open WebSocket connection to pypkjs."""
        from websocket import create_connection, WebSocketException

        # Close existing connection if any
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        # Create new WebSocket connection
        try:
            self._ws = create_connection(f"ws://localhost:{self._pypkjs_port}/", timeout=10)
            logger.debug(f"[{self.platform}] Established WebSocket to pypkjs port {self._pypkjs_port}")
        except Exception as e:
            self._ws = None
            raise RuntimeError(f"Failed to connect to pypkjs WebSocket port {self._pypkjs_port}: {e}")

    def _send_button(self, button: int, retries: int = 2):
        """Send a button press to the emulator via pypkjs WebSocket."""
        from websocket import WebSocketException

        # QEMU protocol 8 = QemuButton
        # Format: [0x0b (qemu_command opcode), 0x08 (button protocol), button_state]
        QEMU_COMMAND_OPCODE = 0x0b
        BUTTON_PROTOCOL = 0x08

        press_data = bytearray([QEMU_COMMAND_OPCODE, BUTTON_PROTOCOL, button])
        release_data = bytearray([QEMU_COMMAND_OPCODE, BUTTON_PROTOCOL, 0])

        for attempt in range(retries + 1):
            # Ensure we have a WebSocket connection
            if self._ws is None:
                if self._pypkjs_port is None:
                    self._connect_transport()
                else:
                    self._ensure_websocket()

            try:
                logger.debug(f"[{self.platform}] Attempt {attempt+1}: sending button {button} via WebSocket")
                # Send press
                self._ws.send_binary(press_data)
                time.sleep(0.1)  # Hold button briefly
                # Send release
                self._ws.send_binary(release_data)
                logger.debug(f"[{self.platform}] Button {button} sent successfully")
                break  # Success
            except (WebSocketException, ConnectionError, OSError, BrokenPipeError) as e:
                logger.warning(f"[{self.platform}] Attempt {attempt+1} failed: {e}")
                # Close broken connection
                if self._ws is not None:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

                if attempt < retries:
                    # Wait and reconnect
                    time.sleep(1)
                    self._connect_transport()
                else:
                    raise RuntimeError(
                        f"Failed to send button after {retries + 1} attempts: {e}"
                    )

        # Wait for display to update
        time.sleep(0.3)

    def hold_button(self, button: int, retries: int = 2):
        """Holds a button down without releasing it via pypkjs WebSocket."""
        from websocket import WebSocketException

        QEMU_COMMAND_OPCODE = 0x0b
        BUTTON_PROTOCOL = 0x08
        press_data = bytearray([QEMU_COMMAND_OPCODE, BUTTON_PROTOCOL, button])

        for attempt in range(retries + 1):
            # Ensure we have a WebSocket connection
            if self._ws is None:
                if self._pypkjs_port is None:
                    self._connect_transport()
                else:
                    self._ensure_websocket()

            try:
                self._ws.send_binary(press_data)
                logger.debug(f"[{self.platform}] Button {button} held")
                break
            except (WebSocketException, ConnectionError, OSError, BrokenPipeError) as e:
                logger.warning(f"[{self.platform}] hold_button attempt {attempt+1} failed: {e}")
                if self._ws is not None:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

                if attempt < retries:
                    time.sleep(1)
                    self._connect_transport()
                else:
                    raise RuntimeError(
                        f"Failed to send button press after {retries + 1} attempts: {e}"
                    )
        time.sleep(0.2)

    def release_buttons(self, retries: int = 2):
        """Releases all currently held buttons via pypkjs WebSocket."""
        from websocket import WebSocketException

        QEMU_COMMAND_OPCODE = 0x0b
        BUTTON_PROTOCOL = 0x08
        release_data = bytearray([QEMU_COMMAND_OPCODE, BUTTON_PROTOCOL, 0])

        for attempt in range(retries + 1):
            # Ensure we have a WebSocket connection
            if self._ws is None:
                if self._pypkjs_port is None:
                    self._connect_transport()
                else:
                    self._ensure_websocket()

            try:
                self._ws.send_binary(release_data)
                logger.debug(f"[{self.platform}] Buttons released")
                break
            except (WebSocketException, ConnectionError, OSError, BrokenPipeError) as e:
                logger.warning(f"[{self.platform}] release_buttons attempt {attempt+1} failed: {e}")
                if self._ws is not None:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

                if attempt < retries:
                    time.sleep(1)
                    self._connect_transport()
                else:
                    raise RuntimeError(
                        f"Failed to send button release after {retries + 1} attempts: {e}"
                    )
        time.sleep(0.2)

    def press_back(self):
        """Press the Back button."""
        logger.debug(f"[{self.platform}] Pressing BACK button")
        self._send_button(Button.BACK)

    def press_up(self):
        """Press the Up button."""
        logger.debug(f"[{self.platform}] Pressing UP button")
        self._send_button(Button.UP)

    def press_select(self):
        """Press the Select button."""
        logger.debug(f"[{self.platform}] Pressing SELECT button")
        self._send_button(Button.SELECT)

    def press_down(self):
        """Press the Down button."""
        logger.debug(f"[{self.platform}] Pressing DOWN button")
        self._send_button(Button.DOWN)

    def press_up_back_chord(self):
        """Press the Up+Back chord (Up held first, then Back) used for voice rename.

        The QEMU button protocol uses an absolute bitmask, so each call sets the
        full set of currently-pressed buttons. Holding Up sets s_up_held; pressing
        and releasing Back while Up stays held fires the Back single-click handler
        with the chord active.
        """
        logger.debug(f"[{self.platform}] Pressing UP+BACK chord")
        self.hold_button(Button.UP)                  # Up down -> s_up_held = true
        self.hold_button(Button.UP | Button.BACK)    # Back down while Up held
        self.hold_button(Button.UP)                  # Back up -> Back single click fires
        self.release_buttons()                       # Up up -> s_up_held = false

    def set_bt_connection(self, connected: bool):
        """Set the emulated Bluetooth (phone app) connection state."""
        state = "yes" if connected else "no"
        logger.debug(f"[{self.platform}] Setting BT connection: {state}")
        self._run_pebble(
            "emu-bt-connection",
            f"--connected={state}",
            f"--emulator={self.platform}",
            check=False,
        )
        time.sleep(0.5)

    def send_app_message_int(self, key: int, value: int):
        """Send an AppMessage with a single signed-int key (used to set settings)."""
        logger.debug(f"[{self.platform}] Sending app message {key}={value}")
        self._run_pebble(
            "send-app-message",
            f"--emulator={self.platform}",
            "--int", f"{key}={value}",
            check=False,
        )
        time.sleep(0.5)

    def open_app_via_menu(self):
        """
        Re-open the app using the install command.
        
        This is more reliable than menu navigation which can be flaky
        if the emulator lands on the wrong screen.
        """
        logger.info(f"[{self.platform}] Opening app via install (preserving state)")
        self.install()
        logger.info(f"[{self.platform}] App opened via install")

    def screenshot(self, name: str = None) -> Image.Image:
        """Take a screenshot and return as PIL Image."""
        # Generate filename with test name prefix if available
        if name:
            if self._current_test_name:
                filename = self.screenshot_dir / f"{self._current_test_name}_{self.platform}_{name}.png"
            else:
                filename = self.screenshot_dir / f"{self.platform}_{name}.png"
        else:
            filename = self.screenshot_dir / f"{self.platform}_temp.png"

        logger.debug(f"[{self.platform}] Taking screenshot: {filename.name}")

        # Take screenshot using pebble command
        result = self._run_pebble(
            "screenshot",
            str(filename),
            f"--emulator={self.platform}",
            "--no-open",
        )
        if result.returncode != 0:
            raise RuntimeError(f"Screenshot failed:\n{result.stderr}")

        # Load and return image
        img = Image.open(filename)

        # Delete temp file if not saving
        if not self.save_screenshots and not name:
            filename.unlink()

        return img

    def kill(self):
        """Kill this platform's emulator (other platforms are left running)."""
        logger.debug(f"[{self.platform}] Killing emulator")
        self._kill_platform_emulator()
        logger.debug(f"[{self.platform}] Emulator killed")


@pytest.fixture(scope="session")
def build_app():
    """Session-scoped fixture to build the app once per test session."""
    helper = EmulatorHelper("basalt")  # Platform doesn't matter for build
    helper.build()
    return True


def _fresh_start_cycle(helper: "EmulatorHelper"):
    """Wipe and reinstall so the app starts in a fresh ControlModeNew.

    First install: fresh start. The app immediately claims slot 0
    (timer_count=1), which would cause the Timer List to appear on re-launch.
    Hold Down to delete slot 0 and exit, leaving timer_count=0 persisted.
    Second install: persisted_count=0 → no Timer List, fresh ControlModeNew.
    """
    helper.wipe()
    helper.install()
    time.sleep(1)
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    time.sleep(0.5)
    helper.install()


def _init_state_is_fresh(init: Optional[dict]) -> bool:
    """True if a TEST_STATE:init dict looks like a fresh ControlModeNew start."""
    if init is None:
        # Launch was confirmed some other way; don't second-guess it.
        return True
    return init.get("m") == "New" and init.get("t") == "0:00"


@pytest.fixture
def emulator(request, platform, build_app):
    """Fixture that provides a configured emulator helper with fresh state."""
    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    _fresh_start_cycle(helper)

    yield helper

    helper.kill()


@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """
    Module-scoped fixture that launches the emulator once per platform.

    The fixture performs a "warm-up" cycle:
    1. Wipe storage, install app
    2. Long press Down to quit the app (sets app state for next launch)

    The app is left closed after warmup. The _reset_app_between_tests autouse
    fixture handles opening/closing the app before/after each test.
    """
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")

    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Warm-up cycle to clear any stale state and set initial persist state
    logger.info(f"[{platform}] Starting warm-up cycle to clear stale state")
    helper.wipe()
    helper.install()
    logger.info(f"[{platform}] Waiting for emulator to stabilize (2s)")
    time.sleep(2)  # Allow emulator to stabilize

    # Long press Down button to quit the app - this sets the app's persist state
    # (reset_on_init=true ensures the timer is reset on next launch)
    logger.info(f"[{platform}] Holding down button to quit app and set persist state")
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    logger.info(f"[{platform}] App quit via long press, persist state set")
    time.sleep(0.5)

    logger.info(f"[{platform}] Emulator ready for tests")

    yield helper

    # Teardown: kill emulator
    logger.info(f"[{platform}] Tearing down - killing emulator")
    helper.kill()


@pytest.fixture(autouse=True)
def _setup_test_environment(request):
    """
    Auto-use fixture that runs before/after each test.

    Before each test:
    - Sets the test name on the emulator helper (for screenshot naming)
    - Opens the app via menu navigation

    After each test:
    - Quits the app via long-press down button
    - Clears the test name
    """
    test_name = request.node.name
    emulator_helper = None

    # Only fetch a fixture if the test explicitly declared it, to avoid
    # parameter-resolution errors with module-scoped parameterized fixtures.
    for fixture_name in ['persistent_emulator', 'emulator']:
        if fixture_name in request.fixturenames:
            emulator_helper = request.getfixturevalue(fixture_name)
            break

    if emulator_helper is not None:
        # Set test name for screenshot prefixing
        emulator_helper.set_test_name(test_name)
        logger.info(f"[{emulator_helper.platform}] Opening app for test: {test_name}")
        if fixture_name == 'persistent_emulator':
            # persistent_emulator closes the app after each test, so we need
            # to re-open it before the next test.
            emulator_helper.open_app_via_menu()
            time.sleep(0.5)
        # (emulator fixture already opened the app via its fresh-start cycle;
        # install() confirmed the launch in the logs, so no warm-up sleep is
        # needed and the test body gets the full 3s ControlModeNew window.)

        # A previous test may have leaked persisted state (e.g. its teardown
        # quit failed in an unexpected control mode). If the app didn't come
        # up in a fresh ControlModeNew, recover with a full wipe cycle rather
        # than letting the leak cascade through the rest of the module.
        if not _init_state_is_fresh(emulator_helper.last_init_state):
            logger.warning(
                f"[{emulator_helper.platform}] App started with leaked state "
                f"(init: {emulator_helper.last_init_state}); recovering with a "
                f"fresh wipe cycle before test: {test_name}"
            )
            _fresh_start_cycle(emulator_helper)
            if not _init_state_is_fresh(emulator_helper.last_init_state):
                pytest.fail(
                    f"[{emulator_helper.platform}] Could not reach a fresh app "
                    f"state even after a wipe cycle "
                    f"(init: {emulator_helper.last_init_state})"
                )

    yield

    if emulator_helper is not None:
        # Quit the app after the test via long-press Down, which sets
        # reset_on_init=true so the next test starts with a fresh timer.
        # After quitting, the Pebble returns to the launcher with the
        # app still selected, ready for open_app_via_menu().
        logger.info(f"[{emulator_helper.platform}] Quitting app after test: {test_name}")
        emulator_helper.hold_button(Button.DOWN)
        time.sleep(1)
        emulator_helper.release_buttons()
        time.sleep(0.5)
        # Clear test name
        emulator_helper.set_test_name(None)


####################################################################################################
# Log Capture for Test Assertions
#
# These classes and functions enable functional tests to verify app state by parsing
# structured log output instead of relying on OCR. See ralph/specs/test-logging.md.
#

import re
import threading
import queue


class _LogStream:
    """Reads app logs for one emulator platform directly from pypkjs.

    Replaces the old `pebble logs` subprocess reader, which broke whenever an
    emulator was killed/restarted mid-session (and could even boot stray
    emulators of its own via the pebble tool's managed transport).

    This connects a dedicated WebSocket to the platform's pypkjs — the same
    transport the button-press helper uses — enables app log shipping, and
    decodes AppLogMessage packets (endpoint 2006) itself. The connection is
    re-established automatically whenever the emulator restarts, and it never
    spawns processes. Decoded lines are fanned out to every attached
    LogCapture sink.
    """

    _instances: dict = {}
    _class_lock = threading.Lock()

    APP_LOG_ENDPOINT = 2006  # AppLogMessage / AppLogShippingControl
    RELAY_FROM_WATCH = 0x00
    RELAY_TO_WATCH = 0x01
    CONNECTION_STATUS = 0x07

    @classmethod
    def get(cls, platform: str) -> '_LogStream':
        with cls._class_lock:
            if platform not in cls._instances:
                stream = cls(platform)
                stream._start()
                cls._instances[platform] = stream
            return cls._instances[platform]

    def __init__(self, platform: str):
        self.platform = platform
        self._ws = None
        self._buf = b""  # partial pebble-protocol packet spanning relay frames
        self._thread: Optional[threading.Thread] = None
        self._sinks: list = []
        self._sink_lock = threading.Lock()
        self._running = False
        self._wake = threading.Event()

    def _start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.debug(f"[{self.platform}] Log stream started")

    def shutdown(self):
        self._running = False
        self._wake.set()
        self._close_ws()

    def force_reconnect(self):
        """Drop the current connection; the reader thread reconnects promptly."""
        self._close_ws()
        self._wake.set()

    def attach(self, capture: 'LogCapture'):
        with self._sink_lock:
            if capture not in self._sinks:
                self._sinks.append(capture)
        self._wake.set()

    def detach(self, capture: 'LogCapture'):
        with self._sink_lock:
            if capture in self._sinks:
                self._sinks.remove(capture)

    def _close_ws(self):
        ws = self._ws
        self._ws = None
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    def _send_shipping_control(self, enable: bool = True):
        """Ask the watch to ship app logs (endpoint 2006, 1-byte payload)."""
        payload = bytes([1 if enable else 0])
        packet = struct.pack(">HH", len(payload), self.APP_LOG_ENDPOINT) + payload
        self._ws.send_binary(bytes([self.RELAY_TO_WATCH]) + packet)

    def _try_connect(self) -> bool:
        """Connect to the platform's current pypkjs, if one is running."""
        try:
            from pebble_tool.sdk.emulator import get_emulator_info
            info = get_emulator_info(self.platform)
        except Exception:
            info = None
        if not info:
            return False
        port = info["pypkjs"]["port"]
        try:
            from websocket import create_connection
            ws = create_connection(f"ws://localhost:{port}/", timeout=5)
            ws.settimeout(1.0)
        except Exception:
            return False
        self._ws = ws
        self._buf = b""  # partial pebble-protocol packet spanning relay frames
        try:
            self._send_shipping_control(True)
        except Exception:
            self._close_ws()
            return False
        logger.info(f"[{self.platform}] Log stream connected to pypkjs port {port}")
        return True

    def _run(self):
        from websocket import WebSocketTimeoutException

        while self._running:
            if self._ws is None:
                if not self._try_connect():
                    # No emulator (or not ready yet); retry shortly. attach()
                    # and force_reconnect() wake us immediately.
                    self._wake.wait(timeout=0.5)
                    self._wake.clear()
                    continue
            try:
                data = self._ws.recv()
            except WebSocketTimeoutException:
                continue  # quiet connection is normal between tests
            except Exception:
                self._close_ws()
                continue
            if not isinstance(data, bytes) or len(data) < 2:
                continue
            opcode = data[0]
            if opcode == self.CONNECTION_STATUS:
                # Watch (re)connected to pypkjs: re-enable log shipping
                if data[1] == 0xFF:
                    try:
                        self._send_shipping_control(True)
                    except Exception:
                        self._close_ws()
                continue
            if opcode != self.RELAY_FROM_WATCH:
                continue
            # A relay frame can contain several pebble-protocol packets, and a
            # packet can span frames — accumulate and split like libpebble2's
            # PebbleConnection does.
            self._buf += data[1:]
            while len(self._buf) >= 4:
                length, endpoint = struct.unpack_from(">HH", self._buf, 0)
                if length > 8192:
                    # Desynced; drop the buffer rather than stalling forever.
                    logger.warning(f"[{self.platform}] Log stream desync (len={length}); resetting buffer")
                    self._buf = b""
                    break
                if len(self._buf) < 4 + length:
                    break  # partial packet; wait for the next frame
                body = self._buf[4:4 + length]
                self._buf = self._buf[4 + length:]
                if endpoint == self.APP_LOG_ENDPOINT:
                    self._handle_app_log(body)

    def _handle_app_log(self, body: bytes):
        """Decode an AppLogMessage body and fan the line out to sinks."""
        # AppLogMessage: uuid[16], timestamp u32, level u8, message_length u8,
        #                line_number u16, filename char[16], message
        if len(body) < 40:
            return
        _ts, _level, msg_len, line_no = struct.unpack_from(">IBBH", body, 16)
        filename = body[24:40].split(b"\0")[0].decode("utf-8", "replace")
        message = body[40:40 + msg_len].decode("utf-8", "replace")
        line = f"[{filename}:{line_no}] {message}"
        with self._sink_lock:
            sinks = list(self._sinks)
        for sink in sinks:
            try:
                sink._on_line(line)
            except Exception:
                pass


class LogCapture:
    """
    Captures app logs in background and provides parsing for TEST_STATE lines.

    Attaches to the shared per-platform _LogStream. Multiple captures can be
    attached at once; each receives every line while it is attached.

    Usage:
        capture = LogCapture(platform="basalt")
        capture.start()
        # ... interact with emulator ...
        state = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state['time'] == '2:00'
        capture.stop()
    """

    STATE_PATTERN = re.compile(r'TEST_STATE:(\w+),(.+)')

    def __init__(self, platform: str):
        self.platform = platform
        self._reader: Optional[_LogStream] = None
        self._state_queue: queue.Queue = queue.Queue()
        self._all_logs: list[str] = []
        self._running = False

    def start(self):
        """Attach to the shared platform log stream and start capturing."""
        if self._running:
            return
        self._reader = _LogStream.get(self.platform)
        self._reader.attach(self)
        self._running = True
        logger.debug(f"[{self.platform}] Log capture started")

    def _on_line(self, line: str):
        """Called by the platform reader thread for every log line."""
        self._all_logs.append(line)
        if 'TEST_STATE:' in line:
            state = self._parse_state_line(line)
            if state:
                self._state_queue.put(state)
                logger.debug(f"[{self.platform}] Captured state: {state}")

    def _parse_state_line(self, line: str) -> Optional[dict]:
        idx = line.find('TEST_STATE:')
        if idx == -1:
            return None
        state_part = line[idx:]
        match = self.STATE_PATTERN.match(state_part)
        if not match:
            logger.warning(f"[{self.platform}] Could not parse state line: {state_part}")
            return None
        event = match.group(1)
        fields_str = match.group(2)
        state = {'event': event}
        for field in fields_str.split(','):
            if '=' in field:
                key, value = field.split('=', 1)
                state[key] = value
        return state

    def stop(self):
        """Detach from the platform log stream (the stream stays alive)."""
        if not self._running:
            return
        self._running = False
        if self._reader:
            self._reader.detach(self)
            self._reader = None
        logger.debug(f"[{self.platform}] Log capture stopped")

    def get_all_logs(self) -> list[str]:
        """Return all log lines captured during this instance's active period."""
        return self._all_logs.copy()

    def get_state_logs(self) -> list[dict]:
        """Return all captured state logs as a list of dicts."""
        states = []
        while not self._state_queue.empty():
            try:
                states.append(self._state_queue.get_nowait())
            except queue.Empty:
                break
        for state in states:
            self._state_queue.put(state)
        return states

    def wait_for_state(self, event: Optional[str] = None, timeout: float = 5.0) -> Optional[dict]:
        """
        Wait for the next state log entry, optionally matching a specific event.

        Args:
            event: If provided, skip states until one with this event is found
            timeout: Maximum time to wait in seconds

        Returns:
            The state dict, or None if timeout
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                state = self._state_queue.get(timeout=min(0.1, remaining))
                if event is None or state.get('event') == event:
                    return state
            except queue.Empty:
                continue
        return None

    def clear_state_queue(self):
        """Clear all pending state logs."""
        while not self._state_queue.empty():
            try:
                self._state_queue.get_nowait()
            except queue.Empty:
                break


def parse_time(time_str: str) -> tuple[int, int]:
    """Parse a time string 'M:SS' into (minutes, seconds)."""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 0


def assert_time_equals(state: dict, minutes: int, seconds: int):
    """Assert the timer shows exactly this time.

    Note: State uses short field name 't' for time.
    """
    expected = f"{minutes}:{seconds:02d}"
    actual = state.get('t', '')
    assert actual == expected, f"Expected time {expected}, got {actual}"


def assert_time_approximately(state: dict, minutes: int, seconds: int, tolerance: int = 5):
    """Assert the timer is within tolerance seconds of expected.

    Note: State uses short field name 't' for time.
    """
    actual_min, actual_sec = parse_time(state.get('t', '0:00'))
    actual_total = actual_min * 60 + actual_sec
    expected_total = minutes * 60 + seconds
    diff = abs(actual_total - expected_total)
    assert diff <= tolerance, (
        f"Expected time ~{minutes}:{seconds:02d} (±{tolerance}s), "
        f"got {state.get('t', '?')}"
    )


def assert_mode(state: dict, mode: str):
    """Assert the control mode matches.

    Note: State uses short field name 'm' for mode.
    """
    actual = state.get('m', '')
    assert actual == mode, f"Expected mode {mode}, got {actual}"


def assert_paused(state: dict, paused: bool = True):
    """Assert pause state.

    Note: State uses short field name 'p' for paused.
    """
    expected = '1' if paused else '0'
    actual = state.get('p', '')
    assert actual == expected, f"Expected paused={expected}, got paused={actual}"


def assert_repeat_count(state: dict, count: int):
    """Assert repeat counter value.

    Note: State uses short field name 'r' for repeat.
    """
    actual = int(state.get('r', '0'))
    assert actual == count, f"Expected repeat={count}, got repeat={actual}"


def assert_vibrating(state: dict, vibrating: bool = True):
    """Assert vibration state.

    Note: State uses short field name 'v' for vibrating.
    """
    expected = '1' if vibrating else '0'
    actual = state.get('v', '')
    assert actual == expected, f"Expected vibrating={expected}, got vibrating={actual}"


def assert_direction(state: dict, forward: bool = True):
    """Assert direction (forward=1, reverse=-1).

    Note: State uses short field name 'd' for direction.
    """
    expected = '1' if forward else '-1'
    actual = state.get('d', '')
    assert actual == expected, f"Expected direction={expected}, got direction={actual}"


def assert_backlight(state: dict, on: bool = True):
    """Assert backlight state.

    Note: State uses short field name 'l' for light.
    """
    expected = '1' if on else '0'
    actual = state.get('l', '')
    assert actual == expected, f"Expected backlight={expected}, got backlight={actual}"


def assert_base_length(state: dict, expected_ms: int, tolerance_ms: int = 0):
    """Assert the base_length_ms value.

    Note: State uses short field name 'bl' for base_length_ms.
    """
    actual = int(state.get('bl', '0'))
    diff = abs(actual - expected_ms)
    assert diff <= tolerance_ms, (
        f"Expected base_length_ms={expected_ms} (±{tolerance_ms}ms), "
        f"got {actual}"
    )


def assert_is_chrono(state: dict, is_chrono: bool = True):
    """Assert whether timer is in chrono mode.

    Note: State uses short field name 'c' for chrono.
    """
    expected = '1' if is_chrono else '0'
    actual = state.get('c', '')
    assert actual == expected, (
        f"Expected timer to be {'chrono' if is_chrono else 'countdown'}, "
        f"but timer is {'chrono' if actual == '1' else 'countdown'}"
    )