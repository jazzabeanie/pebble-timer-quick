"""
Test Cases: Button icon tests.

Verifies that icons appear beside buttons in every app state where a button
has functionality. Tests use pixel-based screenshot comparison against
per-icon reference masks stored in screenshots/icon_refs/.

All button icons are implemented including alarm mode Up button icons.
Hold icons are positioned beside (toward screen center) the standard press icons.

31 tests total per platform (all passing).
"""

import logging
import os
import pytest
from pathlib import Path
from PIL import Image
import numpy as np
import time

from .conftest import Button, EmulatorHelper, PLATFORMS
from .test_create_timer import extract_text, normalize_time_text

# Configure module logger
logger = logging.getLogger(__name__)

# Directory for icon reference masks
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
ICON_REFS_DIR = SCREENSHOTS_DIR / "icon_refs"
ICON_REFS_DIR.mkdir(parents=True, exist_ok=True)

# --- Icon Crop Regions (basalt 144x168) ---
# Standard press regions
REGION_BACK = (0, 5, 35, 40)
REGION_UP = (109, 5, 144, 40)
REGION_SELECT = (122, 71, 144, 96)
REGION_DOWN = (109, 128, 144, 163)

# Long press sub-regions (beside standard icons, toward screen center)
REGION_LONG_UP = (92, 10, 117, 35)
REGION_LONG_SELECT = (105, 71, 130, 96)
REGION_LONG_DOWN = (92, 133, 117, 158)


# --- Helper Functions ---

def crop_icon_region(img, region):
    """Crop a screenshot to the given region tuple (left, top, right, bottom)."""
    return img.crop(region)


def _get_dominant_color(img_array):
    """Get the dominant (most common) color in an image array.

    Returns the color as an (R, G, B) tuple.
    """
    pixels = img_array[:, :, :3].reshape(-1, 3)
    unique, counts = np.unique(pixels, axis=0, return_counts=True)
    dominant_idx = np.argmax(counts)
    return tuple(unique[dominant_idx])


def has_icon_content(img, region, threshold=100):
    """Check if the cropped region has >= threshold non-background pixels.

    Background is determined by the dominant color in the region.
    Note: Timer display digits can produce 200-400+ non-bg pixels in
    regions that overlap with the main display. Use matches_icon_reference()
    for reliable icon detection.

    Args:
        img: Full Pebble screenshot (PIL Image).
        region: Crop tuple (left, top, right, bottom).
        threshold: Minimum non-background pixel count.

    Returns:
        True if the region contains enough non-background pixels.
    """
    crop = crop_icon_region(img, region)
    crop_arr = np.array(crop)
    bg_color = _get_dominant_color(crop_arr)
    non_bg_mask = ~np.all(crop_arr[:, :, :3] == bg_color, axis=2)
    count = int(np.sum(non_bg_mask))
    logger.debug(f"Icon content: region={region}, bg={bg_color}, non_bg_pixels={count}")
    return count >= threshold


def _get_non_bg_mask(crop_arr):
    """Create a boolean mask of non-background pixels.

    Background is the dominant color in the crop.
    """
    bg_color = _get_dominant_color(crop_arr)
    return ~np.all(crop_arr[:, :, :3] == bg_color, axis=2)


def matches_icon_reference(img, region, ref_name, auto_save=True, tolerance=0):
    """Compare the icon region's non-background pixel mask against a stored reference.

    Args:
        img: Full Pebble screenshot (PIL Image).
        region: Crop tuple (left, top, right, bottom).
        ref_name: Reference name, e.g. "silence" loads "ref_basalt_silence_mask.png".
        auto_save: If True and no reference exists, save current mask as reference
                   and return True. If False and no reference exists, return False.
        tolerance: Maximum number of differing pixels allowed (default 0 for exact
                   match). Useful for regions that overlap with flashing UI elements
                   like the repeat counter indicator.

    Returns:
        True if masks match within tolerance (or if a new reference was saved).
    """
    crop = crop_icon_region(img, region)
    crop_arr = np.array(crop)
    mask = _get_non_bg_mask(crop_arr)

    ref_path = ICON_REFS_DIR / f"ref_basalt_{ref_name}_mask.png"
    if not ref_path.exists():
        if auto_save:
            mask_img = Image.fromarray((mask.astype(np.uint8) * 255))
            mask_img.save(ref_path)
            logger.info(f"Saved icon reference to {ref_path}")
            return True
        else:
            logger.info(f"No reference found for '{ref_name}' (auto_save=False)")
            return False

    # Load and compare
    ref_img = Image.open(ref_path).convert("L")
    ref_mask = np.array(ref_img) > 128
    diff_count = int(np.sum(mask != ref_mask))
    matches = diff_count <= tolerance
    if not matches:
        logger.warning(f"Icon mask mismatch for '{ref_name}': {diff_count} pixels differ (tolerance={tolerance})")
    elif diff_count > 0:
        logger.debug(f"Icon mask for '{ref_name}': {diff_count} pixels differ (within tolerance={tolerance})")
    return matches


