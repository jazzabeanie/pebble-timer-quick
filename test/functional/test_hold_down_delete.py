"""
Functional tests for Hold Down behavior in main timer window (multi-timer).

7.2: Hold Down inside open timer → only that timer deleted, app exits;
     other timers remain persisted.
"""

import logging
import time
import pytest

from .conftest import (
    Button,
    EmulatorHelper,
    LogCapture,
    assert_mode,
)

logger = logging.getLogger(__name__)


def _create_two_timers_and_open_second(emulator: EmulatorHelper, platform: str):
    """
    Helper: create 2 timers, then open the second one from the timer list.

    Returns after the main window is showing the second timer.
    """
    # Create timer 1: press Select to add 5 min, wait for expire, press Back to save
    capture = LogCapture(platform)
    capture.start()
    time.sleep(0.3)
    emulator.press_select()  # adds 5 min
    capture.wait_for_state(event="button_select", timeout=5.0)
    capture.stop()
    time.sleep(3.5)  # wait for new_expire_timer → counting mode
    emulator.press_back()
    time.sleep(0.5)

    # Re-launch → timer list appears (1 existing + implicit New Timer)
    emulator.open_app_via_menu()
    time.sleep(1.0)

    # Timer list is showing. Create timer 2 by pressing Select on "New Timer" (row 0)
    # Then add 10 min inside, wait for expire, come back to timer list
    emulator.press_select()  # selects "New Timer"
    time.sleep(0.5)
    # Now in main window in ControlModeNew for the implicit slot
    emulator.press_up()     # +20 min
    time.sleep(3.5)  # wait for new_expire_timer → Counting
    emulator.press_back()   # exit → both timers persisted
    time.sleep(0.5)

    # Re-launch → timer list with 2 existing timers + "New Timer" row
    emulator.open_app_via_menu()
    time.sleep(1.0)

    # Navigate to row 1 (first existing timer - the 5-min one)
    emulator.press_down()   # select row 1
    time.sleep(0.3)
    emulator.press_select() # open it
    time.sleep(0.5)
    # Now in main window showing the 5-min timer


class TestHoldDownDelete:
    """Tests for Hold Down delete behavior in the main timer window."""

    def test_hold_down_in_main_window_deletes_only_active_timer(self, emulator):
        """
        7.2: Hold Down inside open timer deletes only that timer and exits.
        Other timers remain persisted.

        Flow:
        1. Create 2 timers and open one from the timer list
        2. Hold Down in the main window → active timer deleted, app exits
        3. Re-launch → timer list shows with only 1 existing timer remaining
        """
        platform = emulator.platform

        _create_two_timers_and_open_second(emulator, platform)

        # Hold Down to delete the active timer
        capture = LogCapture(platform)
        capture.start()

        emulator.hold_button(Button.DOWN)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.5)

        # Wait for long_press_down event
        state = capture.wait_for_state(event="long_press_down", timeout=5.0)
        capture.stop()

        assert state is not None, (
            "No long_press_down event received. "
            f"All logs: {capture.get_all_logs()}"
        )

        # Re-launch app — should show timer list with 1 remaining timer
        time.sleep(0.5)
        capture2 = LogCapture(platform)
        capture2.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

        list_state = capture2.wait_for_state(event="timer_list_show", timeout=5.0)
        capture2.stop()

        assert list_state is not None, (
            "Timer List did not appear on relaunch after hold-down delete. "
            "Expected 1 remaining timer to trigger timer list."
        )
        # Should have: 1 existing timer + "New Timer" = 2 rows
        list_count = int(list_state.get("list_count", 0))
        assert list_count == 2, (
            f"Expected 2 list rows (New Timer + 1 remaining timer), got {list_count}"
        )

    def test_hold_down_single_timer_exits_cleanly(self, emulator):
        """
        7.2 (single-timer case): Hold Down with only 1 timer exits app cleanly.
        On relaunch, no timer list (0 existing timers → fresh start).

        Flow:
        1. Create 1 timer, background, re-launch → timer list
        2. Select the existing timer
        3. Hold Down → timer deleted, app exits
        4. Re-launch → NO timer list (fresh start)
        """
        platform = emulator.platform

        # Create timer and re-launch to show timer list
        capture = LogCapture(platform)
        capture.start()
        time.sleep(0.3)
        emulator.press_select()  # +5 min
        capture.wait_for_state(event="button_select", timeout=5.0)
        capture.stop()
        time.sleep(3.5)
        emulator.press_back()
        time.sleep(0.5)

        emulator.open_app_via_menu()
        time.sleep(1.0)

        # Navigate to existing timer
        emulator.press_down()
        time.sleep(0.3)
        emulator.press_select()
        time.sleep(0.5)

        # Hold Down to delete
        capture2 = LogCapture(platform)
        capture2.start()
        emulator.hold_button(Button.DOWN)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.5)

        state = capture2.wait_for_state(event="long_press_down", timeout=5.0)
        capture2.stop()
        assert state is not None, "No long_press_down event"

        # Re-launch → should NOT show timer list (no remaining timers)
        time.sleep(0.5)
        capture3 = LogCapture(platform)
        capture3.start()
        emulator.open_app_via_menu()
        time.sleep(1.5)

        # No timer_list_show should appear
        list_state = capture3.wait_for_state(event="timer_list_show", timeout=2.0)
        # But init should appear
        init_state = capture3.wait_for_state(event="init", timeout=3.0)
        capture3.stop()

        assert list_state is None, (
            f"Timer List appeared after deleting the only timer — it should not! State: {list_state}"
        )
        if init_state is not None:
            mode = init_state.get("m", "")
            assert mode in ("New", "Counting"), f"Expected fresh start mode, got '{mode}'"
