"""
Test Cases: Directional button icon tests.

Verifies that minus/decrement icons are displayed when the timer is in
reverse direction mode (toggled via long-press Up), and that the +60 icon
is correctly displayed in EditSec mode (was previously +30).

Tests cover:
1. ControlModeNew: verify + icons in forward mode, - icons in reverse mode
2. ControlModeEditSec: verify +60 (was +30) in forward, -60 in reverse

Tests use pixel-based screenshot comparison against per-icon reference masks
stored in screenshots/icon_refs/.
"""

import logging
import os
import pytest
from pathlib import Path
from PIL import Image
import numpy as np
import time

from .conftest import Button, EmulatorHelper, PLATFORMS
from .test_button_icons import (
    REGION_BACK, REGION_UP, REGION_SELECT, REGION_DOWN,
    REGION_LONG_UP, has_icon_content, matches_icon_reference,
    ICON_REFS_DIR
)

# Configure module logger
logger = logging.getLogger(__name__)


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
# Helper Functions
# ============================================================

def enter_new_mode_forward(emulator):
    """Ensure we are in New mode with forward (increment) direction.

    Just take a screenshot - app starts in New mode with forward direction.
    """
    time.sleep(0.5)
    return emulator.screenshot("new_mode_forward")


def toggle_to_reverse_mode(emulator):
    """Toggle to reverse direction mode by long-pressing Up button.

    Returns screenshot after toggle.
    """
    emulator.hold_button(Button.UP)
    time.sleep(1)
    emulator.release_buttons()
    time.sleep(0.3)
    return emulator.screenshot("new_mode_reverse")


def enter_editsec_mode(emulator):
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
    return emulator.screenshot("editsec_mode_forward")


def toggle_editsec_to_reverse(emulator):
    """Toggle EditSec mode to reverse direction.

    Assumes already in EditSec mode.
    """
    emulator.hold_button(Button.UP)
    time.sleep(1)
    emulator.release_buttons()
    time.sleep(0.3)
    return emulator.screenshot("editsec_mode_reverse")


# ============================================================
# Test: New Mode Forward Direction Icons (content check only)
# ============================================================

class TestNewModeForwardIcons:
    """Tests for forward (increment) icons in ControlModeNew.

    These verify icon content exists - reference masks are managed by
    test_button_icons.py.
    """

    def test_new_forward_has_icons(self, persistent_emulator):
        """Verify icons exist in all button regions in New mode (forward direction)."""
        emulator = persistent_emulator
        screenshot = enter_new_mode_forward(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected +1hr icon content in Back button region"
        )
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected +20min icon content in Up button region"
        )
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected +5min icon content in Select button region"
        )
        assert has_icon_content(screenshot, REGION_DOWN), (
            "Expected +1min icon content in Down button region"
        )


# ============================================================
# Test: New Mode Reverse Direction Icons
# ============================================================

class TestNewModeReverseIcons:
    """Tests for reverse (decrement) icons in ControlModeNew.

    After long-pressing Up to toggle direction, icons should show minus signs.
    """

    def test_new_reverse_back_icon(self, persistent_emulator):
        """Verify -1hr icon for Back button in New mode (reverse direction)."""
        emulator = persistent_emulator
        enter_new_mode_forward(emulator)
        screenshot = toggle_to_reverse_mode(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected -1hr icon content in Back button region"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "new_back_reverse"), (
            "-1hr icon does not match reference mask"
        )

    def test_new_reverse_up_icon(self, persistent_emulator):
        """Verify -20min icon for Up button in New mode (reverse direction)."""
        emulator = persistent_emulator
        enter_new_mode_forward(emulator)
        screenshot = toggle_to_reverse_mode(emulator)
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected -20min icon content in Up button region"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "new_up_reverse"), (
            "-20min icon does not match reference mask"
        )

    def test_new_reverse_select_icon(self, persistent_emulator):
        """Verify -5min icon for Select button in New mode (reverse direction)."""
        emulator = persistent_emulator
        enter_new_mode_forward(emulator)
        screenshot = toggle_to_reverse_mode(emulator)
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected -5min icon content in Select button region"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "new_select_reverse"), (
            "-5min icon does not match reference mask"
        )

    def test_new_reverse_down_icon(self, persistent_emulator):
        """Verify -1min icon for Down button in New mode (reverse direction)."""
        emulator = persistent_emulator
        enter_new_mode_forward(emulator)
        screenshot = toggle_to_reverse_mode(emulator)
        assert has_icon_content(screenshot, REGION_DOWN), (
            "Expected -1min icon content in Down button region"
        )
        assert matches_icon_reference(screenshot, REGION_DOWN, "new_down_reverse"), (
            "-1min icon does not match reference mask"
        )