# --- Short timer setup (reused from test_timer_workflows) ---

def setup_short_timer(emulator, seconds=4):
    """Set up a short timer with the given number of seconds.

    See test_timer_workflows.py for detailed explanation.
    """
    logger.info(f"[{emulator.platform}] Setting up {seconds}s timer for icon test")

    # Wait for transition to chrono mode (0:00 counting up)
    time.sleep(2.5)

    # Pause the chrono
    emulator.press_select()
    time.sleep(0.3)

    # Long press Select to enter ControlModeEditSec
    emulator.hold_button(Button.SELECT)
    time.sleep(1)
    emulator.release_buttons()
    time.sleep(0.3)

    # Press Down N times to add N seconds
    for i in range(seconds):
        emulator.press_down()
        time.sleep(0.2)

    logger.info(f"[{emulator.platform}] Short timer set to {seconds}s, waiting for expire")

    # Wait for expire timer (3s after last button press)
    time.sleep(3.5)

    # Press Select to unpause the timer
    emulator.press_select()
    time.sleep(0.3)

    logger.info(f"[{emulator.platform}] Short timer started, counting down from {seconds}s")


def enter_alarm_state(emulator, seconds=4):
    """Set up a short timer and wait for it to complete (alarm/vibrating state).

    Returns the screenshot taken in alarm state.
    """
    setup_short_timer(emulator, seconds=seconds)
    # Wait for countdown to complete + vibration start
    time.sleep(seconds + 1.5)
    # Take screenshot in alarm state
    screenshot = emulator.screenshot("alarm_state")
    return screenshot


# --- Fixtures ---

@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """Module-scoped fixture that launches the emulator once per platform."""
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")

    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Warm-up cycle
    logger.info(f"[{platform}] Starting warm-up cycle")
    helper.wipe()
    helper.install()
    logger.info(f"[{platform}] Waiting for emulator to stabilize (2s)")
    time.sleep(2)

    # Quit app to set persist state
    logger.info(f"[{platform}] Holding down button to quit app and set persist state")
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    time.sleep(0.5)

    # Navigate to launcher
    helper.press_select()
    time.sleep(0.5)

    logger.info(f"[{platform}] Emulator ready for tests")

    yield helper

    logger.info(f"[{platform}] Tearing down - killing emulator")
    helper.kill()


# ============================================================
# 3.1 Alarm / Vibrating State
# ============================================================

