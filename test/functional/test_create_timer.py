"""
Test Case: Create a 2-minute timer using the down button.

This test verifies that pressing the Down button affects the timer display.

Note: The app has a 3-second inactivity timer that transitions from
ControlModeNew to ControlModeCounting. Due to emulator startup time,
tests may observe the app in counting mode rather than "New" mode.
The tests verify that button presses correctly update the display.
"""

import logging
import os
import pytest
from pathlib import Path
from PIL import Image
import easyocr
import time

from .conftest import Button, EmulatorHelper, PLATFORMS

# Configure module logger
logger = logging.getLogger(__name__)

# Directory for reference images
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
REFERENCES_DIR = SCREENSHOTS_DIR / "references"
REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

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
    - Digits may have common substitutions (0/O, 1/l/L, 5/S, etc.)

    This function normalizes the text to make pattern matching easier.
    """
    # Normalize common digit/letter substitutions from OCR
    # The 7-segment font often causes 0/O confusion and d/0 confusion
    # Also 1/l/L confusion
    normalized = text.replace('O', '0').replace('o', '0').replace('d', '0')
    normalized = normalized.replace('l', '1').replace('L', '1').replace('I', '1')
    normalized = normalized.replace('S', '5').replace('s', '5')

    # Normalize potential colon separators to ':'
    # Common OCR misreadings: '.' ';' or no separator (adjacent digits)
    normalized = normalized.replace(';', ':').replace('.', ':')

    # Remove any character that is not a digit, colon, space, or minus sign
    import re
    normalized = re.sub(r'[^0-9:\-\s]', '', normalized)

    return normalized


def has_time_pattern(text: str, minutes: int, tolerance: int = 10, seconds: int = 0) -> bool:
    """Check if OCR text contains a time pattern for approximately the specified time.

    The LECO 7-segment font causes frequent digit misreadings (e.g. 5→6, 6→8).
    To handle this, each digit in a detected time pattern is expanded to its
    common OCR variants before matching.

    Args:
        text: The OCR extracted text
        minutes: Expected minutes (e.g., 2 for a 2-minute timer)
        tolerance: Seconds tolerance for countdown (default 10 seconds)
        seconds: Expected seconds to add to minutes (default 0)

    Returns:
        True if a matching time pattern is found
    """
    import re
    from itertools import product

    # Common OCR digit confusions for 7-segment LECO font
    digit_variants = {
        '0': ['0', '8'],
        '1': ['1', '7'],
        '2': ['2'],
        '3': ['3'],
        '4': ['4'],
        '5': ['5', '6'],
        '6': ['5', '6', '8'],
        '7': ['1', '7'],
        '8': ['0', '6', '8'],
        '9': ['9'],
    }

    def expand_digit_variants(digit_str):
        """Given a string of digits, return all plausible OCR interpretations."""
        variant_lists = [digit_variants.get(d, [d]) for d in digit_str]
        return [''.join(combo) for combo in product(*variant_lists)]

    # Normalize the text
    normalized = normalize_time_text(text)

    # Build patterns for expected time range
    target_total_secs = minutes * 60 + seconds
    expected_min_secs = max(0, target_total_secs - tolerance)
    expected_max_secs = target_total_secs + tolerance

    # Pattern to find time-like sequences (M:SS or MSS format)
    # Matches digit followed by separator (or not) followed by 2 digits
    time_pattern = r'(\d)[:\s]?(\d{2})'

    matches = re.findall(time_pattern, normalized)
    for match in matches:
        min_str, sec_str = match[0], match[1]
        # Expand both digits to their OCR variant possibilities
        for min_variant in expand_digit_variants(min_str):
            for sec_variant in expand_digit_variants(sec_str):
                try:
                    mins = int(min_variant)
                    secs = int(sec_variant)
                    if 0 <= secs < 60:
                        total_secs = mins * 60 + secs
                        if expected_min_secs <= total_secs <= expected_max_secs:
                            return True
                except ValueError:
                    continue

    return False


# --- Repeat indicator detection via pixel comparison ---
# The repeat indicator ("_x", "2x", "3x") is drawn in white text in the
# top-right corner of the display. OCR is unreliable for detecting this small
# flashing text, so we use direct pixel analysis instead.
#
# The indicator text is pure white (255,255,255) against the green background.

# Indicator crop regions per platform
INDICATOR_REGIONS = {
    "aplite": (94, 0, 144, 30),
    "basalt": (94, 0, 144, 30),
    "chalk": (130, 0, 180, 30),
    "diorite": (94, 0, 144, 30),
    "emery": (150, 0, 200, 30),
}

# Minimum white pixel count to consider indicator visible
INDICATOR_WHITE_THRESHOLD = 20


def _get_indicator_crop(img: Image.Image, platform: str = "basalt") -> "np.ndarray":
    """Crop the top-right indicator region and return as numpy array."""
    import numpy as np
    region = INDICATOR_REGIONS.get(platform, INDICATOR_REGIONS["basalt"])
    crop = img.crop(region)
    return np.array(crop)


def _get_white_mask(crop_arr: "np.ndarray") -> "np.ndarray":
    """Extract a boolean mask of white pixels from a crop array."""
    import numpy as np
    return np.all(crop_arr[:, :, :3] == 255, axis=2)


def has_repeat_indicator(img: Image.Image, platform: str = "basalt") -> bool:
    """Check if any repeat indicator is visible in the screenshot.

    Detects the presence of white text pixels in the top-right indicator region.
    Returns True if the white pixel count exceeds the threshold.
    """
    import numpy as np
    crop_arr = _get_indicator_crop(img, platform)
    mask = _get_white_mask(crop_arr)
    count = int(np.sum(mask))
    logger.debug(f"Indicator white pixel count: {count}")
    return count >= INDICATOR_WHITE_THRESHOLD


def load_indicator_reference(name: str, platform: str = "basalt") -> "np.ndarray | None":
    """Load a reference white pixel mask for indicator comparison.

    Args:
        name: Reference name, e.g. "2x"
        platform: The emulator platform name.

    Returns:
        Boolean numpy array (height x width) where True = white pixel expected,
        or None if the reference file does not exist yet.
    """
    import numpy as np
    ref_path = REFERENCES_DIR / f"ref_{platform}_{name}_mask.png"
    if not ref_path.exists():
        return None
    ref_img = Image.open(ref_path).convert("L")
    return np.array(ref_img) > 128


def save_indicator_reference(name: str, mask: "np.ndarray", platform: str = "basalt") -> None:
    """Save a white pixel mask as the reference for future comparisons.

    Args:
        name: Reference name, e.g. "2x"
        mask: Boolean numpy array (height x width) where True = white pixel.
        platform: The emulator platform name.
    """
    import numpy as np
    ref_path = REFERENCES_DIR / f"ref_{platform}_{name}_mask.png"
    # Convert boolean mask to uint8 image (True=255, False=0)
    mask_img = Image.fromarray((mask.astype(np.uint8) * 255))
    mask_img.save(ref_path)
    logger.info(f"Saved indicator reference to {ref_path}")


def matches_indicator_reference(img: Image.Image, ref_name: str, platform: str = "basalt", tolerance: int = 5) -> bool:
    """Check if the indicator in a screenshot matches a named reference.

    Extracts the white pixel mask from the screenshot's indicator region
    and compares it to the stored reference mask. If no reference exists yet,
    saves the current mask as the reference and returns True.

    Args:
        img: Full Pebble screenshot.
        ref_name: Reference name, e.g. "2x".
        platform: The emulator platform name.
        tolerance: Maximum number of differing pixels allowed.

    Returns:
        True if the white pixel masks match within tolerance (or if a new reference was saved).
    """
    import numpy as np
    crop_arr = _get_indicator_crop(img, platform)
    mask = _get_white_mask(crop_arr)
    ref_mask = load_indicator_reference(ref_name, platform)
    if ref_mask is None:
        logger.info(f"No reference found for '{platform}_{ref_name}', saving current mask as reference")
        save_indicator_reference(ref_name, mask, platform)
        return True
    
    if mask.shape != ref_mask.shape:
        return False
        
    diff_count = int(np.sum(mask != ref_mask))
    matches = diff_count <= tolerance
    if not matches:
        logger.warning(f"Indicator mask mismatch for '{ref_name}' on {platform}: {diff_count} pixels differ (tolerance={tolerance})")
    return matches




class TestCreateTimer:
    """Tests for creating a timer via button presses."""

    def test_create_2_minute_timer(self, persistent_emulator):
        """
        Test creating a 2-minute timer via two Down button presses.

        Uses log-based assertions instead of OCR for reliable verification.

        This test verifies:
        1. After pressing Down twice, mode is "New"
        2. Timer shows approximately 2:00 (slightly less due to countdown)
        """
        from .conftest import LogCapture, assert_time_approximately, assert_mode, assert_paused

        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)  # Wait for pebble logs to connect
        capture.clear_state_queue()

        # Press Down twice to set 2 minutes
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)
        emulator.press_down()
        state = capture.wait_for_state(event="button_down", timeout=5.0)

        # Stop capture
        capture.stop()

        # Assert using structured log data
        assert state is not None, "Did not receive button_down state log"
        logger.info(f"After 2 Down presses - state: {state}")

        # Verify time is approximately 2:00 (timer is running so may have counted down slightly)
        assert_time_approximately(state, minutes=1, seconds=58, tolerance=5)
        assert_mode(state, "New")
        assert_paused(state, False)  # Timer runs immediately in ControlModeNew

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
        """Test that Up button increments timer by 20 minutes.

        Uses log-based assertions instead of OCR for reliable verification.
        The app logs TEST_STATE after each button press with exact timer values.

        Note: The timer runs immediately in ControlModeNew, so the displayed
        time will be slightly less than 20:00 due to elapsed time during startup.
        """
        from .conftest import LogCapture, assert_time_approximately, assert_mode, assert_paused

        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for pebble logs to connect (needs ~1s)
        time.sleep(1.0)
        capture.clear_state_queue()

        # Press Up button to add 20 minutes
        # This must happen before the 3-second new_expire_timer fires
        emulator.press_up()

        # Wait for button_up state log
        state = capture.wait_for_state(event="button_up", timeout=5.0)

        # Stop capture
        capture.stop()

        # Assert using structured log data
        assert state is not None, "Did not receive button_up state log"
        logger.info(f"After Up press - state: {state}")

        # Verify time is approximately 20:00 (timer is running so may have counted down slightly)
        assert_time_approximately(state, minutes=19, seconds=58, tolerance=5)
        assert_mode(state, "New")
        assert_paused(state, False)  # Timer runs immediately in ControlModeNew

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
        logger.info(f"  normalized: {normalized}")
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

        Note: All screenshots are taken first and OCR text extraction + assertions
        are deferred to the end, since OCR is slow and the elapsed time would
        interfere with the app's timing behavior.
        """
        emulator = persistent_emulator

        # --- Capture all screenshots first (OCR is deferred to avoid timing issues) ---

        # Set a 1 minute timer and wait for counting mode (3s auto-transition)
        emulator.press_down()
        time.sleep(4)

        # Take first screenshot - should show ~0:56 (counting mode)
        screenshot1 = emulator.screenshot("countdown_start")

        # Wait 5 seconds and take another screenshot
        time.sleep(5)
        screenshot2 = emulator.screenshot("countdown_after_5s")

        # --- Now perform OCR and assertions (after all screenshots captured) ---

        text1 = extract_text(screenshot1)
        logger.info(f"Countdown start text: {text1}")

        # Verify initial time shows ~1 minute (allowing for ~4s elapsed)
        # Uses has_time_pattern which handles OCR digit errors (e.g. 5→6)
        has_start_time = has_time_pattern(text1, minutes=1, tolerance=15)
        assert has_start_time, f"Expected time around 0:5x initially, got: {text1}"

        text2 = extract_text(screenshot2)
        logger.info(f"After 5s text: {text2}")

        # Timer should have counted down - screenshot1 and screenshot2 should differ
        assert screenshot1.tobytes() != screenshot2.tobytes(), (
            f"Display should change as timer counts down. Start: {text1}, After 5s: {text2}"
        )

    def test_timer_transitions_to_counting_mode(self, persistent_emulator):
        """
        Test that after 3 seconds of inactivity, the app transitions from
        'New' mode to 'Counting' mode.

        Uses log-based assertions to verify the mode transition without relying
        on OCR which can be unreliable.

        Note: The timer runs immediately in ControlModeNew, so the displayed
        time after button press will be slightly less than 1:00.
        """
        from .conftest import LogCapture, assert_mode, assert_paused, assert_time_approximately

        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)  # Wait for pebble logs to connect
        capture.clear_state_queue()

        # Press Down to set timer value (adds 1 minute)
        emulator.press_down()
        state_after_press = capture.wait_for_state(event="button_down", timeout=5.0)

        # Verify initial state after button press
        assert state_after_press is not None, "Did not receive button_down state log"
        logger.info(f"After Down press state: {state_after_press}")
        assert_mode(state_after_press, "New")
        # Timer is running immediately, so time will be slightly less than 1:00
        assert_time_approximately(state_after_press, minutes=0, seconds=58, tolerance=5)
        assert_paused(state_after_press, False)  # Timer runs immediately in ControlModeNew

        # Wait for mode transition (3 seconds + buffer)
        state_after_transition = capture.wait_for_state(event="mode_change", timeout=5.0)

        capture.stop()

        # Verify state after mode transition
        assert state_after_transition is not None, "Did not receive mode_change state log"
        logger.info(f"After transition state: {state_after_transition}")
        assert_mode(state_after_transition, "Counting")
        assert_paused(state_after_transition, False)  # Timer is running in Counting mode
        # Timer should be approximately 55s (1:00 - elapsed time during setup and transition)
        assert_time_approximately(state_after_transition, minutes=0, seconds=55, tolerance=8)


