"""
Functional tests for the Lap Stopwatch feature (openspec: add-stopwatch-laps).

Covered behaviors:
- Select on a running stopwatch records a lap (paused copy in a new slot,
  original keeps running and stays active) when `Lap Stopwatch` is enabled.
- Lap slots are named "Lap [n]: <name>" with n incrementing per source.
- The recorded lap flashes (1s lap / 1s original) for ~5 seconds; Select
  during the flash cancels it and records the next lap, while Back cancels it
  and opens the recorded lap instead of exiting the app.
- Split/total display: main value shows the current split, header shows the
  total prefixed with "-->" while lapping is enabled.
- Approaching-limit warning at <= 3 free slots; "no free slots" guard at
  capacity (original keeps running, play/pause state unchanged).
- Long-press Select restarts the stopwatch and resets lap numbering.
- All 32 slots persist and reload (fill to capacity, relaunch, count rows).

The lap feature is compiled out on aplite (24KB app region), so these tests
skip that platform.
"""

import logging
import time

import pytest

from .conftest import Button, LogCapture, assert_mode

logger = logging.getLogger(__name__)

# AppMessage key for the lap_stopwatch_enabled setting (see src/settings.c)
APPMSG_KEY_LAP_STOPWATCH_ENABLED = 15

# MAX_TIMERS on all lap-capable platforms (see src/timer.h)
MAX_TIMERS = 32


def _skip_if_no_lap_feature(emulator):
    if emulator.platform == "aplite":
        pytest.skip("Lap Stopwatch feature is compiled out on aplite (RAM)")


def _enable_lap_setting(emulator):
    """Enable the Lap Stopwatch setting via AppMessage (default is off)."""
    emulator.send_app_message_int(APPMSG_KEY_LAP_STOPWATCH_ENABLED, 1)
    time.sleep(0.5)


def _wait_for_counting_stopwatch(emulator, capture):
    """The emulator fixture leaves the app in New mode; the 3s new-expire timer
    moves it to Counting as a running stopwatch. Wait it out and verify."""
    time.sleep(3.5)
    capture.clear_state_queue()
    emulator.press_down()  # no-op in Counting, but logs state
    state = capture.wait_for_state(event="button_down", timeout=5.0)
    assert state is not None, "No button_down state; app not responding"
    assert_mode(state, "Counting")
    assert state.get("c") == "1", f"Expected a chrono (stopwatch), got {state}"
    assert state.get("p") == "0", f"Expected a running stopwatch, got {state}"
    return state


def _record_laps(emulator, capture, count, delay=0.6, others=None):
    """Press Select `count` times, returning the lap_recorded states.

    Non-lap events drained while waiting (flash phases, limit warnings, ...)
    are appended to `others` when a list is passed, since wait_for_state
    discards non-matching entries.
    """
    laps = []
    for _ in range(count):
        emulator.press_select()
        lap = None
        deadline = time.time() + 5.0
        while time.time() < deadline:
            state = capture.wait_for_state(timeout=0.5)
            if state is None:
                continue
            if state["event"] == "lap_recorded":
                lap = state
                break
            if others is not None:
                others.append(state)
        assert lap is not None, (
            f"Lap {len(laps) + 1} was not recorded. Logs: {capture.get_all_logs()[-10:]}"
        )
        laps.append(lap)
        time.sleep(delay)
    return laps


