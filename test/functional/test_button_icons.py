"""
Test Cases: Button icon tests.

Verifies that icons appear beside buttons in every app state where a button
has functionality. Tests use pixel-based screenshot comparison against
per-icon reference masks.

Icons that currently exist (alarm state: silence, pause, snooze) are tested
with exact reference mask comparison. Icons that do not yet exist are marked
with @pytest.mark.xfail(strict=True) and require a matching reference mask
in screenshots/icon_refs/. Since no reference mask exists for unimplemented
icons, these tests correctly fail (xfail).

When a new icon is implemented:
1. Generate a reference mask (run the test once to auto-generate, or manually)
2. Commit the reference mask PNG to screenshots/icon_refs/
3. Remove the @pytest.mark.xfail decorator from the test
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

# Long press sub-regions
REGION_LONG_UP = (109, 25, 127, 40)
REGION_LONG_SELECT = (122, 81, 136, 96)
REGION_LONG_DOWN = (109, 128, 127, 143)


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


def matches_icon_reference(img, region, ref_name, auto_save=True):
    """Compare the icon region's non-background pixel mask against a stored reference.

    Args:
        img: Full Pebble screenshot (PIL Image).
        region: Crop tuple (left, top, right, bottom).
        ref_name: Reference name, e.g. "silence" loads "ref_basalt_silence_mask.png".
        auto_save: If True and no reference exists, save current mask as reference
                   and return True. If False and no reference exists, return False.

    Returns:
        True if masks match (or if a new reference was saved with auto_save=True).
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
    matches = np.array_equal(mask, ref_mask)
    if not matches:
        diff_count = int(np.sum(mask != ref_mask))
        logger.warning(f"Icon mask mismatch for '{ref_name}': {diff_count} pixels differ")
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

    Three icons are currently drawn in alarm state: silence (Back),
    pause (Select), and snooze (Down). The repeat icon (Up) resource
    exists but its drawing code is commented out.
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

    @pytest.mark.xfail(
        strict=True,
        reason="Repeat/reset icon drawing is commented out in drawing.c:446-447"
    )
    def test_alarm_up_icon_repeat(self, persistent_emulator):
        """Verify the repeat/reset icon (Up button) during alarm state.

        The IMAGE_REPEAT_ICON resource exists but the drawing code at
        drawing.c:446-447 is commented out. Uses reference mask matching
        (auto_save=False) to avoid false positives from progress ring pixels.
        """
        emulator = persistent_emulator
        screenshot = self._enter_alarm(emulator)

        assert matches_icon_reference(screenshot, REGION_UP, "alarm_repeat", auto_save=False), (
            "No reference mask for repeat icon (icon not yet drawn)"
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

    No icons are currently drawn in this mode. All tests are xfail.
    """

    @pytest.mark.xfail(strict=True, reason="No +1hr icon implemented yet")
    def test_new_back_icon(self, persistent_emulator):
        """Verify +1hr indicator icon for Back button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_BACK, "new_back", auto_save=False), (
            "No reference mask for +1hr icon (icon not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +20min icon implemented yet")
    def test_new_up_icon(self, persistent_emulator):
        """Verify +20min indicator icon for Up button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_UP, "new_up", auto_save=False), (
            "No reference mask for +20min icon (icon not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +5min icon implemented yet")
    def test_new_select_icon(self, persistent_emulator):
        """Verify +5min indicator icon for Select button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_SELECT, "new_select", auto_save=False), (
            "No reference mask for +5min icon (icon not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +1min icon implemented yet")
    def test_new_down_icon(self, persistent_emulator):
        """Verify +1min indicator icon for Down button in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_DOWN, "new_down", auto_save=False), (
            "No reference mask for +1min icon (icon not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="Direction toggle has no visual representation in drawing.c")
    def test_new_long_up_direction_toggle(self, persistent_emulator):
        """Verify screen changes after long press Up (direction toggle) in New mode."""
        emulator = persistent_emulator

        # Take baseline screenshot
        baseline = emulator.screenshot("new_baseline")

        # Long press Up to toggle direction
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.5)

        after_toggle = emulator.screenshot("new_after_direction_toggle")

        # Check for icon in long-press Up sub-region
        assert matches_icon_reference(after_toggle, REGION_LONG_UP, "new_long_up", auto_save=False), (
            "No reference mask for direction toggle icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No reset icon implemented for long-press Select in New mode")
    def test_new_long_select_icon(self, persistent_emulator):
        """Verify reset indicator for long-press Select in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_LONG_SELECT, "new_long_select", auto_save=False), (
            "No reference mask for reset icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No quit icon implemented for long-press Down in New mode")
    def test_new_long_down_icon(self, persistent_emulator):
        """Verify quit indicator for long-press Down in New mode."""
        emulator = persistent_emulator
        screenshot = emulator.screenshot("new_mode")
        assert matches_icon_reference(screenshot, REGION_LONG_DOWN, "new_long_down", auto_save=False), (
            "No reference mask for quit icon (not yet implemented)"
        )


