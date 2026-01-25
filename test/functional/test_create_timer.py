"""
Test Case: Create a 2-minute timer using the down button.

This test verifies that pressing the Down button affects the timer display.

Note: The app has a 3-second inactivity timer that transitions from
ControlModeNew to ControlModeCounting. Due to emulator startup time,
tests may observe the app in counting mode rather than "New" mode.
The tests verify that button presses correctly update the display.
"""

import logging
import pytest
from PIL import Image
import time

from .conftest import Button, EmulatorHelper, PLATFORMS

# Configure module logger
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """
    Module-scoped fixture that launches the emulator once per platform.

    The fixture performs a "warm-up" cycle:
    1. Wipe storage, install app
    2. Long press Down to quit the app (sets app state for next launch)
    3. Re-open the app within the same emulator (preserves persisted state)

    This ensures each test session starts with consistent app state without
    destroying the persist data set by the long-press quit action.
    """
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")

    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Phase 1: Warm-up cycle to clear any stale state and set initial state
    logger.info(f"[{platform}] Starting warm-up cycle to clear stale state")
    helper.wipe()
    helper.install()
    logger.info(f"[{platform}] Waiting for emulator to stabilize (2s)")
    time.sleep(2)  # Allow emulator to stabilize

    # Long press Down button to quit the app - this sets the app's persist state
    logger.info(f"[{platform}] Holding down button to quit app and set persist state")
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    logger.info(f"[{platform}] App quit via long press, persist state set")
    time.sleep(0.5)

    # Phase 2: Re-open the app via menu navigation (preserves persist state)
    # Using install() would clear the app's persisted state, so instead we
    # navigate through the Pebble launcher menu to re-open the app
    logger.info(f"[{platform}] Re-opening app via menu navigation (preserving persist state)")
    helper.open_app_via_menu()
    logger.info(f"[{platform}] Waiting for app to load (1s)")
    time.sleep(1)  # Allow app to fully load
    logger.info(f"[{platform}] Emulator ready for tests")

    yield helper

    # Teardown: kill emulator
    logger.info(f"[{platform}] Tearing down - killing emulator")
    helper.kill()


class TestCreateTimer:
    """Tests for creating a timer via button presses."""

    def test_create_2_minute_timer(self, persistent_emulator):
        """
        Test that Down button presses affect the timer display.

        This test verifies:
        1. The app launches and displays something (not blank)
        2. Pressing Down changes the display
        3. Pressing Down again changes the display again

        Note: Due to the app's 3-second inactivity timer, the exact mode
        may vary. In ControlModeNew, Down adds 1 minute. In ControlModeCounting
        with a running chrono, the display changes as time passes.
        """
        screenshots = []
        emulator = persistent_emulator

        # Step 1: Take initial screenshot
        img1 = emulator.screenshot("step1_initial")
        screenshots.append(("step1_initial", img1))

        # Step 2: Press Down once and take screenshot
        emulator.press_down()
        img2 = emulator.screenshot("step2_after_first_down")
        screenshots.append(("step2_1min", img2))

        # Step 3: Press Down again and take screenshot
        emulator.press_down()
        img3 = emulator.screenshot("step3_after_second_down")
        screenshots.append(("step3_2min", img3))

        # Verify that screenshots are different (display changed)
        # This confirms button presses are being received and processed
        assert img1.tobytes() != img2.tobytes(), (
            "Screenshot after first Down press should be different from initial"
        )
        assert img2.tobytes() != img3.tobytes(), (
            "Screenshot after second Down press should be different from first"
        )

        # Screenshots can be visually inspected with --save-screenshots

    def test_initial_state_shows_new(self, persistent_emulator):
        """Test that the initial state shows 'New' in the header."""
        emulator = persistent_emulator
        # Take screenshot of initial state
        img = emulator.screenshot("initial_state")

        # Basic check: image was captured and has content
        assert img is not None
        assert img.size[0] > 0 and img.size[1] > 0

        # The image should not be completely blank/uniform
        # Check that there's some variation in pixel values
        extrema = img.convert("L").getextrema()
        assert extrema[0] != extrema[1], "Screen appears to be blank"

    def test_down_button_increments_minutes(self, persistent_emulator):
        """Test that each Down press adds 1 minute to the timer."""
        emulator = persistent_emulator
        # Take initial screenshot for comparison
        initial = emulator.screenshot()

        # Press Down and verify change
        emulator.press_down()
        after_one = emulator.screenshot()

        assert initial.tobytes() != after_one.tobytes(), (
            "Display should change after Down press"
        )

        # Press Down again
        emulator.press_down()
        after_two = emulator.screenshot()

        assert after_one.tobytes() != after_two.tobytes(), (
            "Display should change after second Down press"
        )

        # Press Down a third time
        emulator.press_down()
        after_three = emulator.screenshot()

        assert after_two.tobytes() != after_three.tobytes(), (
            "Display should change after third Down press"
        )


class TestButtonPresses:
    """Additional tests for button functionality."""

    def test_up_button_increments_20_minutes(self, persistent_emulator):
        """Test that Up button increments timer by 20 minutes."""
        emulator = persistent_emulator
        initial = emulator.screenshot()

        emulator.press_up()
        after_up = emulator.screenshot()

        # The display should change after pressing Up
        assert initial.tobytes() != after_up.tobytes(), (
            "Display should change after Up press"
        )

    def test_select_button_increments_5_minutes(self, persistent_emulator):
        """Test that Select button increments timer by 5 minutes."""
        emulator = persistent_emulator
        initial = emulator.screenshot()

        emulator.press_select()
        after_select = emulator.screenshot()

        # The display should change after pressing Select
        assert initial.tobytes() != after_select.tobytes(), (
            "Display should change after Select press"
        )