class TestAlarmIcons:
    """Tests for icons displayed during the alarm/vibrating state.

    Five icons drawn in alarm state: silence (Back), reset (Up),
    reset hold icon (Long Up), pause (Select), and snooze (Down).
    """

    def _enter_alarm(self, emulator):
        """Enter alarm state and return screenshot."""
        return enter_alarm_state(emulator, seconds=4)

    def test_alarm_back_icon_silence(self, persistent_emulator):
        """Verify the silence icon (Back button) is drawn during alarm state."""
        emulator = persistent_emulator
        screenshot = self._enter_alarm(emulator)

        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected silence icon content in Back button region during alarm state"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "silence"), (
            "Silence icon does not match reference mask"
        )

    def test_alarm_up_icon_repeat(self, persistent_emulator):
        """Verify the reset icon (Up button) is drawn during alarm state."""
        emulator = persistent_emulator
        screenshot = self._enter_alarm(emulator)

        assert has_icon_content(screenshot, REGION_UP), (
            "Expected reset icon content in Up button region during alarm state"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "alarm_repeat"), (
            "Reset icon does not match reference mask"
        )

    def test_alarm_long_up_icon_reset(self, persistent_emulator):
        """Verify the hold icon (reset) beside the Up button during alarm state."""
        emulator = persistent_emulator
        screenshot = self._enter_alarm(emulator)

        assert matches_icon_reference(screenshot, REGION_LONG_UP, "alarm_long_up"), (
            "Alarm long-press Up icon does not match reference mask"
        )

    def test_alarm_select_icon_pause(self, persistent_emulator):
        """Verify the pause icon (Select button) is drawn during alarm state."""
        emulator = persistent_emulator
        screenshot = self._enter_alarm(emulator)

        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected pause icon content in Select button region during alarm state"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "pause"), (
            "Pause icon does not match reference mask"
        )

    def test_alarm_down_icon_snooze(self, persistent_emulator):
        """Verify the snooze icon (Down button) is drawn during alarm state."""
        emulator = persistent_emulator
        screenshot = self._enter_alarm(emulator)

        assert has_icon_content(screenshot, REGION_DOWN), (
            "Expected snooze icon content in Down button region during alarm state"
        )
        assert matches_icon_reference(screenshot, REGION_DOWN, "snooze"), (
            "Snooze icon does not match reference mask"
        )


# ============================================================
# 3.2 ControlModeNew (Setting New Timer)
# ============================================================

