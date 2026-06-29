"""
Test Case: Paused Stopwatch Millisecond Display

Verifies that when a stopwatch (chrono) is paused and its elapsed time is under
one hour, the main display shows milliseconds (e.g. "1:23.456"); and that
milliseconds are NOT shown while running, nor for countdown timers in any state.

Reference: openspec/changes/stopwatch-paused-milliseconds/specs/
           stopwatch-millisecond-display/spec.md

These functional tests assert real end-to-end behavior on the emulator via the
`TEST_STATE:display,disp=<string>` log emitted by the main-text renderer. The
exact-format scenarios (exact ms values, the >= 1h boundary) that the emulator
cannot reproduce are covered by unit tests in test/test_drawing.c.
"""

import logging
import re
import time

import pytest

from .conftest import LogCapture, assert_paused, assert_is_chrono, assert_mode

logger = logging.getLogger(__name__)

# Matches a millisecond group like ".456" in a display string.
MS_PATTERN = re.compile(r"\.\d{3}")


def latest_display(capture):
    """Return the most recently logged main-text display string, or None."""
    disps = []
    for line in capture.get_all_logs():
        m = re.search(r"disp=(\S+)", line)
        if m:
            disps.append(m.group(1))
    return disps[-1] if disps else None


def shows_ms(disp):
    """True if the display string contains a millisecond group (e.g. .456)."""
    return disp is not None and bool(MS_PATTERN.search(disp))


def create_countdown(emulator, capture):
    """Deterministically create a running countdown timer regardless of the
    current mode.

    Pressing Up from Counting (chrono) mode enters New mode without setting a
    length; pressing Up from New mode just adds time. Either way we then land in
    New mode, where Down adds a positive length, producing a countdown (a timer
    with `length_ms - elapsed > 0`, i.e. not chrono).
    """
    emulator.press_up()
    capture.wait_for_state(event="button_up", timeout=5.0)
    emulator.press_down()
    state = capture.wait_for_state(event="button_down", timeout=5.0)
    assert state is not None, "Did not receive button_down state"
    assert_mode(state, "New")
    assert_is_chrono(state, is_chrono=False)  # sanity: it is now a countdown
    return state


class TestStopwatchMilliseconds:
    """Millisecond display for a paused stopwatch under one hour."""

    def test_paused_stopwatch_under_hour_shows_ms(self, persistent_emulator):
        """A paused stopwatch (< 1h) shows milliseconds in the main display."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for chrono (stopwatch) counting mode after the idle transition.
        time.sleep(3.5)

        # Pause the stopwatch.
        emulator.press_select()
        state = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state is not None
        assert_is_chrono(state, is_chrono=True)
        assert_paused(state, True)

        # Allow the paused frame (with milliseconds) to render and be logged.
        time.sleep(1.0)
        disp = latest_display(capture)
        capture.stop()

        assert disp is not None, "No display string was logged"
        assert shows_ms(disp), (
            f"Expected paused stopwatch display to include milliseconds, got '{disp}'"
        )

    def test_running_stopwatch_hides_ms(self, persistent_emulator):
        """A running stopwatch shows no millisecond component."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for chrono counting mode and let it run (do NOT pause).
        time.sleep(3.5)
        # Let the seconds tick so the running display is logged a few times.
        time.sleep(1.5)
        disp = latest_display(capture)
        capture.stop()

        assert disp is not None, "No display string was logged"
        assert not shows_ms(disp), (
            f"Expected running stopwatch display to omit milliseconds, got '{disp}'"
        )

    def test_paused_countdown_hides_ms(self, persistent_emulator):
        """A paused countdown timer shows no millisecond component."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Establish a countdown timer (not a stopwatch).
        create_countdown(emulator, capture)

        # Wait for the idle transition into Counting mode, then pause.
        time.sleep(3.5)
        emulator.press_select()
        state = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state is not None
        assert_is_chrono(state, is_chrono=False)
        assert_paused(state, True)

        time.sleep(1.0)
        disp = latest_display(capture)
        capture.stop()

        assert disp is not None, "No display string was logged"
        assert not shows_ms(disp), (
            f"Expected paused countdown display to omit milliseconds, got '{disp}'"
        )

    def test_running_countdown_hides_ms(self, persistent_emulator):
        """A running countdown timer shows no millisecond component."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Establish a countdown timer (not a stopwatch).
        create_countdown(emulator, capture)

        # Wait for Counting mode and let it run (do NOT pause).
        time.sleep(3.5)
        time.sleep(1.5)
        disp = latest_display(capture)
        capture.stop()

        assert disp is not None, "No display string was logged"
        assert not shows_ms(disp), (
            f"Expected running countdown display to omit milliseconds, got '{disp}'"
        )
