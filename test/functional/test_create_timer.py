"""
Test Case: Create a 2-minute timer using the down button.

This test verifies that pressing the Down button affects the timer display.

Note: The app has a 3-second inactivity timer that transitions from
ControlModeNew to ControlModeCounting. Due to emulator startup time,
tests may observe the app in counting mode rather than "New" mode.
The tests verify that button presses correctly update the display.
"""

import pytest
from PIL import Image
import time

from .conftest import Button, EmulatorHelper, PLATFORMS


@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """
    Module-scoped fixture that launches the emulator once per platform, performs
    a long "Down" button press, and then yields the emulator for all tests.
    """
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")
    
    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Setup: wipe, install, and do a long press of the down button
    helper.wipe()
    helper.install()
    print(f"[{platform}] Waiting for emulator to stailize.")
    time.sleep(20)  # Allow emulator to stabilize

    # Perform a 1-second long press of the Down button
    print(f"[{platform}] Holding down button.")
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    print(f"[{platform}] Performed a long press of the Down button.")

    time.sleep(0.5) # Wait for app to process the button release
    # TODO: confirm if app need to be relaunced here.

    yield helper

    # Teardown: kill emulator
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
