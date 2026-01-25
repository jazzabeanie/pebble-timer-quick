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
import easyocr
import time

from .conftest import Button, EmulatorHelper, PLATFORMS

# Configure module logger
logger = logging.getLogger(__name__)

# Initialize EasyOCR reader once (models are loaded on first use)
_ocr_reader = None


def _get_ocr_reader():
    """Lazy initialization of EasyOCR reader to avoid loading models until needed."""
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _ocr_reader


def extract_text(img: Image.Image) -> str:
    """Extract text from a Pebble screenshot using OCR.

    Uses EasyOCR with preprocessing optimized for the LECO 7-segment style font.
    """
    import numpy as np

    # Scale up the image 6x for better OCR recognition of small fonts
    scaled = img.resize((img.width * 6, img.height * 6), Image.Resampling.LANCZOS)

    # Convert to RGB for EasyOCR
    rgb = scaled.convert("RGB")

    # Convert to numpy array for EasyOCR
    img_array = np.array(rgb)

    reader = _get_ocr_reader()
    results = reader.readtext(img_array, detail=0, paragraph=False)

    return ' '.join(results)


def normalize_time_text(text: str) -> str:
    """Normalize OCR text to standard time format for matching.

    The LECO 7-segment font can cause various misreadings:
    - Colon ':' may be read as '.', ';', or omitted entirely
    - Digits may have common substitutions (0/O, 1/l, 5/S, etc.)

    This function normalizes the text to make pattern matching easier.
    """
    # First, normalize potential colon separators to ':'
    # Common OCR misreadings: '.' ';' or no separator (adjacent digits)
    normalized = text.replace(';', ':').replace('.', ':')

    # Also normalize common digit/letter substitutions
    # (keeping original case-insensitive matching in tests is also important)
    return normalized


def has_time_pattern(text: str, minutes: int, tolerance: int = 10) -> bool:
    """Check if OCR text contains a time pattern for approximately 'minutes' minutes.

    Args:
        text: The OCR extracted text
        minutes: Expected minutes (e.g., 2 for a 2-minute timer)
        tolerance: Seconds tolerance for countdown (default 10 seconds)

    Returns:
        True if a matching time pattern is found
    """
    import re

    # Normalize the text
    normalized = normalize_time_text(text)

    # Build patterns for expected time range
    # For N minutes, we expect (N-1):5X to N:00 approximately
    expected_min = max(0, minutes - 1)
    expected_max = minutes

    # Pattern to find time-like sequences (M:SS or MSS format)
    # Matches digit followed by separator (or not) followed by 2 digits
    time_pattern = r'(\d)[:\s]?(\d{2})'

    matches = re.findall(time_pattern, normalized)
    for match in matches:
        try:
            mins = int(match[0])
            secs = int(match[1])
            total_secs = mins * 60 + secs
            expected_min_secs = expected_min * 60 + (60 - tolerance)
            expected_max_secs = expected_max * 60 + tolerance

            if expected_min_secs <= total_secs <= expected_max_secs:
                return True
        except ValueError:
            continue

    # Also check for simple digit patterns without separator
    # e.g., "157" for "1:57"
    digit_pattern = r'(\d)(\d{2})'
    matches = re.findall(digit_pattern, text.replace(' ', ''))
    for match in matches:
        try:
            mins = int(match[0])
            secs = int(match[1])
            if 0 <= secs < 60:  # Valid seconds
                total_secs = mins * 60 + secs
                expected_min_secs = expected_min * 60 + (60 - tolerance)
                expected_max_secs = expected_max * 60 + tolerance
                if expected_min_secs <= total_secs <= expected_max_secs:
                    return True
        except ValueError:
            continue

    return False


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
        # EasyOCR may read colon as '.' or ';', and digits may vary
        text2 = extract_text(img2)
        logger.info(f"extracted text {text2}")

        # Use flexible pattern matching that handles OCR variations
        # Also check for simple digit patterns: "15x" could be "1:5x"
        normalized = normalize_time_text(text2)
        time_patterns = ["1:5", "1.5", "1;5", "15"]  # Various colon representations
        has_time = any(pattern in normalized for pattern in time_patterns)

        # Also try the helper function for range matching
        if not has_time:
            has_time = has_time_pattern(text2, minutes=2, tolerance=15)

        assert has_time, f"Expected time around 1:5x after 2 Down presses, got: {text2}"

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
        # EasyOCR may read colon as '.' or ';', and digits may vary
        text = extract_text(img)
        logger.info(f"After 3 Down presses: {text}")

        # Use flexible pattern matching
        normalized = normalize_time_text(text)
        time_patterns = ["2:5", "2.5", "2;5", "25"]  # Various colon representations
        has_time = any(pattern in normalized for pattern in time_patterns)

        # Also try range matching
        if not has_time:
            has_time = has_time_pattern(text, minutes=3, tolerance=15)

        assert has_time, f"Expected time around 2:5x after 3 Down presses, got: {text}"


