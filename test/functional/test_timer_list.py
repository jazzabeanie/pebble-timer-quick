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
            f"Expected at least 2 list entries (New Timer + existing), got {list_count}. "
            f"Full state: {state}"
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

        # Start capture before open_app_via_menu so timer_list_show is not missed
        capture = LogCapture(platform)
        capture.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

        # Wait for timer list to appear
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

    # Load-flaky: the hold-to-delete gesture can be dropped by an under-load
    # emulator late in a long full-suite run (timer_list_delete never fires);
    # a fresh retry passes.
    @pytest.mark.flaky(reruns=2, reruns_delay=5)
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

        capture = LogCapture(platform)
        capture.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

        # Wait for timer list
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

        capture = LogCapture(platform)
        capture.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

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


####################################################################################################
# Delete all row, scrolling, and post-delete selection (openspec: add-stopwatch-laps)
#
# These behaviors are compiled out on aplite together with the lap feature
# (24KB app region), so the tests skip that platform.

import time as _time

# AppMessage key for the lap_stopwatch_enabled setting (see src/settings.c)
APPMSG_KEY_LAP_STOPWATCH_ENABLED = 15


def _skip_if_no_lap_feature(emulator):
    if emulator.platform == "aplite":
        pytest.skip("Delete all / lap feature is compiled out on aplite (RAM)")


def _create_second_timer(emulator, platform):
    """With one persisted timer, relaunch shows the Timer List; select the
    "New Timer" row and let it persist, leaving two timers stored."""
    capture = LogCapture(platform)
    capture.start()
    emulator.open_app_via_menu()
    show = capture.wait_for_state(event="timer_list_show", timeout=10.0)
    assert show is not None, "Timer List did not appear while creating 2nd timer"
    # timer_list_show is logged at the start of the animated window push; a
    # press sent before the transition settles is swallowed, so wait it out
    time.sleep(1.0)
    emulator.press_select()  # row 0 = New Timer -> main window, New mode
    assert capture.wait_for_state(event="timer_list_select_new", timeout=5.0) is not None
    capture.stop()
    emulator.press_select()  # +5 minutes
    time.sleep(3.5)          # expire to Counting
    emulator.press_back()    # exit, persist both timers
    time.sleep(0.5)


def _relaunch_to_list(emulator, platform, expected_count=None):
    capture = LogCapture(platform)
    capture.start()
    emulator.open_app_via_menu()
    show = capture.wait_for_state(event="timer_list_show", timeout=10.0)
    assert show is not None, "Timer List did not appear"
    if expected_count is not None:
        assert int(show.get("list_count", -1)) == expected_count, (
            f"Unexpected row count: {show}"
        )
    # timer_list_show is logged at the start of the animated window push; a
    # press sent before the transition settles is swallowed, so wait it out
    time.sleep(1.0)
    return capture, show


def _hold_down(emulator):
    # Settle after any preceding press so the hold isn't coalesced with it
    time.sleep(0.3)
    emulator.hold_button(Button.DOWN)
    time.sleep(1.0)
    emulator.release_buttons()
    time.sleep(0.5)


class TestDeleteAllRow:
    """The pinned "Delete all" bottom row and its behaviors."""

    def test_select_shows_hint_and_deletes_nothing(self, emulator):
        _skip_if_no_lap_feature(emulator)
        platform = emulator.platform
        _create_timer_and_background(emulator, platform)

        # Rows: 0 = New Timer, 1 = timer, 2 = Delete all
        capture, _ = _relaunch_to_list(emulator, platform, expected_count=3)
        emulator.press_down()
        emulator.press_down()
        emulator.press_select()
        hint = capture.wait_for_state(event="timer_list_delete_all_hint", timeout=5.0)
        assert hint is not None, "Select on Delete all did not show the hint"
        events = [s["event"] for s in capture.get_state_logs()]
        capture.stop()
        assert "timer_list_delete" not in events, "Select on Delete all deleted a timer"
        assert "timer_list_delete_all" not in events, "Select on Delete all cleared timers"

        # Nothing was deleted: exiting and relaunching still shows the timer.
        # Back persists the implicit new-timer slot, so the next launch shows
        # one extra timer row (New Timer + 2 timers + Delete all).
        emulator.press_back()
        time.sleep(1.0)
        capture2, _ = _relaunch_to_list(emulator, platform, expected_count=4)
        capture2.stop()

    # Load-flaky: the hold-to-delete-all gesture can be dropped by an under-load
    # emulator late in a long full-suite run (timer_list_delete_all never fires);
    # a fresh retry passes.
    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_hold_down_clears_all_and_exits(self, emulator):
        _skip_if_no_lap_feature(emulator)
        platform = emulator.platform
        _create_timer_and_background(emulator, platform)

        capture, _ = _relaunch_to_list(emulator, platform, expected_count=3)
        emulator.press_down()
        emulator.press_down()
        _hold_down(emulator)
        cleared = capture.wait_for_state(event="timer_list_delete_all", timeout=5.0)
        capture.stop()
        assert cleared is not None, "Hold Down on Delete all did not clear timers"

        # All timers gone: a fresh launch starts in the main window (no list).
        # Read the queue non-destructively so one check cannot consume the
        # other's event.
        capture2 = LogCapture(platform)
        capture2.start()
        emulator.open_app_via_menu()
        _time.sleep(3.0)
        events = [s["event"] for s in capture2.get_state_logs()]
        capture2.stop()
        assert "timer_list_show" not in events, (
            f"Timer List appeared although all timers were deleted: {events}"
        )
        assert "init" in events, (
            f"App did not restart cleanly after Delete all: {events}"
        )


