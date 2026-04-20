"""
Functional tests for multi-timer Timer List window.

These tests verify the Timer List behavior:
- Timer List shows when existing timers are present
- Selecting an existing timer opens it in counting mode
- Selecting "New Timer" opens edit mode
- Hold Down on existing entry deletes the timer
- 30s idle → app backgrounds, implicit timer persisted

Setup strategy: Use the app UI to create a timer, background the app (press Back),
then re-launch so the timer list appears.
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


def _create_timer_and_background(emulator: EmulatorHelper, platform: str):
    """
    Helper: create a 5-minute countdown timer and background the app.

    Flow:
    - App is in ControlModeNew (fresh start)
    - Press Select 5× to add 25 minutes, then wait for new_expire_timer (3s)
    - Actually: just wait for the 3s new_expire_timer to auto-transition to Counting
    - Press Select once to add 5 minutes worth (1 press = 5 min)
    - Then press Back to exit → timer persisted
    """
    capture = LogCapture(platform)
    capture.start()
    time.sleep(0.5)

    # Press Select once to add 5 minutes
    emulator.press_select()

    # Wait for button_select state
    state = capture.wait_for_state(event="button_select", timeout=5.0)
    capture.stop()
    assert state is not None, "No button_select event received"

    # Wait for new_expire_timer (3 seconds) to transition to Counting mode
    time.sleep(3.5)

    # Press Back to exit and persist the timer
    emulator.press_back()
    time.sleep(0.5)


class TestTimerList:
    """Tests for the Timer List window (multi-timer feature)."""

    def test_timer_list_shown_with_existing_timer(self, emulator):
        """
        5.1: App opens to Timer List when an existing timer is present.

        Flow:
        1. Create a timer and background the app
        2. Re-launch the app
        3. Verify the Timer List is shown (TEST_STATE event=timer_list_show)
        """
        platform = emulator.platform

        # Step 1: Create a timer and background
        _create_timer_and_background(emulator, platform)

        # Step 2: Re-launch the app
        capture = LogCapture(platform)
        capture.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

        # Step 3: Wait for timer_list_show event
        state = capture.wait_for_state(event="timer_list_show", timeout=5.0)
        capture.stop()

        assert state is not None, (
            "Timer List was not shown. Expected TEST_STATE:timer_list_show. "
            f"All logs: {capture.get_all_logs()}"
        )
        assert state.get("m") == "TimerList", f"Unexpected mode: {state}"
        # At least 2 rows: "New Timer" + the existing timer
        list_count = int(state.get("list_count", 0))
        assert list_count >= 2, (
            f"Expected at least 2 list entries (New Timer + existing), got {list_count}"
        )

    def test_select_existing_timer_opens_counting_mode(self, emulator):
        """
        5.2: Selecting an existing timer from the list opens the normal timer view.
        The implicit new timer is discarded.

        Flow:
        1. Create a timer, background, re-launch → timer list
        2. Press Down to navigate to existing timer (row 1)
        3. Press Select → main window opens in Counting mode
        """
        platform = emulator.platform

        # Create timer and re-launch to show list
        _create_timer_and_background(emulator, platform)
        emulator.open_app_via_menu()
        time.sleep(1.0)

        capture = LogCapture(platform)
        capture.start()

        # Navigate to existing timer (row 1 = first existing timer below "New Timer")
        emulator.press_down()
        time.sleep(0.3)

        # Select the existing timer
        emulator.press_select()

        # Wait for the select_existing event
        state = capture.wait_for_state(event="timer_list_select_existing", timeout=5.0)
        capture.stop()

        assert state is not None, (
            "Did not receive timer_list_select_existing event. "
            f"All logs: {capture.get_all_logs()}"
        )

        # After selection, main window should be in Counting mode
        capture2 = LogCapture(platform)
        capture2.start()
        # Trigger a state log by pressing Down (no-op in counting mode but logs)
        time.sleep(0.5)
        emulator.press_down()
        state2 = capture2.wait_for_state(event="button_down", timeout=5.0)
        capture2.stop()

        assert state2 is not None, "No button_down state received after timer selection"
        assert_mode(state2, "Counting")

    def test_select_new_timer_opens_edit_mode(self, emulator):
        """
        5.3: Selecting "New Timer" from the list opens edit mode.

        Flow:
        1. Create a timer, background, re-launch → timer list shows
        2. Press Select (row 0 = "New Timer" is selected by default)
        3. Verify main window opens in New mode
        """
        platform = emulator.platform

        _create_timer_and_background(emulator, platform)
        emulator.open_app_via_menu()
        time.sleep(1.0)

        # Wait for timer list to appear
        capture = LogCapture(platform)
        capture.start()
        state = capture.wait_for_state(event="timer_list_show", timeout=5.0)
        assert state is not None, "Timer List did not appear"

        # Press Select on "New Timer" (default selection = row 0)
        emulator.press_select()

        select_state = capture.wait_for_state(event="timer_list_select_new", timeout=5.0)
        capture.stop()

        assert select_state is not None, (
            "Did not receive timer_list_select_new event. "
            f"All logs: {capture.get_all_logs()}"
        )

        # Main window should now be in New (edit) mode
        capture2 = LogCapture(platform)
        capture2.start()
        time.sleep(0.3)
        emulator.press_up()
        state2 = capture2.wait_for_state(event="button_up", timeout=5.0)
        capture2.stop()

        assert state2 is not None, "No button_up state after selecting New Timer"
        assert_mode(state2, "New")

    def test_hold_down_deletes_existing_timer(self, emulator):
        """
        5.4: Hold Down on an existing timer entry deletes it and refreshes the list.

        Flow:
        1. Create a timer, background, re-launch → timer list
        2. Press Down to navigate to existing timer
        3. Hold Down → timer deleted, list refreshes
        4. Verify the delete event was logged and list_count decreased
        """
        platform = emulator.platform

        _create_timer_and_background(emulator, platform)
        emulator.open_app_via_menu()
        time.sleep(1.0)

        # Wait for timer list
        capture = LogCapture(platform)
        capture.start()
        show_state = capture.wait_for_state(event="timer_list_show", timeout=5.0)
        assert show_state is not None, "Timer List did not appear"
        initial_count = int(show_state.get("list_count", 0))

        # Navigate to existing timer (row 1)
        emulator.press_down()
        time.sleep(0.3)

        # Hold Down to delete
        emulator.hold_button(Button.DOWN)
        time.sleep(1.0)  # Hold for long-click threshold (750ms)
        emulator.release_buttons()
        time.sleep(0.5)

        # Wait for delete event
        delete_state = capture.wait_for_state(event="timer_list_delete", timeout=5.0)
        capture.stop()

        assert delete_state is not None, (
            "Did not receive timer_list_delete event. "
            f"All logs: {capture.get_all_logs()}"
        )

        # After deletion, list_count should have decreased
        new_count = int(delete_state.get("list_count", initial_count))
        assert new_count < initial_count, (
            f"List count did not decrease after deletion: {initial_count} → {new_count}"
        )

    def test_idle_backgrounds_and_persists_implicit_timer(self, emulator):
        """
        5.5: 30s idle → app backgrounds, implicit timer is persisted.

        Flow:
        1. Create a timer, background, re-launch → timer list shows
        2. Wait 30s without pressing any button
        3. Verify idle_background event logged
        4. Re-launch app → timer list shows with 2 timers (original + implicit)
        """
        platform = emulator.platform

        _create_timer_and_background(emulator, platform)
        emulator.open_app_via_menu()
        time.sleep(1.0)

        capture = LogCapture(platform)
        capture.start()

        # Wait for timer list
        show_state = capture.wait_for_state(event="timer_list_show", timeout=5.0)
        assert show_state is not None, "Timer List did not appear"

        # Wait for the 30-second idle timer to fire (add 5s buffer)
        logger.info(f"[{platform}] Waiting 35s for idle timer to fire...")
        idle_state = capture.wait_for_state(event="timer_list_idle_background", timeout=38.0)
        capture.stop()

        assert idle_state is not None, (
            "Idle auto-background did not fire within 38 seconds. "
            f"All logs: {capture.get_all_logs()}"
        )

        # Re-launch the app - should show timer list with 2 timers (original + implicit)
        time.sleep(0.5)
        capture2 = LogCapture(platform)
        capture2.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

        show_state2 = capture2.wait_for_state(event="timer_list_show", timeout=5.0)
        capture2.stop()

        assert show_state2 is not None, "Timer List not shown on second launch"
        second_count = int(show_state2.get("list_count", 0))
        # Should have: New Timer + original timer + persisted implicit timer = 3 rows
        # Or at minimum: New Timer + 2 existing = 3
        assert second_count >= 3, (
            f"Expected at least 3 list entries after implicit timer persisted, got {second_count}"
        )

    def test_timer_list_not_shown_without_existing_timers(self, emulator):
        """
        5.6: App opens normally (no timer list) when no timers are present.

        Flow:
        1. Fresh start (no prior timers)
        2. Launch app
        3. Verify timer list is NOT shown (mode should be New or Counting)
        """
        platform = emulator.platform

        capture = LogCapture(platform)
        capture.start()
        time.sleep(0.5)

        # Check no timer_list_show event fires within 2 seconds
        # (if it fires, something is wrong)
        state = capture.wait_for_state(event="timer_list_show", timeout=2.0)

        # Also check the init event
        init_state = capture.wait_for_state(event="init", timeout=3.0)
        capture.stop()

        assert state is None, (
            "Timer List appeared on fresh start — it should not! "
            f"State: {state}"
        )
        # Verify app is in normal mode (not timer list)
        if init_state is not None:
            mode = init_state.get("m", "")
            assert mode in ("New", "Counting"), (
                f"Expected New or Counting mode on fresh start, got '{mode}'"
            )