class TestButtonPresses:
    """Additional tests for button functionality."""

    def test_up_button_increments_20_minutes(self, persistent_emulator):
        """Test that Up button increments timer by 20 minutes."""
        emulator = persistent_emulator

        emulator.press_up()
        img = emulator.screenshot("after_up")

        # Verify the timer shows ~20 minutes (19:5x due to countdown)
        text = extract_text(img)
        logger.info(f"After Up press: {text}")

        # Use flexible pattern matching for ~19 minutes
        normalized = normalize_time_text(text)
        time_patterns = ["19:", "19.", "19;"]
        has_time = any(pattern in normalized for pattern in time_patterns)

        if not has_time:
            has_time = has_time_pattern(text, minutes=20, tolerance=15)

        assert has_time, f"Expected time around 19:xx after Up press, got: {text}"

    def test_select_button_increments_5_minutes(self, persistent_emulator):
        """Test that Select button increments timer by 5 minutes."""
        emulator = persistent_emulator

        emulator.press_select()
        img = emulator.screenshot("after_select")

        # Verify the timer shows ~5 minutes (4:5x due to countdown)
        text = extract_text(img)
        logger.info(f"After Select press: {text}")

        # Use flexible pattern matching
        normalized = normalize_time_text(text)
        time_patterns = ["4:5", "4.5", "4;5", "45"]
        has_time = any(pattern in normalized for pattern in time_patterns)

        if not has_time:
            has_time = has_time_pattern(text, minutes=5, tolerance=15)

        assert has_time, f"Expected time around 4:5x after Select press, got: {text}"


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

        # Verify initial time shows ~1 minute (0:5x)
        normalized1 = normalize_time_text(text1)
        time_patterns_start = ["0:5", "0.5", "0;5", "05"]
        has_start_time = any(pattern in normalized1 for pattern in time_patterns_start)
        if not has_start_time:
            has_start_time = has_time_pattern(text1, minutes=1, tolerance=15)
        assert has_start_time, f"Expected time around 0:5x initially, got: {text1}"

        # Wait 5 seconds and take another screenshot
        time.sleep(5)
        screenshot2 = emulator.screenshot("countdown_after_5s")
        text2 = extract_text(screenshot2)
        logger.info(f"After 5s text: {text2}")

        # Timer should have counted down - look for ~50 seconds or less (0:4x or lower)
        normalized2 = normalize_time_text(text2)
        time_patterns_later = ["0:4", "0.4", "0:3", "0.3", "0:2", "0.2"]
        has_later_time = any(pattern in normalized2 for pattern in time_patterns_later)
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
        normalized1 = normalize_time_text(text1)
        time_patterns_start = ["0:0", "0.0", "0;0"]
        has_start_time = any(pattern in normalized1 for pattern in time_patterns_start)
        assert has_start_time, f"Expected chrono to show '0:0x' at start, got: {text1}"

        # Wait and verify it's counting up
        time.sleep(5)
        screenshot2 = emulator.screenshot("chrono_after_5s")
        text2 = extract_text(screenshot2)
        logger.info(f"Chrono after 5s: {text2}")

        # Should now show higher time (0:05 or more)
        normalized2 = normalize_time_text(text2)
        time_patterns_later = ["0:0", "0.0", "0:1", "0.1"]
        has_later_time = any(pattern in normalized2 for pattern in time_patterns_later)
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
        normalized = normalize_time_text(text_before)
        time_patterns_before = ["19:", "19.", "19;", "20:", "20."]
        has_time_before = any(pattern in normalized for pattern in time_patterns_before)
        if not has_time_before:
            has_time_before = has_time_pattern(text_before, minutes=20, tolerance=15)
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