class TestNewModeIcons:
    """Tests for icons in ControlModeNew (setting a new timer).

    Icons: +1hr (Back), +20min (Up), +5min (Select), +1min (Down),
    direction toggle (Long Up), reset (Long Select), quit (Long Down).
    """

    def test_new_back_icon(self, persistent_emulator):
        """Verify +1hr indicator icon for Back button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected +1hr icon content in Back button region in New mode"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "new_back"), (
            "+1hr icon does not match reference mask"
        )

    def test_new_up_icon(self, persistent_emulator):
        """Verify +20min indicator icon for Up button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected +20min icon content in Up button region in New mode"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "new_up"), (
            "+20min icon does not match reference mask"
        )

    def test_new_select_icon(self, persistent_emulator):
        """Verify +5min indicator icon for Select button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected +5min icon content in Select button region in New mode"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "new_select"), (
            "+5min icon does not match reference mask"
        )

    def test_new_down_icon(self, persistent_emulator):
        """Verify +1min indicator icon for Down button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert has_icon_content(screenshot, REGION_DOWN), (
            "Expected +1min icon content in Down button region in New mode"
        )
        assert matches_icon_reference(screenshot, REGION_DOWN, "new_down"), (
            "+1min icon does not match reference mask"
        )

    def test_new_long_up_direction_toggle(self, persistent_emulator):
        """Verify direction toggle icon exists in long-press Up sub-region in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode_long_up")
        assert matches_icon_reference(screenshot, REGION_LONG_UP, "new_long_up"), (
            "Direction toggle icon does not match reference mask"
        )

    def test_new_long_select_icon(self, persistent_emulator):
        """Verify reset indicator for long-press Select in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_LONG_SELECT, "new_long_select"), (
            "Reset icon does not match reference mask"
        )

    def test_new_long_down_icon(self, persistent_emulator):
        """Verify quit indicator for long-press Down in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_LONG_DOWN, "new_long_down"), (
            "Quit icon does not match reference mask"
        )


# ============================================================
# 3.3 ControlModeEditSec (Editing Seconds)
# ============================================================

class TestEditSecIcons:
    """Tests for icons in ControlModeEditSec.

    Icons: +30s (Back), +20s (Up), +5s (Select), +1s (Down),
    direction toggle (Long Up).
    """

    def _enter_editsec(self, emulator):
        """Enter ControlModeEditSec mode.

        From a fresh app start:
        1. Wait for chrono mode (3.5s)
        2. Pause chrono (Select)
        3. Long press Select to enter EditSec
        """
        time.sleep(2.5)
        emulator.press_select()
        time.sleep(0.3)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.3)
        return emulator.screenshot("editsec_mode")

    def test_editsec_back_icon(self, persistent_emulator):
        """Verify +30s indicator icon for Back button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected +30s icon content in Back button region in EditSec mode"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "editsec_back"), (
            "+30s icon does not match reference mask"
        )

    def test_editsec_up_icon(self, persistent_emulator):
        """Verify +20s indicator icon for Up button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected +20s icon content in Up button region in EditSec mode"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "editsec_up"), (
            "+20s icon does not match reference mask"
        )

    def test_editsec_select_icon(self, persistent_emulator):
        """Verify +5s indicator icon for Select button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected +5s icon content in Select button region in EditSec mode"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "editsec_select"), (
            "+5s icon does not match reference mask"
        )

    def test_editsec_down_icon(self, persistent_emulator):
        """Verify +1s indicator icon for Down button in EditSec mode.

        Note: has_icon_content threshold check skipped because the "+1" icon
        has fewer non-bg pixels than the default threshold of 100.
        """
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert matches_icon_reference(screenshot, REGION_DOWN, "editsec_down"), (
            "+1s icon does not match reference mask"
        )

    def test_editsec_long_up_direction_toggle(self, persistent_emulator):
        """Verify direction toggle indicator for long-press Up in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_UP, "editsec_long_up"), (
            "Direction toggle icon does not match reference mask in EditSec mode"
        )


# ============================================================
# 3.4 ControlModeCounting (Timer Running)
# ============================================================

class TestCountingIcons:
    """Tests for icons in ControlModeCounting (timer running).

    Icons: BG (Back), Edit (Up), Pause (Select), Details (Down),
    Repeat Enable (Long Up), Reset (Long Select), Quit (Long Down).
    """

    def _enter_counting(self, emulator):
        """Enter counting mode: press Down, wait for 3s auto-transition."""
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode
        return emulator.screenshot("counting_mode")

    def test_counting_back_icon(self, persistent_emulator):
        """Verify exit/background indicator for Back button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected BG icon content in Back button region in Counting mode"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "counting_back"), (
            "BG icon does not match reference mask"
        )

    def test_counting_up_icon(self, persistent_emulator):
        """Verify edit indicator for Up button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected Edit icon content in Up button region in Counting mode"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "counting_up"), (
            "Edit icon does not match reference mask"
        )

    def test_counting_select_icon(self, persistent_emulator):
        """Verify pause indicator for Select button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected Pause icon content in Select button region in Counting mode"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "counting_select"), (
            "Pause icon does not match reference mask"
        )

    def test_counting_down_icon(self, persistent_emulator):
        """Verify details/refresh indicator for Down button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert has_icon_content(screenshot, REGION_DOWN), (
            "Expected Details icon content in Down button region in Counting mode"
        )
        assert matches_icon_reference(screenshot, REGION_DOWN, "counting_down"), (
            "Details icon does not match reference mask"
        )

    def test_counting_long_up_icon(self, persistent_emulator):
        """Verify enable repeat indicator for long-press Up in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_UP, "counting_long_up"), (
            "Enable-repeat icon does not match reference mask"
        )

    def test_counting_long_select_icon(self, persistent_emulator):
        """Verify restart indicator for long-press Select in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_SELECT, "counting_long_select"), (
            "Restart icon does not match reference mask"
        )

    def test_counting_long_down_icon(self, persistent_emulator):
        """Verify quit indicator for long-press Down in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_DOWN, "counting_long_down"), (
            "Quit icon does not match reference mask"
        )


# ============================================================
# 3.5 ControlModeCounting + Paused
# ============================================================

class TestPausedIcons:
    """Tests for icons when timer is paused.

    Icons: Play (Select). Other buttons share Counting mode icons.
    """

    def test_paused_select_icon_play(self, persistent_emulator):
        """Verify play icon for Select button when timer is paused."""
        emulator = persistent_emulator

        # Set timer and enter counting mode
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode

        # Pause the timer
        emulator.press_select()
        time.sleep(0.5)

        screenshot = emulator.screenshot("paused_mode")
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected Play icon content in Select button region when paused"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "paused_play"), (
            "Play icon does not match reference mask"
        )


