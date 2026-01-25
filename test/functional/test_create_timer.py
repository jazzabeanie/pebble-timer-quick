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
import pytesseract
import time

from .conftest import Button, EmulatorHelper, PLATFORMS

# Configure module logger
logger = logging.getLogger(__name__)


def extract_text(img: Image.Image) -> str:
    """Extract text from a Pebble screenshot using OCR.

    Pebble screenshots are small, so we scale them up for better OCR accuracy.
    """
    # Scale up the image 4x for better OCR recognition
    scaled = img.resize((img.width * 4, img.height * 4), Image.Resampling.LANCZOS)
    # Convert to grayscale for better OCR
    grayscale = scaled.convert("L")
    # Use PSM 6 (uniform block of text) for better recognition of watch display
    config = "--psm 6"
    return pytesseract.image_to_string(grayscale, config=config)


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


class TestCreateTimer:
    """Tests for creating a timer via button presses."""

    def test_create_2_minute_timer(self, persistent_emulator):
        """
        Test creating a 2-minute timer via two Down button presses.

        This test verifies:
        1. The app shows "New" mode initially
        2. After pressing Down twice, the timer shows approximately 2 minutes (1:5x)
        """
        emulator = persistent_emulator

        # Step 1: Take initial screenshot and verify "New" mode
        img1 = emulator.screenshot("step1_initial")
        text1 = extract_text(img1)
        assert "New" in text1, f"Expected 'New' in initial screen, got: {text1}"

        # Step 2: Press Down twice to set 2 minutes
        emulator.press_down()
        emulator.press_down()
        img2 = emulator.screenshot("step2_after_two_down")

        # Step 3: Verify the timer shows ~2 minutes (1:5x due to countdown)
        # Note: OCR may misread 7-segment digits (e.g., "1" as "L", "5" as "S")
        text2 = extract_text(img2)
        logger.info(f"extracted text {text2}")
        # Check for common OCR interpretations of "1:5x"
        time_patterns = ["1:5", "L:5", "1:S", "L:S"]
        has_time = any(pattern in text2 for pattern in time_patterns)
        assert has_time, f"Expected time starting with '1:5' (or OCR variant) after 2 Down presses, got: {text2}"

    def test_initial_state_shows_new(self, persistent_emulator):
        """Test that the initial state shows 'New' in the header."""
        emulator = persistent_emulator
        # Take screenshot of initial state
        img = emulator.screenshot("initial_state")

        # Extract text and verify "New" is shown
        text = extract_text(img)
        logger.info(f"Initial state text: {text}")
        assert "New" in text, f"Expected 'New' in initial screen, got: {text}"

    def test_down_button_increments_minutes(self, persistent_emulator):
        """Test that each Down press adds 1 minute to the timer."""
        emulator = persistent_emulator

        # Press Down three times to set 3 minutes
        emulator.press_down()
        emulator.press_down()
        emulator.press_down()
        img = emulator.screenshot("after_three_down")

        # Verify the timer shows ~3 minutes (2:5x due to countdown)
        # Note: OCR may misread 7-segment digits (e.g., "2" as "Z", "5" as "S")
        text = extract_text(img)
        logger.info(f"After 3 Down presses: {text}")
        time_patterns = ["2:5", "Z:5", "2:S", "Z:S"]
        has_time = any(pattern in text for pattern in time_patterns)
        assert has_time, f"Expected time starting with '2:5' (or OCR variant) after 3 Down presses, got: {text}"


