"""
Shared fixtures for functional tests.

Provides emulator setup, screenshot helpers, and button simulation.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

# Configure module logger
logger = logging.getLogger(__name__)

# Add pebble tool to path
CONDA_ENV = Path(__file__).parent.parent.parent / "conda-env"
PEBBLE_CMD = CONDA_ENV / "bin" / "pebble"
PYTHON_CMD = CONDA_ENV / "bin" / "python"
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Emulator platforms
PLATFORMS = ["aplite", "basalt", "chalk", "diorite", "emery"]

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

    def wipe(self):
        """Wipe emulator state for a fresh start."""
        logger.debug(f"[{self.platform}] Wiping emulator state")
        # Kill any existing emulator first - this is required so the wipe takes effect
        try:
            self._run_pebble("kill", "--force", check=False)
            time.sleep(2)  # Give processes time to fully exit
        except Exception:
            pass
        # Wipe storage (deletes persist directory for all platforms)
        self._run_pebble("wipe", check=False)
        # Reset port info since emulator was killed
        self._pypkjs_port = None
        logger.debug(f"[{self.platform}] Wipe complete")

    def build(self):
        """Build the application."""
        result = self._run_pebble("build", timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Build failed:\n{result.stderr}")

    def install(self):
        """Install and launch the app on the emulator."""
        logger.info(f"[{self.platform}] Installing app on emulator")
        # Install will start the emulator if needed
        result = self._run_pebble(
            "install",
            f"--emulator={self.platform}",
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Install failed:\n{result.stderr}")
        # Give the app time to fully load (but not too long - app has 3-second inactivity timer)
        time.sleep(1)
        # Get emulator info for button presses
        self._connect_transport()
        logger.info(f"[{self.platform}] App installed and transport connected")

    def _connect_transport(self):
        """Connect to pypkjs WebSocket for button presses."""
        # Import here to avoid issues when pytest collects tests
        sys.path.insert(0, str(CONDA_ENV / "lib" / "python3.10" / "site-packages"))
        from pebble_tool.sdk.emulator import get_emulator_info

        info = get_emulator_info(self.platform)
        if info is None:
            raise RuntimeError(f"Could not get emulator info for {self.platform}")

        self._pypkjs_port = info["pypkjs"]["port"]
        logger.debug(f"[{self.platform}] Got pypkjs port {self._pypkjs_port}")

        # Establish WebSocket connection to pypkjs
        self._ensure_websocket()

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

    def open_app_via_menu(self):
        """
        Re-open the app by navigating through the Pebble launcher menu.

        This method is used after quitting the app (long-press down) to re-launch
        it WITHOUT using install(), which would clear the app's persisted state.

        After quitting via long-press Down, the Pebble returns to the launcher
        with the previously-run app already selected, so a single SELECT press
        launches it.

        If the app auto-quit (e.g. chrono auto-background), the Pebble also
        returns to the launcher with the app selected, so SELECT still works.
        """
        logger.info(f"[{self.platform}] Opening app via menu navigation")
        self.press_select()
        time.sleep(1)  # Allow time for app to fully load
        logger.info(f"[{self.platform}] App opened via menu")

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
        """Kill the emulator."""
        logger.debug(f"[{self.platform}] Killing emulator")
        # Close WebSocket connection first
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        try:
            self._run_pebble("kill", check=False)
        except Exception:
            pass
        self._pypkjs_port = None
        logger.debug(f"[{self.platform}] Emulator killed")


@pytest.fixture(scope="session")
def build_app():
    """Session-scoped fixture to build the app once per test session."""
    helper = EmulatorHelper("basalt")  # Platform doesn't matter for build
    helper.build()
    return True


@pytest.fixture
def emulator(request, platform, build_app):
    """Fixture that provides a configured emulator helper with fresh state."""
    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Setup: wipe and install (build is already done by build_app fixture)
    helper.wipe()
    helper.install()

    yield helper

    # Teardown: keep emulator running for faster subsequent tests on same platform


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

    # Navigate to launcher: after first quit the watch lands on the watchface.
    # Press SELECT to enter the launcher so open_app_via_menu() can launch
    # the app with a single SELECT press.
    helper.press_select()
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

    # Try to get emulator helper from various fixture names
    for fixture_name in ['persistent_emulator', 'emulator']:
        try:
            emulator_helper = request.getfixturevalue(fixture_name)
            break
        except pytest.FixtureLookupError:
            continue

    if emulator_helper is not None:
        # Set test name for screenshot prefixing
        emulator_helper.set_test_name(test_name)
        # Open the app before the test
        logger.info(f"[{emulator_helper.platform}] Opening app for test: {test_name}")
        emulator_helper.open_app_via_menu()
        time.sleep(0.5)

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