# ============================================================
# 3.3 ControlModeEditSec (Editing Seconds)
# ============================================================

class TestEditSecIcons:
    """Tests for icons in ControlModeEditSec.

    No icons are currently drawn in this mode. All tests are xfail.
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

    @pytest.mark.xfail(strict=True, reason="No +30s icon implemented yet")
    def test_editsec_back_icon(self, persistent_emulator):
        """Verify +30s indicator icon for Back button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert matches_icon_reference(screenshot, REGION_BACK, "editsec_back", auto_save=False), (
            "No reference mask for +30s icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +20s icon implemented yet")
    def test_editsec_up_icon(self, persistent_emulator):
        """Verify +20s indicator icon for Up button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert matches_icon_reference(screenshot, REGION_UP, "editsec_up", auto_save=False), (
            "No reference mask for +20s icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +5s icon implemented yet")
    def test_editsec_select_icon(self, persistent_emulator):
        """Verify +5s indicator icon for Select button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert matches_icon_reference(screenshot, REGION_SELECT, "editsec_select", auto_save=False), (
            "No reference mask for +5s icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +1s icon implemented yet")
    def test_editsec_down_icon(self, persistent_emulator):
        """Verify +1s indicator icon for Down button in EditSec mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editsec(emulator)
        assert matches_icon_reference(screenshot, REGION_DOWN, "editsec_down", auto_save=False), (
            "No reference mask for +1s icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No direction toggle icon in EditSec mode")
    def test_editsec_long_up_direction_toggle(self, persistent_emulator):
        """Verify direction toggle indicator for long-press Up in EditSec mode."""
        emulator = persistent_emulator
        self._enter_editsec(emulator)

        # Long press Up to toggle direction
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.5)

        screenshot = emulator.screenshot("editsec_after_direction_toggle")
        assert matches_icon_reference(screenshot, REGION_LONG_UP, "editsec_long_up", auto_save=False), (
            "No reference mask for direction toggle icon (not yet implemented)"
        )


# ============================================================
# 3.4 ControlModeCounting (Timer Running)
# ============================================================

class TestCountingIcons:
    """Tests for icons in ControlModeCounting (timer running).

    No icons are currently drawn in this mode. All tests are xfail.
    """

    def _enter_counting(self, emulator):
        """Enter counting mode: press Down, wait for 3s auto-transition."""
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode
        return emulator.screenshot("counting_mode")

    @pytest.mark.xfail(strict=True, reason="No exit/background icon implemented yet")
    def test_counting_back_icon(self, persistent_emulator):
        """Verify exit/background indicator for Back button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_BACK, "counting_back", auto_save=False), (
            "No reference mask for exit icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No edit icon implemented yet")
    def test_counting_up_icon(self, persistent_emulator):
        """Verify edit indicator for Up button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_UP, "counting_up", auto_save=False), (
            "No reference mask for edit icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No pause icon implemented for Counting mode")
    def test_counting_select_icon(self, persistent_emulator):
        """Verify pause indicator for Select button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_SELECT, "counting_select", auto_save=False), (
            "No reference mask for pause icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No details/refresh icon implemented yet")
    def test_counting_down_icon(self, persistent_emulator):
        """Verify details/refresh indicator for Down button in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_DOWN, "counting_down", auto_save=False), (
            "No reference mask for details icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No enable-repeat icon implemented yet")
    def test_counting_long_up_icon(self, persistent_emulator):
        """Verify enable repeat indicator for long-press Up in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_UP, "counting_long_up", auto_save=False), (
            "No reference mask for enable-repeat icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No restart icon implemented yet")
    def test_counting_long_select_icon(self, persistent_emulator):
        """Verify restart indicator for long-press Select in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_SELECT, "counting_long_select", auto_save=False), (
            "No reference mask for restart icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No quit icon implemented yet")
    def test_counting_long_down_icon(self, persistent_emulator):
        """Verify quit indicator for long-press Down in Counting mode."""
        emulator = persistent_emulator
        screenshot = self._enter_counting(emulator)
        assert matches_icon_reference(screenshot, REGION_LONG_DOWN, "counting_long_down", auto_save=False), (
            "No reference mask for quit icon (not yet implemented)"
        )


# ============================================================
# 3.5 ControlModeCounting + Paused
# ============================================================

class TestPausedIcons:
    """Tests for icons when timer is paused.

    The play icon resource exists (IMAGE_PLAY_ICON) but is never drawn.
    """

    @pytest.mark.xfail(strict=True, reason="Play icon resource exists but is never drawn")
    def test_paused_select_icon_play(self, persistent_emulator):
        """Verify play icon for Select button when timer is paused.

        IMAGE_PLAY_ICON resource exists (music_icon_play.png) but is never drawn.
        """
        emulator = persistent_emulator

        # Set timer and enter counting mode
        emulator.press_down()  # Add 1 minute
        time.sleep(4)  # Wait for counting mode

        # Pause the timer
        emulator.press_select()
        time.sleep(0.5)

        screenshot = emulator.screenshot("paused_mode")
        assert matches_icon_reference(screenshot, REGION_SELECT, "paused_play", auto_save=False), (
            "No reference mask for play icon (not yet drawn)"
        )


# ============================================================
# 3.6 ControlModeCounting + Chrono (Counting Up)
# ============================================================

class TestChronoIcons:
    """Tests for icons in chrono mode (counting up after timer completion).

    No icons are currently drawn in chrono mode. All tests are xfail.
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

    @pytest.mark.xfail(strict=True, reason="No pause icon implemented for chrono mode")
    def test_chrono_select_icon(self, persistent_emulator):
        """Verify pause indicator for Select button in chrono mode."""
        emulator = persistent_emulator
        screenshot = self._enter_chrono(emulator)

        # Cancel quit timer
        emulator.press_down()

        assert matches_icon_reference(screenshot, REGION_SELECT, "chrono_select", auto_save=False), (
            "No reference mask for pause icon in chrono mode (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No reset icon implemented for chrono mode")
    def test_chrono_long_select_icon(self, persistent_emulator):
        """Verify reset indicator for long-press Select in chrono mode."""
        emulator = persistent_emulator
        screenshot = self._enter_chrono(emulator)

        # Cancel quit timer
        emulator.press_down()

        assert matches_icon_reference(screenshot, REGION_LONG_SELECT, "chrono_long_select", auto_save=False), (
            "No reference mask for reset icon in chrono mode (not yet implemented)"
        )