# ============================================================
# Test: EditSec Mode Forward Direction Icons (including +60 fix)
# ============================================================

class TestEditSecModeForwardIcons:
    """Tests for forward icons in ControlModeEditSec.

    Key change: Back button should now show +60 (was +30).
    """

    def test_editsec_forward_back_icon_plus60(self, persistent_emulator):
        """Verify +60s icon for Back button in EditSec mode (was +30, now +60).

        This test specifically verifies the fix from directional-icons spec.
        """
        emulator = persistent_emulator
        screenshot = enter_editsec_mode(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected +60s icon content in Back button region"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "editsec_back_plus60"), (
            "+60s icon does not match reference mask (this is the fix for +30 -> +60)"
        )

    def test_editsec_forward_has_icons(self, persistent_emulator):
        """Verify icons exist in all button regions in EditSec mode (forward direction)."""
        emulator = persistent_emulator
        screenshot = enter_editsec_mode(emulator)
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected +20s icon content in Up button region"
        )
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected +5s icon content in Select button region"
        )


# ============================================================
# Test: EditSec Mode Reverse Direction Icons
# ============================================================

class TestEditSecModeReverseIcons:
    """Tests for reverse (decrement) icons in ControlModeEditSec."""

    def test_editsec_reverse_back_icon(self, persistent_emulator):
        """Verify -60s icon for Back button in EditSec mode (reverse direction)."""
        emulator = persistent_emulator
        enter_editsec_mode(emulator)
        screenshot = toggle_editsec_to_reverse(emulator)
        assert has_icon_content(screenshot, REGION_BACK), (
            "Expected -60s icon content in Back button region"
        )
        assert matches_icon_reference(screenshot, REGION_BACK, "editsec_back_reverse"), (
            "-60s icon does not match reference mask"
        )

    def test_editsec_reverse_up_icon(self, persistent_emulator):
        """Verify -20s icon for Up button in EditSec mode (reverse direction)."""
        emulator = persistent_emulator
        enter_editsec_mode(emulator)
        screenshot = toggle_editsec_to_reverse(emulator)
        assert has_icon_content(screenshot, REGION_UP), (
            "Expected -20s icon content in Up button region"
        )
        assert matches_icon_reference(screenshot, REGION_UP, "editsec_up_reverse"), (
            "-20s icon does not match reference mask"
        )

    def test_editsec_reverse_select_icon(self, persistent_emulator):
        """Verify -5s icon for Select button in EditSec mode (reverse direction)."""
        emulator = persistent_emulator
        enter_editsec_mode(emulator)
        screenshot = toggle_editsec_to_reverse(emulator)
        assert has_icon_content(screenshot, REGION_SELECT), (
            "Expected -5s icon content in Select button region"
        )
        assert matches_icon_reference(screenshot, REGION_SELECT, "editsec_select_reverse"), (
            "-5s icon does not match reference mask"
        )

    def test_editsec_reverse_down_icon(self, persistent_emulator):
        """Verify -1s icon for Down button in EditSec mode (reverse direction)."""
        emulator = persistent_emulator
        enter_editsec_mode(emulator)
        screenshot = toggle_editsec_to_reverse(emulator)
        assert matches_icon_reference(screenshot, REGION_DOWN, "editsec_down_reverse"), (
            "-1s icon does not match reference mask"
        )
