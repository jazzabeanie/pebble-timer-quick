"""
Test Case: Stopwatch Subtraction to Countdown Conversion

This test verifies the fix for a bug where subtracting time from a stopwatch
(chrono) timer converts it into a countdown timer instead of producing an
invalid state.

Reference: specs/stopwatch-subtraction.md

When the timer is in chrono mode (counting up from 0:00) and a user subtracts
time (e.g., 1 minute) by entering edit mode and using reverse direction,
the timer should correctly transition to countdown mode showing the remaining
time until the subtracted value.

Example:
- Chrono shows 0:05 (5 seconds elapsed)
- User subtracts 1 minute
- Timer should show ~0:55 countdown (55 seconds remaining)
"""

import logging
import time

import pytest

from .conftest import (
    Button,
    PLATFORMS,
    LogCapture,
    assert_mode,
    assert_paused,
    assert_time_approximately,
    assert_direction,
    assert_is_chrono,
)
from .test_create_timer import (
    extract_text,
    normalize_time_text,
    has_time_pattern,
)

# Configure module logger
logger = logging.getLogger(__name__)


class TestStopwatchSubtraction:
    """Tests for stopwatch subtraction to countdown conversion."""

    def test_chrono_subtraction_converts_to_countdown(self, persistent_emulator):
        """
        Test that subtracting time from a chrono converts it to a countdown.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode
        logger.info("Waiting for chrono mode...")
        time.sleep(3.5)
        
        # Step 2: Pause the timer
        emulator.press_select()
        state_pause = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_pause is not None
        assert_paused(state_pause, True)

        # Step 3: Enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")

        # Step 4: Toggle reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 5: Subtract 1 minute
        emulator.press_down()
        state_sub = capture.wait_for_state(event="button_down", timeout=5.0)
        
        capture.stop()

        # Verify countdown state
        assert state_sub is not None
        logger.info(f"After subtraction state: {state_sub}")

        # Should be ~0:55 countdown
        assert_is_chrono(state_sub, is_chrono=False)
        assert_time_approximately(state_sub, minutes=0, seconds=55, tolerance=10)
        assert_mode(state_sub, "New")
        assert_paused(state_sub, True)


    def test_chrono_subtraction_multiple_minutes(self, persistent_emulator):
        """
        Test subtracting multiple minutes from a chrono.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode
        time.sleep(3.5)
        emulator.press_select()
        capture.wait_for_state(event="button_select", timeout=5.0)

        # Step 2: Enter edit mode and reverse direction
        emulator.press_up()
        capture.wait_for_state(event="button_up", timeout=5.0)
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        capture.wait_for_state(event="long_press_up", timeout=5.0)

        # Step 3: Subtract 3 minutes
        emulator.press_down()
        emulator.press_down()
        emulator.press_down()
        
        # Wait for all 3 button_down events
        state_sub1 = capture.wait_for_state(event="button_down", timeout=5.0)
        state_sub2 = capture.wait_for_state(event="button_down", timeout=5.0)
        state_sub3 = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        # Verify countdown shows approximately 2:55
        assert state_sub3 is not None
        assert_time_approximately(state_sub3, minutes=2, seconds=55, tolerance=10)


    def test_chrono_add_then_subtract(self, persistent_emulator):
        """
        Test adding time then subtracting to verify direction toggle works.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode
        time.sleep(3.5)
        emulator.press_up()
        capture.wait_for_state(event="button_up", timeout=5.0)

        # Step 2: Add 2 minutes (forward)
        emulator.press_down()
        emulator.press_down()
        state_add1 = capture.wait_for_state(event="button_down", timeout=5.0)
        state_add2 = capture.wait_for_state(event="button_down", timeout=5.0)
        # Timer runs immediately in ControlModeNew, so more elapsed time accumulates
        assert_time_approximately(state_add2, minutes=2, seconds=5, tolerance=15)
        assert_direction(state_add2, forward=True)

        # Step 3: Toggle reverse and subtract 1 minute
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        capture.wait_for_state(event="long_press_up", timeout=5.0)

        emulator.press_down()
        state_sub1 = capture.wait_for_state(event="button_down", timeout=5.0)
        
        capture.stop()

        # Verify subtraction reduced the time back to ~1:05 (subtract 1 min from ~2:05)
        assert state_sub1 is not None
        assert_direction(state_sub1, forward=False)
        assert_time_approximately(state_sub1, minutes=1, seconds=5, tolerance=15)