class TestPostDeleteSelection:
    """Deleting an entry selects the previous timer (never Delete all)."""

    # Load-flaky: relies on the hold-to-delete gesture TWICE, so it has double
    # exposure to an under-load emulator dropping the gesture (timer_list_delete
    # never fires) late in a long full-suite run; a fresh retry passes.
    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_delete_selects_previous_then_new_timer(self, emulator):
        _skip_if_no_lap_feature(emulator)
        platform = emulator.platform
        _create_timer_and_background(emulator, platform)
        _create_second_timer(emulator, platform)

        # Rows: 0 = New Timer, 1 = timer A, 2 = timer B, 3 = Delete all
        capture, _ = _relaunch_to_list(emulator, platform, expected_count=4)

        # Delete the bottom timer (row 2): the previous timer (row 1) is selected
        emulator.press_down()
        emulator.press_down()
        _hold_down(emulator)
        deleted = capture.wait_for_state(event="timer_list_delete", timeout=5.0)
        assert deleted is not None, "First delete did not fire"
        assert int(deleted.get("sel", -1)) == 1, (
            f"Expected previous timer (row 1) selected: {deleted}"
        )
        assert int(deleted.get("list_count", -1)) == 3, deleted

        # Delete the only remaining timer: the New Timer row is selected
        _hold_down(emulator)
        deleted2 = capture.wait_for_state(event="timer_list_delete", timeout=5.0)
        capture.stop()
        assert deleted2 is not None, "Second delete did not fire"
        assert int(deleted2.get("sel", -1)) == 0, (
            f"Expected New Timer row selected after deleting the last timer: {deleted2}"
        )

    # Load-flaky: the hold-to-delete gesture can be dropped by an under-load
    # emulator late in a long full-suite run (timer_list_delete never fires);
    # a fresh retry passes.
    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_delete_topmost_keeps_position(self, emulator):
        _skip_if_no_lap_feature(emulator)
        platform = emulator.platform
        _create_timer_and_background(emulator, platform)
        _create_second_timer(emulator, platform)

        capture, _ = _relaunch_to_list(emulator, platform, expected_count=4)

        # Delete the topmost timer (row 1): the position is kept so the next
        # timer shifts up into the selection (still row 1, never Delete all)
        emulator.press_down()
        _hold_down(emulator)
        deleted = capture.wait_for_state(event="timer_list_delete", timeout=5.0)
        capture.stop()
        assert deleted is not None, "Delete did not fire"
        assert int(deleted.get("sel", -1)) == 1, (
            f"Expected position kept at row 1 after deleting topmost: {deleted}"
        )
        assert int(deleted.get("list_count", -1)) == 3, deleted


class TestListScrolling:
    """With many slots the list scrolls so every row stays reachable."""

    def test_scroll_reaches_delete_all(self, emulator):
        _skip_if_no_lap_feature(emulator)
        platform = emulator.platform

        # Create 5 timers quickly: a running stopwatch plus 4 laps. The setting
        # is sent twice because the phone JS pushes defaults shortly after
        # install and can race (and overwrite) the first send.
        capture = LogCapture(platform)
        capture.start()
        emulator.send_app_message_int(APPMSG_KEY_LAP_STOPWATCH_ENABLED, 1)
        time.sleep(3.0)
        emulator.send_app_message_int(APPMSG_KEY_LAP_STOPWATCH_ENABLED, 1)
        for i in range(4):
            emulator.press_select()
            lap = capture.wait_for_state(event="lap_recorded", timeout=5.0)
            assert lap is not None, f"Lap {i + 1} was not recorded for scrolling test"
            time.sleep(0.3)
        emulator.press_back()
        time.sleep(1.0)
        capture.stop()

        # Rows: New Timer + 5 timers + Delete all = 7 (taller than the screen)
        capture2, show = _relaunch_to_list(emulator, platform, expected_count=7)
        rows = int(show.get("list_count"))
        for _ in range(rows - 1):
            emulator.press_down()
            time.sleep(0.15)
        # Reaching and activating the bottom row proves the list scrolled
        emulator.press_select()
        hint = capture2.wait_for_state(event="timer_list_delete_all_hint", timeout=5.0)
        capture2.stop()
        assert hint is not None, (
            "Could not reach the Delete all row at the bottom of a scrolled list"
        )
