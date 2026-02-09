"""
Test Case: Edit Timer Direction and Zero-Crossing Behavior

Verifies timer editing behavior related to direction changes and zero-crossing
(chrono <-> countdown type conversion).

Reference: specs/edit-timer-direction-tests.md

Two test classes:
- TestZeroCrossingTypeConversion: Verify existing type conversion (should pass)
- TestAutoDirectionFlip: Verify auto-flip on zero-crossing (spec #22)
"""

import logging
import time

import pytest

from .conftest import (
    Button,
    LogCapture,
    assert_mode,
    assert_paused,
    assert_time_approximately,
    assert_direction,
    assert_is_chrono,
)

# Configure module logger
logger = logging.getLogger(__name__)


class TestZeroCrossingTypeConversion:
    """Tests verifying that zero-crossing correctly converts between chrono and countdown."""

    def test_countdown_to_chrono_via_subtraction_new_mode(self, persistent_emulator):
        """
        Test 1: Subtracting enough time from a countdown timer to go past zero
        converts it to a chrono timer (ControlModeNew).

        Steps:
        1. Press Down twice to set 2-minute timer
        2. Wait 4s for auto-start
        3. Press Up to enter edit mode
        4. Long press Up to toggle reverse direction
        5. Press Up (subtract 20 minutes) -> timer crosses zero -> chrono ~18:04
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Press Down twice to set 2-minute timer
        emulator.press_down()
        emulator.press_down()
        state = capture.wait_for_state(event="button_down", timeout=5.0)
        state = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state is not None
        assert_mode(state, "New")

        # Step 2: Wait for auto-start (3s inactivity -> ControlModeCounting)
        time.sleep(4.0)

        # Step 3: Press Up to enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")
        assert_direction(state_edit, forward=True)

        # Step 4: Long press Up to toggle reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 5: Press Up (subtract 20 minutes)
        emulator.press_up()
        state_sub = capture.wait_for_state(event="button_up", timeout=5.0)

        assert state_sub is not None
        logger.info(f"After subtraction state: {state_sub}")
        assert_is_chrono(state_sub, is_chrono=True)
        emulator.screenshot("chrono_via_subtraction_new_mode_after_subtraction")
        assert_time_approximately(state_sub, minutes=18, seconds=4, tolerance=10)

        time.sleep(4)

        emulator.press_down()  # To trigger a new state
        state_display = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()
        emulator.screenshot("chrono_via_subtraction_new_mode_after_down_press")
        assert_time_approximately(state_display, minutes=18, seconds=13, tolerance=10)

    def test_countdown_to_chrono_via_subtraction_editsec(self, persistent_emulator):
        """
        Test 2: Countdown -> chrono conversion works in ControlModeEditSec.

        Steps:
        1. Wait 3.5s for chrono mode
        2. Press Up to enter Edit mode
        3. Long press Select to enter EditSec at 0:00
        4. Press Down 5 times (+5 seconds)
        5. Long press Up to toggle reverse
        6. Press Back (subtract 60 seconds) -> crosses zero -> chrono ~0:55
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode
        time.sleep(3.5)

        # Step 2: Press Up to enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")

        # Step 3: Long press Select to enter EditSec at 0:00
        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        state_editsec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_editsec is not None
        assert_mode(state_editsec, "EditSec")

        # Step 4: Press Down 5 times (+5 seconds)
        for i in range(5):
            emulator.press_down()
            time.sleep(0.2)
        # Consume all button_down events
        state_down = None
        for i in range(5):
            state_down = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_down is not None
        assert_time_approximately(state_down, minutes=0, seconds=5, tolerance=1)

        # Step 5: Long press Up to toggle reverse
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 6: Press Back (subtract 60 seconds)
        emulator.press_back()
        state_sub = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        assert state_sub is not None
        logger.info(f"After subtraction state: {state_sub}")
        assert_is_chrono(state_sub, is_chrono=True)
        assert_time_approximately(state_sub, minutes=0, seconds=55, tolerance=5)


