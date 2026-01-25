"""
Shared fixtures for functional tests.

Provides emulator setup, screenshot helpers, and button simulation.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

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
        self._qemu_port = None

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
        # Kill any existing emulator first - this is required so the wipe takes effect
        try:
            self._run_pebble("kill", "--force", check=False)
            time.sleep(2)  # Give processes time to fully exit
        except Exception:
            pass
        # Wipe storage (deletes persist directory for all platforms)
        self._run_pebble("wipe", check=False)
        # Reset port info since emulator was killed
        self._qemu_port = None

    def build(self):
        """Build the application."""
        result = self._run_pebble("build", timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Build failed:\n{result.stderr}")

    def install(self):
        """Install and launch the app on the emulator."""
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

    def _connect_transport(self):
        """Connect to the emulator's QEMU transport for button presses."""
        # Import here to avoid issues when pytest collects tests
        sys.path.insert(0, str(CONDA_ENV / "lib" / "python3.10" / "site-packages"))
        from pebble_tool.sdk.emulator import get_emulator_info

        info = get_emulator_info(self.platform)
        if info is None:
            raise RuntimeError(f"Could not get emulator info for {self.platform}")

        self._qemu_port = info["qemu"]["port"]

    def _send_button(self, button: int, retries: int = 2):
        """Send a button press to the emulator via QEMU protocol."""
        if self._qemu_port is None:
            self._connect_transport()

        import socket
        from libpebble2.communication.transports.qemu.protocol import QemuButton, QemuPacket

        # Create button press packet
        press_packet = QemuButton(state=button)
        # Create button release packet (state=0 means no buttons pressed)
        release_packet = QemuButton(state=0)

        for attempt in range(retries + 1):
            # Send via raw socket to QEMU port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # 5 second timeout
            try:
                sock.connect(("localhost", self._qemu_port))
                # Send press
                data = QemuPacket(data=press_packet).serialise()
                sock.send(data)
                time.sleep(0.05)  # Brief press
                # Send release
                data = QemuPacket(data=release_packet).serialise()
                sock.send(data)
                break  # Success
            except (socket.timeout, ConnectionError, OSError) as e:
                if attempt < retries:
                    # Refresh port info and retry
                    self._qemu_port = None
                    self._connect_transport()
                else:
                    raise RuntimeError(
                        f"Failed to send button after {retries + 1} attempts: {e}"
                    )
            finally:
                sock.close()

        # Wait for display to update
        time.sleep(0.2)

    def hold_button(self, button: int, retries: int = 2):
        """Holds a button down without releasing it."""
        if self._qemu_port is None:
            self._connect_transport()

        import socket
        from libpebble2.communication.transports.qemu.protocol import QemuButton, QemuPacket

        press_packet = QemuButton(state=button)
        for attempt in range(retries + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            try:
                sock.connect(("localhost", self._qemu_port))
                data = QemuPacket(data=press_packet).serialise()
                sock.send(data)
                break
            except (socket.timeout, ConnectionError, OSError) as e:
                if attempt < retries:
                    self._qemu_port = None
                    self._connect_transport()
                else:
                    raise RuntimeError(
                        f"Failed to send button press after {retries + 1} attempts: {e}"
                    )
            finally:
                sock.close()
        time.sleep(0.2)

    def release_buttons(self, retries: int = 2):
        """Releases all currently held buttons."""
        if self._qemu_port is None:
            self._connect_transport()

        import socket
        from libpebble2.communication.transports.qemu.protocol import QemuButton, QemuPacket

        release_packet = QemuButton(state=0)
        for attempt in range(retries + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            try:
                sock.connect(("localhost", self._qemu_port))
                data = QemuPacket(data=release_packet).serialise()
                sock.send(data)
                break
            except (socket.timeout, ConnectionError, OSError) as e:
                if attempt < retries:
                    self._qemu_port = None
                    self._connect_transport()
                else:
                    raise RuntimeError(
                        f"Failed to send button release after {retries + 1} attempts: {e}"
                    )
            finally:
                sock.close()
        time.sleep(0.2)

    def press_back(self):
        """Press the Back button."""
        self._send_button(Button.BACK)

    def press_up(self):
        """Press the Up button."""
        self._send_button(Button.UP)

    def press_select(self):
        """Press the Select button."""
        self._send_button(Button.SELECT)

    def press_down(self):
        """Press the Down button."""
        self._send_button(Button.DOWN)

    def screenshot(self, name: str = None) -> Image.Image:
        """Take a screenshot and return as PIL Image."""
        # Generate temp filename
        if name:
            filename = self.screenshot_dir / f"{self.platform}_{name}.png"
        else:
            filename = self.screenshot_dir / f"{self.platform}_temp.png"

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
        try:
            self._run_pebble("kill", check=False)
        except Exception:
            pass


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