# ============================================================
# 3.6 ControlModeCounting + Chrono (Counting Up)
# ============================================================

class TestChronoIcons:
    """Tests for icons in chrono mode (counting up after timer completion).

    Icons: Pause (Select), Reset (Long Select).
    """

    def _enter_chrono(self, emulator):
        """Enter chrono mode: set short timer, wait for completion, silence alarm.

        Returns screenshot in chrono mode.
        """
        setup_short_timer(emulator, seconds=4)
        # Wait for countdown to complete + buffer
        time.sleep(5.5)
        # Press Back to silence alarm (stays in chrono mode)
        emulator.press_back()
        time.sleep(0.5)
        return emulator.screenshot("chrono_mode")

    def test_chrono_select_icon(self, persistent_emulator):
        """Verify pause indicator for Select button in chrono mode."""
        emulator = persistent_emulator
        screenshot = self._enter_chrono(emulator)

        # Cancel quit timer
        emulator.press_down()

        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected Pause icon content in Select button region in chrono mode"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "chrono_select"), (
            "Pause icon does not match reference mask in chrono mode"
        )

    def test_chrono_long_select_icon(self, persistent_emulator):
        """Verify reset indicator for long-press Select in chrono mode."""
        emulator = persistent_emulator
        screenshot = self._enter_chrono(emulator)

        # Cancel quit timer
        emulator.press_down()

        assert matches_icon_reference(screenshot, REGION_LONG_SELECT, "chrono_long_select"), (
            "Reset icon does not match reference mask in chrono mode"
        )


# ============================================================
# 3.7 ControlModeEditRepeat
# ============================================================

class TestEditRepeatIcons:
    """Tests for icons in ControlModeEditRepeat mode.

    Icons: Reset Count (Back), +20 (Up), +5 (Select), +1 (Down).
    """

    def _enter_editrepeat(self, emulator):
        """Enter EditRepeat mode: set timer, wait for counting, long press Up.

        Returns screenshot in EditRepeat mode.
        """
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode

        # Long press Up to enter EditRepeat
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()

        # Wait 0.5s to shift flash phase for consistent screenshots
        time.sleep(0.5)
        return emulator.screenshot("editrepeat_mode")

    def test_editrepeat_back_icon(self, persistent_emulator):
        """Verify reset count indicator for Back button in EditRepeat mode.

        Tolerance of 20 pixels for minor rendering variations from timer
        digits near the Back icon region.
        """
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected Reset Count icon content in Back button region in EditRepeat mode"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "editrepeat_back", tolerance=20), (
            "Reset Count icon does not match reference mask"
        )

    def test_editrepeat_up_icon(self, persistent_emulator):
        """Verify +20 repeats indicator for Up button in EditRepeat mode.

        Tolerance of 60 pixels because REGION_UP (109,5,144,40) overlaps with
        the flashing repeat indicator "_x" at (94,0,144,30). The indicator
        flashes on/off at 1000ms intervals, causing up to ~50 pixel differences.
        """
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected +20 repeats icon content in Up button region in EditRepeat mode"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "editrepeat_up", tolerance=60), (
            "+20 repeats icon does not match reference mask"
        )

    def test_editrepeat_select_icon(self, persistent_emulator):
        """Verify +5 repeats indicator for Select button in EditRepeat mode.

        Tolerance of 30 pixels for timer display digit variation in the
        Select crop region across runs.
        """
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected +5 repeats icon content in Select button region in EditRepeat mode"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "editrepeat_select", tolerance=30), (
            "+5 repeats icon does not match reference mask"
        )

    def test_editrepeat_down_icon(self, persistent_emulator):
        """Verify +1 repeat indicator for Down button in EditRepeat mode.

        Note: has_icon_content threshold check skipped because the "+1" icon
        has fewer non-bg pixels than the default threshold of 100.
        """
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert matches_icon_reference(screenshot, REGION_DOWN, "editrepeat_down"), (
            "+1 repeat icon does not match reference mask"
        )