class TestAutoDirectionFlip:
    """Tests verifying auto-direction-flip on zero-crossing (spec #22)."""

    def test_auto_flip_countdown_to_chrono_new_mode(self, persistent_emulator):
        """
        Test 3: When subtracting from a countdown causes zero-crossing,
        direction automatically flips to forward (ControlModeNew).

        Steps:
        1. Press Down twice to set 2-minute timer
        2. Wait 4s for auto-start
        3. Press Up to enter edit mode
        4. Long press Up to toggle reverse
        5. Press Up (subtract 20 minutes) -> chrono ~18:04, direction forward
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Press Down twice to set 2-minute timer
        emulator.press_down()
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)
        capture.wait_for_state(event="button_down", timeout=5.0)

        # Step 2: Wait for auto-start
        time.sleep(4.0)

        # Step 3: Press Up to enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")

        # Step 4: Long press Up to toggle reverse
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 5: Press Up (subtract 20 minutes)
        emulator.press_up()
        state_sub = capture.wait_for_state(event="button_up", timeout=5.0)

        capture.stop()

        assert state_sub is not None
        logger.info(f"After zero-crossing state: {state_sub}")
        assert_is_chrono(state_sub, is_chrono=True)
        assert_direction(state_sub, forward=True)
        assert_time_approximately(state_sub, minutes=18, seconds=4, tolerance=10)

    def test_auto_flip_countdown_to_chrono_editsec(self, persistent_emulator):
        """
        Test 4: Auto-direction-flip works in ControlModeEditSec.

        Steps:
        1. Long press Select to enter EditSec at 0:00
        2. Press Down 5 times (+5 seconds)
        3. Long press Up to toggle reverse
        4. Press Back (subtract 60 seconds) -> chrono ~0:55, direction forward
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Enter EditSec - need to go through New mode first
        # Wait for chrono auto-start, then press Up, then long press Select
        time.sleep(2.5)
        emulator.press_up()
        capture.wait_for_state(event="button_up", timeout=5.0)

        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        state_editsec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_editsec is not None
        assert_mode(state_editsec, "EditSec")

        # Step 2: Press Down 5 times (+5 seconds)
        for i in range(5):
            emulator.press_down()
            time.sleep(0.2)
        state_down = None
        for i in range(5):
            state_down = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_down is not None

        # Step 3: Long press Up to toggle reverse
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 4: Press Back (subtract 60 seconds)
        emulator.press_back()
        state_sub = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        assert state_sub is not None
        logger.info(f"After zero-crossing state: {state_sub}")
        assert_is_chrono(state_sub, is_chrono=True)
        assert_direction(state_sub, forward=True)
        assert_time_approximately(state_sub, minutes=0, seconds=55, tolerance=5)

    def test_continued_editing_after_auto_flip_new_mode(self, persistent_emulator):
        """
        Test 5: After auto-direction-flip, subsequent button presses work in
        forward direction.

        Steps:
        1. Wait 4s for chrono mode with elapsed time
        2. Press Up to enter ControlModeNew
        3. Long press Up to toggle reverse
        4. Press Down (subtract 1 minute) -> crosses zero -> countdown ~0:56, forward
        5. Press Down (add 1 minute in forward direction) -> countdown ~1:56
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for chrono mode
        time.sleep(4.0)

        # Step 2: Press Up to enter ControlModeNew
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")
        assert_direction(state_edit, forward=True)

        # Step 3: Long press Up to toggle reverse
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir is not None
        assert_direction(state_dir, forward=False)

        # Step 4: Press Down (subtract 1 minute) -> crosses zero
        emulator.press_down()
        state_cross = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_cross is not None
        assert_direction(state_cross, forward=True)
        assert_is_chrono(state_cross, is_chrono=False)

        # Step 5: Press Down (add 1 minute in forward direction)
        emulator.press_down()
        state_add = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        assert state_add is not None
        logger.info(f"After adding 1 minute state: {state_add}")
        assert_time_approximately(state_add, minutes=1, seconds=58, tolerance=10)
        assert_direction(state_add, forward=True)

    def test_round_trip_zero_crossing_editsec(self, persistent_emulator):
        """
        Test 6: Two consecutive zero-crossings both trigger auto-direction-flip.

        Steps:
        1. Wait 2.5s, press Up, long press Select -> EditSec at 0:00
        2. Press Down 5 times (+5 seconds)
        3. Long press Up to toggle reverse
        4. Press Back (subtract 60s) -> chrono ~0:55, direction forward (1st flip)
        5. Long press Up to toggle reverse
        6. Press Back (subtract 60s) -> countdown ~0:05, direction forward (2nd flip)
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Enter EditSec
        time.sleep(2.5)
        emulator.press_up()
        capture.wait_for_state(event="button_up", timeout=5.0)

        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        state_editsec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_editsec is not None
        assert_mode(state_editsec, "EditSec")

        # Step 2: Press Down 5 times (+5 seconds)
        for i in range(5):
            emulator.press_down()
            time.sleep(0.2)
        state_down = None
        for i in range(5):
            state_down = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_down is not None

        # Step 3: Long press Up to toggle reverse
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir1 = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir1 is not None
        assert_direction(state_dir1, forward=False)

        # Step 4: Press Back (subtract 60 seconds) -> 1st zero-crossing
        emulator.press_back()
        state_cross1 = capture.wait_for_state(event="button_back", timeout=5.0)
        assert state_cross1 is not None
        assert_is_chrono(state_cross1, is_chrono=True)
        assert_direction(state_cross1, forward=True)

        # Step 5: Long press Up to toggle reverse again
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir2 = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_dir2 is not None
        assert_direction(state_dir2, forward=False)

        # Step 6: Press Back (subtract 60 seconds) -> 2nd zero-crossing
        emulator.press_back()
        state_cross2 = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        assert state_cross2 is not None
        logger.info(f"After 2nd zero-crossing state: {state_cross2}")
        assert_is_chrono(state_cross2, is_chrono=False)
        assert_direction(state_cross2, forward=True)
        assert_time_approximately(state_cross2, minutes=0, seconds=5, tolerance=3)
