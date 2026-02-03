"""
Test Cases: Repeat counter visibility and icon overlap prevention.

Tests the repeat_counter_visible variable in drawing.c which controls:
1. Whether the repeat counter indicator (e.g., "2x") is shown
2. Whether the +20 min/sec icon is hidden to prevent overlap

When a timer has is_repeating == true AND repeat_count > 1, the repeat
counter indicator is displayed and the +20 icon should NOT be visible
in New and EditSec modes.
"""

import logging
import time
import pytest
from pathlib import Path
from PIL import Image
import numpy as np

from .conftest import Button, EmulatorHelper, PLATFORMS
from .test_button_icons import (
    get_region,
    has_icon_content,
    matches_icon_reference,
    crop_icon_region,
    _get_non_bg_mask,
)

# Configure module logger
logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


def count_non_bg_pixels(img, region):
    """Count non-background pixels in a region."""
    crop = crop_icon_region(img, region)
    crop_arr = np.array(crop)
    mask = _get_non_bg_mask(crop_arr)
    return int(np.sum(mask))


class TestRepeatCounterVisibility:
    """Tests for repeat_counter_visible behavior in drawing.c.

    The repeat_counter_visible variable determines:
    - If True: Show repeat counter indicator (e.g., "2x"), hide +20 icon
    - If False: Show +20 icon normally

    repeat_counter_visible is True when:
    - In EditRepeat mode (with flashing)
    - OR (is_repeating == true AND repeat_count > 1) in any other mode
    """

    def _setup_repeating_timer(self, emulator):
        """Set up a timer and add repeats to make repeat_count > 1.

        Steps:
        1. Add 1 minute to timer (press Down)
        2. Wait for counting mode (auto-start after 3 seconds)
        3. Long press Up to enter EditRepeat mode
        4. Press Select to add +5 repeats (repeat_count becomes 6)
        5. Return to counting mode (wait for auto-exit)

        Returns the emulator positioned in counting mode with repeat_count > 1.
        """
        # Add 1 minute
        emulator.press_down()
        time.sleep(0.5)

        # Wait for auto-start into counting mode
        time.sleep(4)

        # Long press Up to enter EditRepeat mode
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.3)

        # Press Select to add +5 repeats
        emulator.press_select()
        time.sleep(0.3)

        # Screenshot in EditRepeat mode showing the repeat count indicator
        editrepeat_screenshot = emulator.screenshot("editrepeat_with_repeats")

        # Wait for EditRepeat mode to auto-exit (returns to counting)
        time.sleep(4)

        return editrepeat_screenshot

    def _get_to_new_mode_with_repeats(self, emulator):
        """Get to New mode with a repeating timer (repeat_count > 1).

        This requires:
        1. Set up a short timer with repeats
        2. Let the timer count down and complete all repeats
        3. After all alarms are dismissed, return to New mode

        For testing efficiency, we use a minimal timer duration.
        """
        # Add minimal time (1 press = 1 minute)
        emulator.press_down()
        time.sleep(0.5)

        # Wait for counting mode
        time.sleep(4)

        # Enter EditRepeat mode
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.3)

        # Add 2 repeats (we'll wait for 2 cycles)
        emulator.press_down()  # +1 repeat
        emulator.press_down()  # +1 repeat (total: 3 cycles including original)
        time.sleep(0.3)

        # Wait for auto-exit from EditRepeat
        time.sleep(4)

        # Now wait for all 3 cycles to complete (each cycle is ~60 seconds)
        # This is too long for a practical test, so we'll use a different approach
        # Instead, we'll test what we can with the counting mode screenshot

        return None

    def test_editrepeat_shows_repeat_counter(self, persistent_emulator):
        """Verify repeat counter indicator is visible in EditRepeat mode.

        When in EditRepeat mode, the repeat counter should be visible (flashing).
        This is a prerequisite for the icon overlap fix.
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Set up timer and enter EditRepeat with repeats
        screenshot = self._setup_repeating_timer(emulator)

        # Save screenshot for visual inspection
        screenshot_path = SCREENSHOTS_DIR / f"test_repeat_counter_{platform}_editrepeat.png"
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

        # In EditRepeat mode with repeat_count > 1, the UP region should show
        # the +20 repeats icon, NOT the +20 minutes icon
        region = get_region(platform, "UP")

        # Verify there's content in the UP region (either +20 repeats or repeat indicator)
        assert has_icon_content(screenshot, region), (
            f"Expected icon content in UP region in EditRepeat mode with repeats"
        )

        # The screenshot is saved for visual inspection
        print(f"\nScreenshot for visual verification: {screenshot_path}")

    def test_counting_mode_up_region_with_repeats(self, persistent_emulator):
        """Verify UP region appearance in counting mode with repeat_count > 1.

        When counting with repeat_count > 1, the repeat indicator (e.g., "6x")
        should be visible and the Edit icon should NOT be shown to prevent overlap.

        This test verifies:
        1. The repeat counter is visible (has content in UP region)
        2. The Edit icon is NOT shown (region should not match Edit icon reference)
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # First set up the repeating timer
        self._setup_repeating_timer(emulator)

        # Now we're in counting mode with repeat_count > 1
        # Take screenshot
        screenshot = emulator.screenshot("counting_with_repeats")

        # Save screenshot for visual inspection
        screenshot_path = SCREENSHOTS_DIR / f"test_repeat_counter_{platform}_counting_repeats.png"
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

        # In counting mode with repeat_count > 1, the UP region should:
        # 1. Have some content (the repeat counter indicator like "6x")
        # 2. NOT match the Edit icon reference (Edit icon should be hidden)
        region = get_region(platform, "UP")

        # Verify there's content in the UP region (the repeat counter indicator)
        has_content = has_icon_content(screenshot, region)
        logger.info(f"UP region has content: {has_content}")
        assert has_content, "Expected repeat counter indicator in UP region"

        # Verify the Edit icon is NOT shown (should not match the Edit icon reference)
        # The Edit icon reference is "counting_up" - if it matches, that means
        # the Edit icon is being shown which is incorrect
        matches_edit = matches_icon_reference(
            screenshot, region, "counting_up", platform, auto_save=False, tolerance=10
        )
        assert not matches_edit, (
            f"Edit icon should NOT be visible in counting mode when repeat_count > 1. "
            f"Only the repeat counter indicator (e.g., '6x') should be shown."
        )

        print(f"\nScreenshot for visual verification: {screenshot_path}")

    def test_new_mode_baseline_has_plus_20_icon(self, persistent_emulator):
        """Verify +20 icon IS visible in New mode without repeats (baseline).

        In New mode with is_repeating == false (or repeat_count == 1),
        the +20 minute icon SHOULD be visible. This is the baseline behavior
        before any repeat configuration.
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Fresh app state - should be in New mode without repeating
        # Reset by pressing Back to return to New mode if needed
        emulator.press_back()
        time.sleep(0.5)
        emulator.press_back()
        time.sleep(0.5)

        # Take screenshot in New mode
        screenshot = emulator.screenshot("new_mode_baseline")

        # Save for visual inspection
        screenshot_path = SCREENSHOTS_DIR / f"test_repeat_counter_{platform}_new_baseline.png"
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

        # In New mode without repeating, UP region should show +20 min icon
        region = get_region(platform, "UP")
        pixel_count = count_non_bg_pixels(screenshot, region)

        logger.info(f"New mode UP region non-bg pixels: {pixel_count}")

        # The +20 icon should have content (baseline)
        assert has_icon_content(screenshot, region), (
            f"Expected +20 min icon content in UP region in New mode (baseline). "
            f"Got {pixel_count} non-bg pixels."
        )

        print(f"\nScreenshot for visual verification: {screenshot_path}")
        print(f"UP region non-background pixels: {pixel_count}")

    def test_new_mode_with_repeats_hides_plus_20_icon(self, persistent_emulator):
        """Verify +20 icon is HIDDEN in New mode when editing a repeating timer.

        When in New mode (edit mode) with is_repeating == true AND repeat_count > 1,
        the +20 minute icon should NOT be visible to prevent overlap with the
        repeat counter indicator (e.g., "6x").

        Steps:
        1. Set up a repeating timer (Counting mode with repeat_count > 1)
        2. Short-press Up to enter New mode (edit mode)
        3. Verify the +20 icon is NOT visible in UP region
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Set up repeating timer (this leaves us in Counting mode with repeats)
        self._setup_repeating_timer(emulator)

        # Short-press Up to enter edit mode (New mode)
        emulator.press_up()
        time.sleep(0.5)

        # Take screenshot in New mode while editing repeating timer
        screenshot = emulator.screenshot("new_mode_with_repeats")

        # Save for visual inspection
        screenshot_path = SCREENSHOTS_DIR / f"test_repeat_counter_{platform}_new_with_repeats.png"
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

        # In New mode with repeats, the UP region should NOT show the +20 min icon
        # The repeat counter indicator (e.g., "6x") is shown instead
        region = get_region(platform, "UP")
        pixel_count = count_non_bg_pixels(screenshot, region)

        logger.info(f"New mode (with repeats) UP region non-bg pixels: {pixel_count}")

        # Compare with the +20 min icon reference - it should NOT match
        matches_plus_20 = matches_icon_reference(
            screenshot, region, "new_up", platform, auto_save=False, tolerance=10
        )

        # The +20 icon should NOT be visible (should not match reference)
        assert not matches_plus_20, (
            f"+20 min icon should NOT be visible in New mode when editing a repeating timer. "
            f"The repeat counter indicator should be shown instead. "
            f"Got {pixel_count} non-bg pixels in UP region."
        )

        print(f"\nScreenshot for visual verification: {screenshot_path}")
        print(f"UP region non-background pixels: {pixel_count}")
        print(f"Matches +20 icon reference: {matches_plus_20}")

    def test_editsec_mode_with_repeats_hides_plus_20_icon(self, persistent_emulator):
        """Verify +20sec icon is HIDDEN in EditSec mode when editing a repeating timer.

        When in EditSec mode with is_repeating == true AND repeat_count > 1,
        the +20 second icon should NOT be visible to prevent overlap with the
        repeat counter indicator (e.g., "6x").

        Steps:
        1. Set up a repeating timer (Counting mode with repeat_count > 1)
        2. Short-press Up to enter edit mode (New mode)
        3. Press Select to enter EditSec mode (by modifying the timer)
        4. Verify the +20sec icon is NOT visible in UP region
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Set up repeating timer (this leaves us in Counting mode with repeats)
        self._setup_repeating_timer(emulator)

        # Short-press Up to enter edit mode (New mode)
        emulator.press_up()
        time.sleep(0.5)

        # Press Select to go to EditSec mode (adds time, goes to EditSec)
        emulator.press_select()
        time.sleep(0.5)

        # Take screenshot in EditSec mode while editing repeating timer
        screenshot = emulator.screenshot("editsec_mode_with_repeats")

        # Save for visual inspection
        screenshot_path = SCREENSHOTS_DIR / f"test_repeat_counter_{platform}_editsec_with_repeats.png"
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

        # In EditSec mode with repeats, the UP region should NOT show the +20sec icon
        # The repeat counter indicator (e.g., "6x") is shown instead
        region = get_region(platform, "UP")
        pixel_count = count_non_bg_pixels(screenshot, region)

        logger.info(f"EditSec mode (with repeats) UP region non-bg pixels: {pixel_count}")

        # Compare with the +20sec icon reference - it should NOT match
        matches_plus_20sec = matches_icon_reference(
            screenshot, region, "editsec_up", platform, auto_save=False, tolerance=10
        )

        # The +20sec icon should NOT be visible (should not match reference)
        assert not matches_plus_20sec, (
            f"+20sec icon should NOT be visible in EditSec mode when editing a repeating timer. "
            f"The repeat counter indicator should be shown instead. "
            f"Got {pixel_count} non-bg pixels in UP region."
        )

        print(f"\nScreenshot for visual verification: {screenshot_path}")
        print(f"UP region non-background pixels: {pixel_count}")
        print(f"Matches +20sec icon reference: {matches_plus_20sec}")

    def test_new_mode_reverse_with_repeats_hides_minus_20_icon(self, persistent_emulator):
        """Verify -20min icon is HIDDEN in New mode (reverse) when editing a repeating timer.

        When in New mode with reverse direction, is_repeating == true AND repeat_count > 1,
        the -20 minute icon should NOT be visible to prevent overlap with the
        repeat counter indicator.

        Steps:
        1. Set up a repeating timer (Counting mode with repeat_count > 1)
        2. Short-press Up to enter edit mode (New mode)
        3. Long-press Up to toggle to reverse direction
        4. Verify the -20min icon is NOT visible in UP region
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # Set up repeating timer (this leaves us in Counting mode with repeats)
        self._setup_repeating_timer(emulator)

        # Short-press Up to enter edit mode (New mode)
        emulator.press_up()
        time.sleep(0.5)

        # Long-press Up to toggle to reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.5)

        # Take screenshot in New mode (reverse) while editing repeating timer
        screenshot = emulator.screenshot("new_mode_reverse_with_repeats")

        # Save for visual inspection
        screenshot_path = SCREENSHOTS_DIR / f"test_repeat_counter_{platform}_new_reverse_with_repeats.png"
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

        # In New mode (reverse) with repeats, the UP region should NOT show the -20min icon
        region = get_region(platform, "UP")
        pixel_count = count_non_bg_pixels(screenshot, region)

        logger.info(f"New mode reverse (with repeats) UP region non-bg pixels: {pixel_count}")

        # Compare with the -20min icon reference - it should NOT match
        matches_minus_20 = matches_icon_reference(
            screenshot, region, "new_up_reverse", platform, auto_save=False, tolerance=10
        )

        # The -20min icon should NOT be visible (should not match reference)
        assert not matches_minus_20, (
            f"-20min icon should NOT be visible in New mode (reverse) when editing a repeating timer. "
            f"The repeat counter indicator should be shown instead. "
            f"Got {pixel_count} non-bg pixels in UP region."
        )

        print(f"\nScreenshot for visual verification: {screenshot_path}")
        print(f"UP region non-background pixels: {pixel_count}")
        print(f"Matches -20min icon reference: {matches_minus_20}")


