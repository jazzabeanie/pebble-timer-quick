"""
Tests verifying that base_length_ms is set correctly after setting a timer.

The header displays base_length_ms as the original timer length. A bug in
prv_check_zero_crossing_direction_flip caused the displayed value to be
shorter than what the user entered because elapsed editing time was subtracted.
"""

import logging
import pytest
import time

from .conftest import (
    Button,
    LogCapture,
    assert_base_length,
    assert_direction,
    assert_is_chrono,
    assert_mode,
)

logger = logging.getLogger(__name__)


class TestBaseLength:
    """Tests that base_length_ms matches user-entered timer values."""

    def test_20_second_timer_base_length(self, persistent_emulator):
        """
        Enter EditSec, press Up once (adds 20s), let the edit mode expire.
        Assert base_length_ms == 20000.
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)

        # Long press Select to enter EditSec mode from New mode.
        # Must happen before the 3-second new_expire_timer fires.
        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.3)

        # The long press Select logs "long_press_select" (not "mode_change")
        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state is not None, "Did not receive long_press_select event"
        assert_mode(state, "EditSec")
        logger.info(f"Entered EditSec: {state}")

        capture.clear_state_queue()

        # Press Up to add 20 seconds
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Did not receive button_up state"
        logger.info(f"After Up press in EditSec: {state}")

        # Wait for EditSec to expire (3s inactivity timer) and transition to Counting
        state = capture.wait_for_state(event="mode_change", timeout=10.0)
        assert state is not None, "Did not receive mode_change to Counting"
        assert_mode(state, "Counting")
        logger.info(f"After mode change to Counting: {state}")

        # base_length_ms should be exactly 20000 (20 seconds)
        assert_base_length(state, 20000)

        capture.stop()

    def test_5_minute_timer_base_length(self, persistent_emulator):
        """
        In New mode, press Down 5 times (adds 5 min), let mode expire.
        Assert base_length_ms == 300000.
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Press Down 5 times (each adds 1 minute)
        for i in range(5):
            emulator.press_down()
            state = capture.wait_for_state(event="button_down", timeout=5.0)
            assert state is not None, f"Did not receive button_down state for press {i+1}"
            logger.info(f"After Down press {i+1}: {state}")

        # Wait for New mode to expire (3s inactivity) and transition to Counting
        state = capture.wait_for_state(event="mode_change", timeout=10.0)
        assert state is not None, "Did not receive mode_change to Counting"
        assert_mode(state, "Counting")
        logger.info(f"After mode change to Counting: {state}")

        # base_length_ms should be exactly 300000 (5 minutes)
        assert_base_length(state, 300000)

        capture.stop()

    def test_chrono_edit_then_countdown_ignores_chrono_elapsed(self, persistent_emulator):
        """
        Edit a chrono to add 20 seconds, then edit again switching direction
        to subtract 20 minutes (crossing zero to countdown).

        The chrono elapsed time from the first edit should not affect the
        countdown value. The header should show 20:00, not 19:40.

        Workflow:
        1. Create chrono (let New mode expire)
        2. Edit it, switch to EditSec, add 20 seconds
        3. Let edit expire (back to Counting as chrono)
        4. Edit again, switch direction, subtract 20 minutes (crosses zero)
        5. Assert length_ms == 1200000 (20:00) and base_length_ms == 1200000
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode (New mode auto-expires after 3s)
        logger.info("Waiting for chrono mode...")
        time.sleep(3.5)

        # Step 2: Enter edit mode (Up enters ControlModeNew)
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Did not receive button_up state"
        assert_mode(state, "New")
        logger.info(f"Entered New mode (editing chrono): {state}")

        # Step 3: Switch to EditSec (long press Select)
        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.3)
        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state is not None, "Did not receive long_press_select event"
        assert_mode(state, "EditSec")
        logger.info(f"Entered EditSec: {state}")

        # Step 4: Add 20 seconds (Up in EditSec = +20s)
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Did not receive button_up after +20s"
        assert_is_chrono(state, True)
        logger.info(f"After +20s in EditSec (still chrono): {state}")

        # Step 5: Wait for edit mode to expire → back to Counting (chrono)
        state = capture.wait_for_state(event="mode_change", timeout=10.0)
        assert state is not None, "Did not receive mode_change to Counting"
        assert_mode(state, "Counting")
        assert_is_chrono(state, True)
        logger.info(f"Back in Counting (chrono): {state}")

        # Step 6: Enter edit mode again (Up enters ControlModeNew)
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Did not receive button_up for second edit"
        assert_mode(state, "New")
        logger.info(f"Entered New mode again: {state}")

        # Step 7: Toggle reverse direction (long press Up)
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state is not None, "Did not receive long_press_up event"
        assert_direction(state, forward=False)
        logger.info(f"Toggled reverse direction: {state}")

        # Step 8: Press Up to subtract 20 minutes (crosses zero → countdown)
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Did not receive button_up after -20min"
        logger.info(f"After -20min (crossed zero to countdown): {state}")

        capture.stop()

        # Verify: should be a countdown timer, not chrono
        assert_is_chrono(state, False)
        # Direction should auto-flip to forward after zero-crossing
        assert_direction(state, forward=True)
        # The header should show 20:00 — the chrono elapsed time from the
        # first edit should NOT reduce the countdown value
        assert_base_length(state, 1200000)
        actual_tl = int(state.get('tl', '0'))
        assert actual_tl == 1200000, (
            f"Expected length_ms=1200000 (20:00 header), got {actual_tl}"
        )