class TestChronoMode:
    """Tests for stopwatch (chrono) mode functionality."""

    def test_chrono_mode_counts_up(self, persistent_emulator):
        """
        Test that in chrono mode (no timer set), the stopwatch counts up.

        When the app starts fresh with no timer value set (0:00),
        after the 3-second timeout it begins counting up as a stopwatch.

        Note: The app auto-backgrounds chrono mode after 7 seconds
        (AUTO_BACKGROUND_CHRONO in main.c), so both screenshots must be
        captured within that window. All OCR text extraction + assertions
        are deferred to the end, since OCR is slow and the elapsed time
        would interfere with the app's timing behavior.
        """
        emulator = persistent_emulator

        # --- Capture all screenshots first (OCR is deferred to avoid timing issues) ---

        # Wait for the app to enter chrono mode (timer at 0:00 with no value set)
        # The 3-second inactivity timeout transitions from New to Counting/Chrono mode.
        # After that, a 7-second auto-quit timer starts (AUTO_BACKGROUND_CHRONO in
        # main.c), so both screenshots must be captured within ~7 seconds of the
        # mode transition. Total time from app open must stay under ~10 seconds.
        time.sleep(3.5)  # Wait for transition to chrono mode (3s timeout + buffer)

        screenshot1 = emulator.screenshot("chrono_start")

        # Wait 2 seconds (staying within the 7s auto-quit window) and verify counting up
        time.sleep(2)
        screenshot2 = emulator.screenshot("chrono_after_2s")

        # Press Down to cancel the auto-quit timer (keeps the app alive for
        # the teardown to properly quit via long-press Down + reset_on_init).
        # In counting/chrono mode, Down just refreshes the display and cancels
        # the quit timer without changing the timer value.
        emulator.press_down()

        # --- Now perform OCR and assertions (after all screenshots captured) ---

        text1 = extract_text(screenshot1)
        logger.info(f"Chrono mode start: {text1}")

        # Should show small time value (0:0x) - stopwatch just started
        normalized1 = normalize_time_text(text1)
        time_patterns_start = ["0:0"]
        has_start_time = any(pattern in normalized1 for pattern in time_patterns_start)
        assert has_start_time, f"Expected chrono to show '0:0x' at start, got: {text1}"

        text2 = extract_text(screenshot2)
        logger.info(f"Chrono after 3s: {text2}")

        # Should now show higher time (0:0x where x > start)
        normalized2 = normalize_time_text(text2)
        time_patterns_later = ["0:0", "0:1"]
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

        Note: All screenshots are taken first and OCR text extraction + assertions
        are deferred to the end, since OCR is slow and the elapsed time would
        interfere with the app's timing behavior.
        """
        emulator = persistent_emulator

        # --- Capture all screenshots first (OCR is deferred to avoid timing issues) ---

        # Set a timer and wait for it to start counting
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode

        # Take screenshot while running
        running = emulator.screenshot("playpause_running")

        # Press Select to pause
        emulator.press_select()
        time.sleep(0.5)
        paused = emulator.screenshot("playpause_paused")

        # Wait a moment - if paused, the time value shouldn't change
        time.sleep(2)
        still_paused = emulator.screenshot("playpause_still_paused")

        # Press Select again to resume
        emulator.press_select()
        time.sleep(2)
        resumed = emulator.screenshot("playpause_resumed")

        # --- Now perform OCR and assertions (after all screenshots captured) ---

        text_running = extract_text(running)
        logger.info(f"Running timer: {text_running}")

        text_paused = extract_text(paused)
        logger.info(f"Paused timer: {text_paused}")

        text_still_paused = extract_text(still_paused)
        logger.info(f"Still paused: {text_still_paused}")

        # The paused screenshots should show the same time (timer stopped)
        assert paused.tobytes() == still_paused.tobytes(), (
            f"Display should not change while paused. Before: {text_paused}, After: {text_still_paused}"
        )

        text_resumed = extract_text(resumed)
        logger.info(f"Resumed timer: {text_resumed}")

        # Display should have changed (timer resumed counting)
        assert still_paused.tobytes() != resumed.tobytes(), (
            f"Display should change after resuming. Paused: {text_still_paused}, Resumed: {text_resumed}"
        )


class TestTimerStartsImmediately:
    """Tests that verify timer countdown starts immediately in ControlModeNew."""

    def test_timer_counts_down_during_setup(self, persistent_emulator):
        """
        Test that timer starts counting down immediately when buttons are pressed.

        This test verifies that the timer begins counting down right away when
        the user starts adding time in ControlModeNew, rather than waiting for
        the mode to expire (3 seconds of inactivity).

        Test approach:
        1. Press Down 6 times with 2-second sleeps between each press
           to build up to a 6-minute timer over ~10 seconds
        2. Capture the timer state after all presses
        3. If the timer is < 5:50, the timer was counting down during setup (PASS)
        4. If the timer is >= 5:50, the timer waited to start counting (FAIL)

        Expected behavior (PASS): Timer value should be around 5:50 or less
        Current buggy behavior (FAIL): Timer stays at 6:00 during setup
        """
        from .conftest import LogCapture, parse_time

        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)  # Wait for pebble logs to connect
        capture.clear_state_queue()

        # Press Down 6 times with 2 second sleeps to set a 6 minute timer
        # This takes about 10 seconds total
        for i in range(6):
            emulator.press_down()
            if i < 5:  # Don't sleep after the last press
                time.sleep(2)

        # Wait a moment for the final state to be logged
        time.sleep(0.5)

        # Drain all button_down events from the queue and get the last one
        # (There will be 6 button_down events, we want the most recent)
        state = None
        while True:
            next_state = capture.wait_for_state(event="button_down", timeout=0.5)
            if next_state is None:
                break
            state = next_state

        # Stop capture
        capture.stop()

        assert state is not None, "Did not receive button_down state log"
        logger.info(f"After 6 Down presses with 2s delays - state: {state}")

        # Parse the time from the state
        timer_value = state.get('t', '0:00')
        minutes, seconds = parse_time(timer_value)
        total_seconds = minutes * 60 + seconds

        # Threshold: 5:50 = 350 seconds
        # If timer counted down during setup, it should be less than 5:50
        # If timer waited (current buggy behavior), it would be at or near 6:00 (360 seconds)
        threshold_seconds = 350  # 5:50

        assert total_seconds < threshold_seconds, (
            f"Timer should have counted down during setup! "
            f"Expected time < 5:50 (350s), got {timer_value} ({total_seconds}s). "
            f"This indicates the timer is waiting for ControlModeNew to expire "
            f"instead of counting down immediately."
        )

    def test_chrono_has_elapsed_time_when_mode_expires(self, persistent_emulator):
        """
        Test that chrono mode already has elapsed time when ControlModeNew expires.

        When the app starts and no buttons are pressed, after 3 seconds the
        ControlModeNew expires and transitions to ControlModeCounting (chrono mode).
        The timer should already have ~3 seconds counted, not start from 0:00.

        This verifies that the timer is running during ControlModeNew, not just
        starting when the mode transitions.

        Expected behavior (PASS): Chrono shows ~3 seconds when mode changes
        Old buggy behavior (FAIL): Chrono would start at 0:00
        """
        from .conftest import LogCapture, parse_time, assert_mode

        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)  # Wait for pebble logs to connect
        capture.clear_state_queue()

        # Don't press any buttons - just wait for the mode to expire
        # The 3-second timeout will transition from ControlModeNew to ControlModeCounting
        state = capture.wait_for_state(event="mode_change", timeout=5.0)

        # Stop capture
        capture.stop()

        assert state is not None, "Did not receive mode_change state log"
        logger.info(f"Mode change state: {state}")

        # Verify we're now in Counting mode (chrono since no time was added)
        assert_mode(state, "Counting")

        # Parse the time - it should be around 3 seconds (the timeout duration)
        timer_value = state.get('t', '0:00')
        minutes, seconds = parse_time(timer_value)
        total_seconds = minutes * 60 + seconds

        # The timer should have ~3 seconds elapsed (allow 1-5 seconds for timing tolerance)
        min_expected = 1  # At least 1 second
        max_expected = 6  # At most 6 seconds (3s timeout + some slack)

        assert min_expected <= total_seconds <= max_expected, (
            f"Chrono should have ~3 seconds when mode expires! "
            f"Expected {min_expected}-{max_expected}s, got {timer_value} ({total_seconds}s). "
            f"This indicates the timer wasn't running during ControlModeNew."
        )


class TestLongPressReset:
    """Tests for long press reset functionality."""

    def test_long_press_select_resets_timer(self, persistent_emulator):
        """
        Test that long pressing Select restarts the timer in counting mode.

        In counting mode, a long press on Select should restart the timer
        to its original value (base_length_ms). The app must first transition
        from ControlModeNew to ControlModeCounting (3-second inactivity timeout)
        before the long press, otherwise the timer would be reset to 0:00 instead.

        Note: All screenshots are taken first and OCR text extraction + assertions
        are deferred to the end, since OCR is slow and the elapsed time would
        interfere with the app's timing behavior.
        """
        emulator = persistent_emulator

        # --- Capture all screenshots first (OCR is deferred to avoid timing issues) ---

        # Set a timer with some value
        emulator.press_up()  # Add 20 minutes

        # Wait for the 3-second inactivity timeout to transition
        # from ControlModeNew to ControlModeCounting
        time.sleep(4)
        before_reset = emulator.screenshot("reset_before")

        # Long press Select to restart the timer
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)  # Hold for reset threshold
        emulator.release_buttons()
        time.sleep(0.5)

        after_reset = emulator.screenshot("reset_after")

        # --- Now perform OCR and assertions (after all screenshots captured) ---

        text_before = extract_text(before_reset)
        logger.info(f"Before reset: {text_before}")

        # Verify we have a non-zero timer (should show ~20 minutes, counted down ~4s)
        normalized_before = normalize_time_text(text_before)
        time_patterns_before = ["19:", "19.", "19;", "20:", "20."]
        has_time_before = any(pattern in normalized_before for pattern in time_patterns_before)
        if not has_time_before:
            has_time_before = has_time_pattern(text_before, minutes=20, tolerance=15)
        assert has_time_before, f"Expected timer showing ~20 minutes before reset, got: {text_before}"

        text_after = extract_text(after_reset)
        logger.info(f"After reset: {text_after}")

        # After long press SELECT in counting mode, the timer restarts to its
        # original value (~20 minutes). Verify ~20 minutes is shown.
        normalized_after = normalize_time_text(text_after)
        time_patterns_after = ["19:", "19.", "19;", "20:", "20."]
        has_time_after = any(pattern in normalized_after for pattern in time_patterns_after)
        if not has_time_after:
            has_time_after = has_time_pattern(text_after, minutes=20, tolerance=15)
        assert has_time_after, f"Expected timer showing ~20 minutes after restart, got: {text_after}"
