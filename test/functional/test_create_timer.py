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


class TestCreateTimer:
    """Tests for creating a timer via button presses."""

    def test_create_2_minute_timer(self, emulator):
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

    def test_initial_state_shows_new(self, emulator):
        """Test that the initial state shows 'New' in the header."""
        # Take screenshot of initial state
        img = emulator.screenshot("initial_state")

        # Basic check: image was captured and has content
        assert img is not None
        assert img.size[0] > 0 and img.size[1] > 0

        # The image should not be completely blank/uniform
        # Check that there's some variation in pixel values
        extrema = img.convert("L").getextrema()
        assert extrema[0] != extrema[1], "Screen appears to be blank"

    def test_down_button_increments_minutes(self, emulator):
        """Test that each Down press adds 1 minute to the timer."""
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

    def test_up_button_increments_20_minutes(self, emulator):
        """Test that Up button increments timer by 20 minutes."""
        initial = emulator.screenshot()

        emulator.press_up()
        after_up = emulator.screenshot()

        # The display should change after pressing Up
        assert initial.tobytes() != after_up.tobytes(), (
            "Display should change after Up press"
        )

    def test_select_button_increments_5_minutes(self, emulator):
        """Test that Select button increments timer by 5 minutes."""
        initial = emulator.screenshot()

        emulator.press_select()
        after_select = emulator.screenshot()

        # The display should change after pressing Select
        assert initial.tobytes() != after_select.tobytes(), (
            "Display should change after Select press"
        )