class TestLapRecording:
    """7.1: recording a lap and the Lap [n]: naming scheme."""

    def test_lap_creates_paused_copy_and_original_keeps_running(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        others = []
        laps = _record_laps(emulator, capture, 1, others=others)
        lap = laps[0]
        # A new slot was created and the original is still running (p=0)
        assert lap.get("name", "").startswith("Lap 1: "), f"Bad lap name: {lap}"
        assert lap.get("p") == "0", f"Original paused after lap: {lap}"
        # 2 slots used (original + lap) leaves MAX_TIMERS - 2 free
        assert int(lap.get("free", -1)) == MAX_TIMERS - 2, f"Unexpected free count: {lap}"

        # No approaching-limit warning while plenty of slots remain
        events = [s["event"] for s in others + capture.get_state_logs()]
        assert "limit_warning" not in events, "limit_warning fired with >3 slots free"

        # Buttons still act on the original running stopwatch
        capture.clear_state_queue()
        emulator.press_down()
        state = capture.wait_for_state(event="button_down", timeout=5.0)
        capture.stop()
        assert state is not None
        assert_mode(state, "Counting")
        assert state.get("p") == "0", "Original stopwatch stopped running after lap"

    def test_lap_numbering_increments(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        laps = _record_laps(emulator, capture, 3)
        capture.stop()
        names = [lap.get("name", "") for lap in laps]
        assert names[0].startswith("Lap 1: "), names
        assert names[1].startswith("Lap 2: "), names
        assert names[2].startswith("Lap 3: "), names
        # The source name after the prefix is the same for every lap
        bases = {name.split(": ", 1)[1] for name in names}
        assert len(bases) == 1, f"Lap base names differ: {names}"

    def test_select_toggles_pause_when_setting_off(self, emulator):
        """With Lap Stopwatch off, Select keeps the play/pause behavior."""
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        # Setting intentionally NOT enabled
        _wait_for_counting_stopwatch(emulator, capture)

        capture.clear_state_queue()
        emulator.press_select()
        state = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state is not None
        assert state.get("p") == "1", f"Select did not pause the stopwatch: {state}"
        events = [s["event"] for s in capture.get_state_logs()]
        capture.stop()
        assert "lap_recorded" not in events, "Lap recorded although setting is off"


class TestLapFlash:
    """7.2: the 5-second lap/original flash and the re-lap window."""

    def test_flash_alternates_then_ends(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        capture.clear_state_queue()
        emulator.press_select()
        lap = capture.wait_for_state(event="lap_recorded", timeout=5.0)
        assert lap is not None

        # Collect flash phases until the flash ends (~5s window)
        phases = []
        end = None
        deadline = time.time() + 8.0
        while time.time() < deadline:
            state = capture.wait_for_state(timeout=1.0)
            if state is None:
                continue
            if state["event"] == "flash_phase":
                phases.append(state.get("lap"))
            elif state["event"] == "flash_end":
                end = state
                break
        capture.stop()

        assert end is not None, f"Flash never ended; phases seen: {phases}"
        assert len(phases) >= 3, f"Expected several flash phases, got {phases}"
        # Phases alternate between original (0) and lap (1)
        for a, b in zip(phases, phases[1:]):
            assert a != b, f"Flash phases did not alternate: {phases}"

    def test_select_during_flash_records_next_lap(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        # Two Selects ~1s apart: the second lands inside the first flash window
        laps = _record_laps(emulator, capture, 2, delay=1.0)
        capture.stop()
        assert laps[0].get("name", "").startswith("Lap 1: ")
        assert laps[1].get("name", "").startswith("Lap 2: ")
        # Original still running after the re-lap
        assert laps[1].get("p") == "0"

    def test_back_during_flash_views_lap(self, emulator):
        """Back inside the flash window opens the paused lap, not the original."""
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        capture.clear_state_queue()
        emulator.press_select()
        lap = capture.wait_for_state(event="lap_recorded", timeout=5.0)
        assert lap is not None
        lap_slot = lap.get("slot")

        # Back well inside the 5s flash window switches to the lap slot
        emulator.press_back()
        view = capture.wait_for_state(event="flash_view_lap", timeout=5.0)
        assert view is not None, (
            f"Back did not open the lap. Logs: {capture.get_all_logs()[-10:]}"
        )
        assert view.get("slot") == lap_slot, f"Opened the wrong slot: {view}"

        # The app is still alive, in Counting mode, showing the paused lap
        state = capture.wait_for_state(event="button_back", timeout=5.0)
        capture.stop()
        assert state is not None, "App exited instead of viewing the lap"
        assert_mode(state, "Counting")
        assert state.get("p") == "1", f"Active timer is not the paused lap: {state}"


class TestSplitTotalDisplay:
    """7.2b: main value shows the split; header shows the total with -->."""

    def test_header_shows_total_after_lap(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        # Let the total grow, then lap: the split restarts while the total keeps
        # counting, so during the flash the original's frames show
        # main (split) < header (total), both fed by the same stopwatch.
        time.sleep(3.0)
        capture.clear_state_queue()
        emulator.press_select()
        assert capture.wait_for_state(event="lap_recorded", timeout=5.0) is not None

        # The flash forces display logs for both the lap slot and the original
        lap_frames = []
        orig_frames = []
        deadline = time.time() + 5.0
        while time.time() < deadline:
            state = capture.wait_for_state(event="display", timeout=1.0)
            if state is None:
                continue
            if state.get("slot", "0") != "0":
                lap_frames.append(state)
            else:
                orig_frames.append(state)
        capture.stop()

        def to_seconds(text):
            # "M:SS" or "M:SS.mmm" -> float seconds ("_" power-degradation
            # placeholders are treated as 0)
            text = text.lstrip("-")
            minutes, _, rest = text.partition(":")
            rest = rest.replace("_", "0")
            minutes = minutes.replace("_", "0") or "0"
            return int(minutes) * 60 + float(rest or 0)

        assert lap_frames, "No display frames for the lap slot during the flash"
        assert orig_frames, "No display frames for the original during the flash"

        # Lap slot (paused chrono): header shows cumulative with --> prefix and
        # the main value shows the split; the first lap's split equals its
        # cumulative total.
        lap = lap_frames[0]
        assert lap.get("hdr", "").startswith("-->"), f"Lap header not -->: {lap}"
        lap_hdr_s = to_seconds(lap["hdr"][3:])
        lap_disp_s = to_seconds(lap["disp"])
        assert abs(lap_hdr_s - lap_disp_s) <= 1, (
            f"First lap split should equal its cumulative total: {lap}"
        )

        # Original (running): header total keeps counting while the main value
        # restarted as the new split -> split strictly smaller than total.
        orig = orig_frames[0]
        assert orig.get("hdr", "").startswith("-->"), f"Header not total form: {orig}"
        total_s = to_seconds(orig["hdr"][3:])
        split_s = to_seconds(orig["disp"])
        assert split_s < total_s, (
            f"Main value should show the split (< total) after a lap: {orig}"
        )

    def test_header_shows_start_time_when_lapping_disabled(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _wait_for_counting_stopwatch(emulator, capture)

        # Force a fresh Counting-mode display log: enter edit (Up) and let the
        # 3s new-expire timer drop back to Counting (each mode change logs).
        capture.clear_state_queue()
        emulator.press_up()
        time.sleep(4.0)
        states = [s for s in capture.get_state_logs() if s["event"] == "display"]
        capture.stop()
        assert states, "No display logs captured"
        # A genuine stopwatch's header now shows the time of day it was
        # started, prefixed with "@" (disambiguates from an overtime
        # countdown's unchanged base-length header, see
        # test_overtime_countdown_header_unchanged_when_lapping_disabled)
        # and suffixed with the count-up arrow, e.g. "@14:07-->".
        last = states[-1]
        hdr = last.get("hdr", "")
        assert hdr.startswith("@"), f"Expected '@'-prefixed start-time header: {last}"
        assert hdr.endswith("-->"), f"Expected trailing --> header: {last}"
        assert hdr != "@00:00-->", f"Header still shows the old placeholder: {last}"

    def test_overtime_countdown_header_unchanged_when_lapping_disabled(self, persistent_emulator):
        """An ordinary countdown that runs into overtime keeps its base-length
        header (e.g. "00:01-->") -- not the new stopwatch start-time header --
        since it was never a genuine (0-length) stopwatch. Regression test for
        `timer_is_chrono()` also being true for overtime countdowns.

        Uses persistent_emulator (like test_base_length.py) rather than the
        plain emulator fixture: the emulator fixture's per-test warm-up sleeps
        3s before the test body runs, which already consumes the New-mode
        window this test needs to catch with a long-press Select.
        """
        emulator = persistent_emulator
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)

        # Long press Select to enter EditSec mode from New mode (must happen
        # before the 3s new-expire timer fires).
        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.3)
        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state is not None, "Did not receive long_press_select event"
        assert_mode(state, "EditSec")

        # Set a 1-second countdown (Down in EditSec adds 1s) so it reaches
        # overtime quickly.
        capture.clear_state_queue()
        emulator.press_down()
        state = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state is not None, "Did not receive button_down state"

        # Let EditSec expire into Counting (3s), then let the 1s countdown
        # run past zero into overtime.
        capture.clear_state_queue()
        time.sleep(5.0)

        states = [s for s in capture.get_state_logs() if s["event"] == "display"]
        capture.stop()
        assert states, "No display logs captured"
        last = states[-1]
        assert last.get("hdr", "") == "00:01-->", (
            f"Expected unchanged base-length header for an overtime countdown: {last}"
        )


class TestSlotLimit:
    """7.2/7.2a/1.2a: capacity guard, approaching-limit warning, persistence."""

    def test_fill_to_capacity_warns_and_persists(self, emulator):
        _skip_if_no_lap_feature(emulator)
        platform = emulator.platform
        capture = LogCapture(platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        # Fill every remaining slot via laps: original + 31 laps = 32
        others = []
        laps = _record_laps(emulator, capture, MAX_TIMERS - 1, delay=0.3, others=others)
        frees = [int(lap.get("free", -1)) for lap in laps]
        assert frees[-1] == 0, f"Expected the last lap to leave 0 free: {frees}"

        # Approaching-limit warnings fired for every lap leaving <= 3 free
        warnings = [s for s in others + capture.get_state_logs()
                    if s["event"] == "limit_warning"]
        warn_frees = sorted(int(w.get("free", -1)) for w in warnings)
        assert warn_frees == [0, 1, 2, 3], f"Expected warnings at 3..0 free: {warn_frees}"
        assert all(w.get("src") == "lap" for w in warnings), warnings

        # At capacity: Select records nothing, warns, and the original keeps
        # running with its play/pause state unchanged
        capture.clear_state_queue()
        emulator.press_select()
        full = capture.wait_for_state(event="lap_full", timeout=5.0)
        assert full is not None, "No lap_full warning at capacity"
        assert full.get("p") == "0", f"Original no longer running at capacity: {full}"
        events = [s["event"] for s in capture.get_state_logs()]
        assert "lap_recorded" not in events, "A lap was recorded at capacity"

        # 1.2a: all 32 slots persist and reload within the persist budget.
        # Exit via Back (persists), relaunch, and count the Timer List rows:
        # 32 timers + Delete all (no New Timer row at capacity) = 33.
        time.sleep(3.5)  # let the at-capacity warning overlay clear
        emulator.press_back()
        time.sleep(1.0)
        capture.clear_state_queue()
        emulator.open_app_via_menu()
        show = capture.wait_for_state(event="timer_list_show", timeout=10.0)
        capture.stop()
        assert show is not None, "Timer List did not appear after relaunch"
        assert int(show.get("list_count", 0)) == MAX_TIMERS + 1, (
            f"Expected {MAX_TIMERS} persisted timers + Delete all row: {show}"
        )

    def test_new_timer_near_limit_shows_warning(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        # 27 laps -> 28 slots used, 4 free. Opening the Timer List creates the
        # implicit new timer (29 used, 3 free) and must warn.
        _record_laps(emulator, capture, 27, delay=0.3)
        emulator.press_back()
        time.sleep(1.0)
        capture.clear_state_queue()
        emulator.open_app_via_menu()

        warning = capture.wait_for_state(event="limit_warning", timeout=10.0)
        assert warning is not None, "No approaching-limit warning for a new timer"
        assert warning.get("src") == "timer", f"Wrong warning source: {warning}"
        assert int(warning.get("free", -1)) == 3, f"Wrong free count: {warning}"

        # The 3-second overlay auto-dismisses
        dismiss = capture.wait_for_state(event="warning_dismiss", timeout=6.0)
        capture.stop()
        assert dismiss is not None, "Limit warning overlay did not auto-dismiss"


class TestLongPressRestart:
    """7.2c: long-press Select restarts and resets lap numbering."""

    def test_restart_resets_lap_numbering(self, emulator):
        _skip_if_no_lap_feature(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        _enable_lap_setting(emulator)
        _wait_for_counting_stopwatch(emulator, capture)

        laps = _record_laps(emulator, capture, 2, delay=0.5)
        assert laps[1].get("name", "").startswith("Lap 2: ")
        time.sleep(5.5)  # let the flash window end

        # Long-press Select: restart from zero with the lap session reset
        capture.clear_state_queue()
        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state is not None, "No long_press_select event"
        assert_mode(state, "Counting")
        assert state.get("c") == "1"
        minutes, _, seconds = state.get("t", "9:99").partition(":")
        assert int(minutes) * 60 + int(seconds) <= 2, (
            f"Stopwatch did not restart from zero: {state}"
        )

        # The next lap is numbered 1 again; prior lap slots are untouched
        laps_after = _record_laps(emulator, capture, 1)
        capture.stop()
        assert laps_after[0].get("name", "").startswith("Lap 1: "), (
            f"Lap numbering was not reset: {laps_after[0]}"
        )
        # Slots: original + 2 old laps + 1 new lap = 4 -> MAX_TIMERS - 4 free
        assert int(laps_after[0].get("free", -1)) == MAX_TIMERS - 4, (
            f"Previously recorded lap slots were not preserved: {laps_after[0]}"
        )