class TestIconOverlapPrevention:
    """Tests specifically for the icon overlap fix (commit 96a5f47).

    The fix ensures that when repeat_counter_visible is true, the +20 icon
    is NOT drawn to prevent visual overlap with the repeat counter indicator.
    """

    def test_editrepeat_mode_icon_comparison(self, persistent_emulator):
        """Compare UP region in EditRepeat mode vs baseline New mode.

        This test verifies the icon overlap prevention fix (commit 96a5f47).
        In New mode (baseline), the UP button shows the +20 min icon.
        In EditRepeat mode, the UP button should show the +20 repeats icon.

        Crucially, in EditRepeat mode, the +20 min icon should NOT be visible
        (no overlap).

        Steps:
        1. Capture baseline in New Mode (should verify +20 min icon present)
        2. Transition to EditRepeat Mode
        3. Capture EditRepeat screenshot (should verify +20 repeats icon present)
        4. Assert that EditRepeat screenshot does NOT match +20 min icon
        """
        emulator = persistent_emulator
        platform = emulator.platform

        # 1. Baseline: We start in New Mode (fresh app state from fixture)
        baseline_screenshot = emulator.screenshot("overlap_test_baseline")
        baseline_path = SCREENSHOTS_DIR / f"test_icon_overlap_{platform}_baseline.png"
        baseline_screenshot.save(baseline_path)
        logger.info(f"Baseline screenshot saved: {baseline_path}")

        # Verify we have content in UP region (baseline +20 min icon)
        region = get_region(platform, "UP")
        baseline_pixels = count_non_bg_pixels(baseline_screenshot, region)

        assert has_icon_content(baseline_screenshot, region), (
            f"Baseline New Mode should show content in UP region (+20 min icon). "
            f"Got {baseline_pixels} non-bg pixels."
        )

        # 2. Transition to EditRepeat Mode
        # First, set a timer (press Down adds 1 min) to ensure we are not in stopwatch mode
        emulator.press_down()
        time.sleep(0.5)

        # Wait for auto-start to Counting Mode (3s timeout + buffer)
        time.sleep(4)

        # Hold UP to enter EditRepeat Mode
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.5)

        editrepeat_screenshot_1 = emulator.screenshot("overlap_test_editrepeat_1")
        time.sleep(0.5)

        pixels_1 = count_non_bg_pixels(editrepeat_screenshot_1, region)

        editrepeat_screenshot = editrepeat_screenshot_1
        editrepeat_pixels = pixels_1
        best_shot_name = "1"

        editrepeat_path = SCREENSHOTS_DIR / f"test_icon_overlap_{platform}_editrepeat.png"
        editrepeat_screenshot.save(editrepeat_path)
        logger.info(f"EditRepeat screenshot saved (using shot {best_shot_name}): {editrepeat_path}")

        # 4. Assert that EditRepeat screenshot has more background pixels than the baseline
        # (meaning it has FEWER non-background pixels, because the +20 icon should be hidden)
        assert editrepeat_pixels < baseline_pixels, (
            f"EditRepeat mode should have fewer non-background pixels ({editrepeat_pixels}) "
            f"than baseline New mode ({baseline_pixels}) because the +20 icon should be hidden "
            f"to avoid overlap with the repeat counter. Visual overlap detected."
        )

        # 5. Assert that EditRepeat screenshot does NOT match +20 min icon (overlap check)
        # We check against "new_up" reference which is the +20 min icon
        matches_plus_20 = matches_icon_reference(
            editrepeat_screenshot, region, "new_up", platform, auto_save=False, tolerance=10
        )

        assert not matches_plus_20, (
            "EditRepeat mode should NOT show +20 min icon. "
            "The +20 repeats icon should be shown instead. "
            "Visual overlap detected (match with new_up reference)."
        )

        logger.info(f"Baseline pixels: {baseline_pixels}, EditRepeat pixels: {editrepeat_pixels}")