class TestButtonPresses:
    """Additional tests for button functionality."""

    def test_up_button_increments_20_minutes(self, persistent_emulator):
        """Test that Up button increments timer by 20 minutes."""
        emulator = persistent_emulator

        emulator.press_up()
        img = emulator.screenshot("after_up")

        # Verify the timer shows ~20 minutes (19:5x due to countdown)
        # Note: OCR may misread 7-segment digits
        text = extract_text(img)
        logger.info(f"After Up press: {text}")
        # Look for "19:" pattern (20 minutes minus countdown)
        time_patterns = ["19:", "L9:", "1S:"]
        has_time = any(pattern in text for pattern in time_patterns)
        assert has_time, f"Expected time starting with '19:' (or OCR variant) after Up press, got: {text}"

    def test_select_button_increments_5_minutes(self, persistent_emulator):
        """Test that Select button increments timer by 5 minutes."""
        emulator = persistent_emulator

        emulator.press_select()
        img = emulator.screenshot("after_select")

        # Verify the timer shows ~5 minutes (4:5x due to countdown)
        # Note: OCR may misread 7-segment digits
        text = extract_text(img)
        logger.info(f"After Select press: {text}")
        # Look for "4:" pattern (5 minutes minus countdown)
        time_patterns = ["4:5", "4:S"]
        has_time = any(pattern in text for pattern in time_patterns)
        assert has_time, f"Expected time starting with '4:5' (or OCR variant) after Select press, got: {text}"


class TestTimerCountdown:
    """Tests for timer countdown functionality."""

    def test_timer_counts_down(self, persistent_emulator):
        """
        Test that a running timer counts down over time.

        This test:
        1. Sets a timer by pressing Down (adds 1 minute)
        2. Waits for the app to transition to counting mode (3 second inactivity)
        3. Takes screenshots at intervals to verify the timer value decreased
        """
        emulator = persistent_emulator

        # Set a 1 minute timer
        emulator.press_down()
        time.sleep(0.5)

        # Take first screenshot - should show ~1 minute (0:5x)
        screenshot1 = emulator.screenshot("countdown_start")
        text1 = extract_text(screenshot1)
        logger.info(f"Countdown start text: {text1}")

        # Verify initial time shows ~1 minute
        time_patterns_start = ["0:5", "O:5", "0:S", "O:S"]
        has_start_time = any(pattern in text1 for pattern in time_patterns_start)
        assert has_start_time, f"Expected time starting with '0:5' (or OCR variant) initially, got: {text1}"

        # Wait 5 seconds and take another screenshot
        time.sleep(5)
        screenshot2 = emulator.screenshot("countdown_after_5s")
        text2 = extract_text(screenshot2)
        logger.info(f"After 5s text: {text2}")

        # Timer should have counted down - look for ~50 seconds or less (0:4x or lower)
        time_patterns_later = ["0:4", "O:4", "0:3", "O:3", "0:2", "O:2"]
        has_later_time = any(pattern in text2 for pattern in time_patterns_later)
        assert has_later_time, f"Expected time to have decreased after 5s, got: {text2}"

    def test_timer_transitions_to_counting_mode(self, persistent_emulator):
        """
        Test that after 3 seconds of inactivity, the app transitions from
        'New' mode to 'Counting' mode (header changes from 'New').
        """
        emulator = persistent_emulator

        # Take initial screenshot - should show "New"
        initial = emulator.screenshot("transition_initial")
        text_initial = extract_text(initial)
        logger.info(f"Initial text: {text_initial}")
        assert "New" in text_initial, f"Expected 'New' in initial screen, got: {text_initial}"

        # Press Down to set timer value
        emulator.press_down()
        after_press = emulator.screenshot("transition_after_press")
        text_after = extract_text(after_press)
        logger.info(f"After Down press: {text_after}")
        assert "New" in text_after, f"Expected 'New' still shown after button press, got: {text_after}"

        # Wait for 3-second inactivity timeout to trigger mode transition
        time.sleep(4)

        # Take screenshot after transition
        after_transition = emulator.screenshot("transition_after_wait")
        text_transition = extract_text(after_transition)
        logger.info(f"After transition: {text_transition}")

        # In counting mode, "New" should no longer appear in header
        assert "New" not in text_transition, (
            f"Expected 'New' to disappear after transition to counting mode, got: {text_transition}"
        )


