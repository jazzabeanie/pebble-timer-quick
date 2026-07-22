"""Functional test: the Timer List shows a repeat glyph on repeating timers.

A repeating countdown, once persisted, appears in the Timer List with the same
glyph the Counting-mode "enable repeat" button uses. The glyph is pre-tinted so
it stays visible on both the light (unselected) row background and the black
(selected) row highlight. See src/timer_list.c (prv_create_tinted_repeat_icon).
"""

import logging
import time

import pytest

from .conftest import Button, LogCapture

logger = logging.getLogger(__name__)

# The repeat glyph is drawn REPEAT_ICON_SIZE (15px) wide, right-aligned 4px from
# the row's right edge, on the 26px-tall name line (LINE1_HEIGHT). ROW_HEIGHT is
# 46px, so row 1 (the first existing timer, below the "New Timer" row) starts at
# y=46 with no scrolling on a rectangular display.
ROW_HEIGHT = 46
LINE1_HEIGHT = 26
ICON_SIZE = 15
ICON_RIGHT_PAD = 4


def _make_repeating_countdown_and_background(emulator, platform):
    """From a fresh New-mode app, build a running 5-minute repeating countdown
    and background it so it persists into the Timer List."""
    capture = LogCapture(platform)
    capture.start()
    time.sleep(0.5)

    # New mode: Select = +5 minutes -> a 5:00 countdown (won't expire mid-test)
    emulator.press_select()
    assert capture.wait_for_state(event="button_select", timeout=5.0) is not None

    # Auto-transition to Counting after the 3s edit timeout
    time.sleep(3.5)

    # Long-press Up in Counting enters EditRepeat; one Down press sets count=1
    emulator.hold_button(Button.UP)
    time.sleep(1.0)
    emulator.release_buttons()
    assert capture.wait_for_state(event="long_press_up", timeout=5.0) is not None
    emulator.press_down()
    assert capture.wait_for_state(event="button_down", timeout=5.0) is not None

    # Wait out the edit timeout back to Counting (timer now is_repeating)
    time.sleep(3.5)
    capture.stop()

    # Back exits and persists the repeating countdown
    emulator.press_back()
    time.sleep(0.5)


def _icon_region(img):
    """Pixel bounds of the glyph on row 1's name line (rectangular display)."""
    w = img.width
    x0 = w - ICON_SIZE - ICON_RIGHT_PAD
    y0 = ROW_HEIGHT + (LINE1_HEIGHT - ICON_SIZE) // 2
    return x0, y0, x0 + ICON_SIZE, y0 + ICON_SIZE


def _luma_extremes(img, box):
    """Return (min_luma, max_luma) over the box, on a 0-255 scale."""
    x0, y0, x1, y1 = box
    crop = img.convert("L").crop((x0, y0, x1, y1))
    lo, hi = crop.getextrema()
    return lo, hi


class TestRepeatListIcon:
    def test_repeat_icon_contrasts_on_both_row_states(self, emulator):
        platform = emulator.platform
        if platform in ("aplite",):
            # aplite still shows the list, but its round/scaling and tight RAM
            # make the deterministic pixel geometry below unreliable; the render
            # path is identical and exercised on the other platforms.
            pytest.skip("pixel geometry check limited to non-aplite platforms")
        if platform == "chalk":
            pytest.skip("round display centers/scrolls rows; geometry differs")

        # Build a repeating countdown and get it into the Timer List
        _make_repeating_countdown_and_background(emulator, platform)

        capture = LogCapture(platform)
        capture.start()
        emulator.open_app_via_menu()
        show = capture.wait_for_state(event="timer_list_show", timeout=10.0)
        assert show is not None, "Timer List did not appear"
        time.sleep(1.0)  # let the window-push animation settle

        # Row 0 = "New Timer" (selected/black), row 1 = repeating countdown
        # (unselected/light). The glyph is black here, so the icon box holds
        # both a light background and dark glyph pixels.
        img = emulator.screenshot("repeat_icon_unselected")
        box = _icon_region(img)
        lo, hi = _luma_extremes(img, box)
        assert lo < 90, (
            f"[{platform}] No dark repeat glyph on the unselected (light) row; "
            f"icon box luma range was ({lo}, {hi})"
        )
        assert hi > 150, (
            f"[{platform}] Unselected row icon box has no light background; "
            f"luma range ({lo}, {hi}) — is the row actually unselected?"
        )

        # Select row 1: it fills black, and the glyph must flip to white to stay
        # visible (a white glyph pixel means hi is bright on an otherwise dark box).
        # List navigation emits no log event, so settle with a short sleep.
        capture.stop()
        emulator.press_down()
        time.sleep(0.5)

        img2 = emulator.screenshot("repeat_icon_selected")
        lo2, hi2 = _luma_extremes(img2, box)
        assert hi2 > 150, (
            f"[{platform}] Repeat glyph not visible on the selected (black) row; "
            f"icon box luma range was ({lo2}, {hi2}). The glyph tint likely did "
            f"not flip to white."
        )
        assert lo2 < 90, (
            f"[{platform}] Selected row icon box is not dark; luma range "
            f"({lo2}, {hi2}) — is the row actually selected/highlighted?"
        )
