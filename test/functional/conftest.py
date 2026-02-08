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
if not PEBBLE_CMD.exists():
    PEBBLE_CMD = Path("pebble")

PYTHON_CMD = CONDA_ENV / "bin" / "python"
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Emulator platforms
PLATFORMS = ["aplite", "basalt", "chalk", "diorite"]

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
        if self._ws is not None:
            # Transport already connected from a previous install; the pypkjs
            # WebSocket survives app reinstalls. Use a shorter wait to stay
            # within the app's 3-second inactivity timer.
            time.sleep(0.5)
        else:
            # First install: give app time to fully load, then connect transport
            time.sleep(1)
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


####################################################################################################
# Log Capture for Test Assertions
#
# These classes and functions enable functional tests to verify app state by parsing
# structured log output instead of relying on OCR. See ralph/specs/test-logging.md.
#

import re
import threading
import queue
from typing import Optional


class LogCapture:
    """
    Captures pebble logs in background and provides parsing for TEST_STATE lines.

    Usage:
        capture = LogCapture(platform="basalt")
        capture.start()
        # ... interact with emulator ...
        state = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state['time'] == '2:00'
        capture.stop()
    """

    # Regex to parse TEST_STATE log lines
    # Format: TEST_STATE:<event>,time=M:SS,mode=<mode>,repeat=<n>,paused=<0|1>,vibrating=<0|1>,direction=<1|-1>
    STATE_PATTERN = re.compile(r'TEST_STATE:(\w+),(.+)')

    def __init__(self, platform: str):
        self.platform = platform
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._state_queue: queue.Queue = queue.Queue()
        self._all_logs: list[str] = []
        self._running = False

    def start(self):
        """Start capturing logs in background."""
        if self._running:
            return

        env = os.environ.copy()
        env["PEBBLE_EMULATOR"] = self.platform

        self._process = subprocess.Popen(
            [str(PEBBLE_CMD), "logs", f"--emulator={self.platform}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
        )

        self._running = True
        self._thread = threading.Thread(target=self._read_logs, daemon=True)
        self._thread.start()
        logger.debug(f"[{self.platform}] Log capture started")

    def _read_logs(self):
        """Background thread that reads log lines and queues state logs."""
        while self._running and self._process and self._process.poll() is None:
            try:
                line = self._process.stdout.readline()
                if not line:
                    continue

                line = line.strip()
                self._all_logs.append(line)

                # Check for TEST_STATE lines
                if 'TEST_STATE:' in line:
                    state = self._parse_state_line(line)
                    if state:
                        self._state_queue.put(state)
                        logger.debug(f"[{self.platform}] Captured state: {state}")
            except Exception as e:
                logger.warning(f"[{self.platform}] Error reading log: {e}")
                break

    def _parse_state_line(self, line: str) -> Optional[dict]:
        """Parse a TEST_STATE log line into a dictionary."""
        # Find the TEST_STATE part in the log line
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
        """Stop capturing logs."""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        logger.debug(f"[{self.platform}] Log capture stopped")

    def get_all_logs(self) -> list[str]:
        """Return all captured log lines."""
        return self._all_logs.copy()

    def get_state_logs(self) -> list[dict]:
        """Return all captured state logs as a list of dicts."""
        states = []
        while not self._state_queue.empty():
            try:
                states.append(self._state_queue.get_nowait())
            except queue.Empty:
                break
        # Put them back for other consumers
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
                # Not the event we want, keep waiting
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