class TestChronoMode:
    """Tests for stopwatch (chrono) mode functionality."""

    def test_chrono_mode_counts_up(self, persistent_emulator):
        """
        Test that in chrono mode (no timer set), the stopwatch counts up.

        When the app starts fresh with no timer value set (0:00),
        after the 3-second timeout it begins counting up as a stopwatch.
        """
        emulator = persistent_emulator

        # Wait for the app to enter chrono mode (timer at 0:00 with no value set)
        # The app should start counting up
        time.sleep(4)  # Wait for transition

        screenshot1 = emulator.screenshot("chrono_start")
        text1 = extract_text(screenshot1)
        logger.info(f"Chrono mode start: {text1}")

        # Should show small time value (0:0x) - stopwatch just started
        time_patterns_start = ["0:0", "O:0", "0:O", "O:O"]
        has_start_time = any(pattern in text1 for pattern in time_patterns_start)
        assert has_start_time, f"Expected chrono to show '0:0x' at start, got: {text1}"

        # Wait and verify it's counting up
        time.sleep(5)
        screenshot2 = emulator.screenshot("chrono_after_5s")
        text2 = extract_text(screenshot2)
        logger.info(f"Chrono after 5s: {text2}")

        # Should now show higher time (0:05 or more)
        time_patterns_later = ["0:0", "O:0", "0:1", "O:1"]
        has_later_time = any(pattern in text2 for pattern in time_patterns_later)
        assert has_later_time, f"Expected chrono to have counted up, got: {text2}"

        # Verify the time actually increased by checking screenshots differ
        assert screenshot1.tobytes() != screenshot2.tobytes(), (
            "Display should change as chrono counts up"
        )


class TestPlayPause:
    """Tests for play/pause functionality."""

    def test_select_toggles_play_pause_in_counting_mode(self, persistent_emulator):
        """
        Test that pressing Select in counting mode toggles play/pause.

        In counting mode (after the 3-second timeout), pressing Select
        should pause/resume the timer.
        """
        emulator = persistent_emulator

        # Set a timer and wait for it to start counting
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode

        # Take screenshot while running
        running = emulator.screenshot("playpause_running")
        text_running = extract_text(running)
        logger.info(f"Running timer: {text_running}")

        # Press Select to pause
        emulator.press_select()
        time.sleep(0.5)
        paused = emulator.screenshot("playpause_paused")
        text_paused = extract_text(paused)
        logger.info(f"Paused timer: {text_paused}")

        # Wait a moment - if paused, the time value shouldn't change
        time.sleep(2)
        still_paused = emulator.screenshot("playpause_still_paused")
        text_still_paused = extract_text(still_paused)
        logger.info(f"Still paused: {text_still_paused}")

        # The paused screenshots should show the same time (timer stopped)
        assert paused.tobytes() == still_paused.tobytes(), (
            f"Display should not change while paused. Before: {text_paused}, After: {text_still_paused}"
        )

        # Press Select again to resume
        emulator.press_select()
        time.sleep(2)
        resumed = emulator.screenshot("playpause_resumed")
        text_resumed = extract_text(resumed)
        logger.info(f"Resumed timer: {text_resumed}")

        # Display should have changed (timer resumed counting)
        assert still_paused.tobytes() != resumed.tobytes(), (
            f"Display should change after resuming. Paused: {text_still_paused}, Resumed: {text_resumed}"
        )


class TestLongPressReset:
    """Tests for long press reset functionality."""

    def test_long_press_select_resets_timer(self, persistent_emulator):
        """
        Test that long pressing Select resets the timer.

        A long press on Select should restart/reset the timer.
        """
        emulator = persistent_emulator

        # Set a timer with some value
        emulator.press_up()  # Add 20 minutes
        time.sleep(0.5)
        before_reset = emulator.screenshot("reset_before")
        text_before = extract_text(before_reset)
        logger.info(f"Before reset: {text_before}")

        # Verify we have a non-zero timer (should show ~20 minutes)
        time_patterns_before = ["19:", "L9:", "1S:", "20:", "ZO:"]
        has_time_before = any(pattern in text_before for pattern in time_patterns_before)
        assert has_time_before, f"Expected timer showing ~20 minutes before reset, got: {text_before}"

        # Long press Select to reset
        emulator.hold_button(Button.SELECT)
        time.sleep(1)  # Hold for reset threshold
        emulator.release_buttons()
        time.sleep(0.5)

        after_reset = emulator.screenshot("reset_after")
        text_after = extract_text(after_reset)
        logger.info(f"After reset: {text_after}")

        # After reset, timer should be back to 0:00 and show "New"
        assert "New" in text_after, f"Expected 'New' after reset, got: {text_after}"