# ============================================================
# 3.7 ControlModeEditRepeat
# ============================================================

class TestEditRepeatIcons:
    """Tests for icons in ControlModeEditRepeat mode.

    No icons are currently drawn in this mode. All tests are xfail.
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

    @pytest.mark.xfail(strict=True, reason="No reset count icon implemented yet")
    def test_editrepeat_back_icon(self, persistent_emulator):
        """Verify reset count indicator for Back button in EditRepeat mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert matches_icon_reference(screenshot, REGION_BACK, "editrepeat_back", auto_save=False), (
            "No reference mask for reset count icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +20 repeats icon implemented yet")
    def test_editrepeat_up_icon(self, persistent_emulator):
        """Verify +20 repeats indicator for Up button in EditRepeat mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert matches_icon_reference(screenshot, REGION_UP, "editrepeat_up", auto_save=False), (
            "No reference mask for +20 repeats icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +5 repeats icon implemented yet")
    def test_editrepeat_select_icon(self, persistent_emulator):
        """Verify +5 repeats indicator for Select button in EditRepeat mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert matches_icon_reference(screenshot, REGION_SELECT, "editrepeat_select", auto_save=False), (
            "No reference mask for +5 repeats icon (not yet implemented)"
        )

    @pytest.mark.xfail(strict=True, reason="No +1 repeat icon implemented yet")
    def test_editrepeat_down_icon(self, persistent_emulator):
        """Verify +1 repeat indicator for Down button in EditRepeat mode."""
        emulator = persistent_emulator
        screenshot = self._enter_editrepeat(emulator)
        assert matches_icon_reference(screenshot, REGION_DOWN, "editrepeat_down", auto_save=False), (
            "No reference mask for +1 repeat icon (not yet implemented)"
        )
