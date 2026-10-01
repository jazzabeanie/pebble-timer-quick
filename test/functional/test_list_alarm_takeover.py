"""
Functional tests: alarm takeover and held alarms (openspec: list-alarm-takeover).

A countdown that reaches zero while it is not on screen must still ring:

- In the Timer List, the alarm is HELD. The list stays open, the timer's row
  gets a bell icon, and the watch vibrates five short pulses once. The alarm
  takes over when the user leaves the list (Select on a timer, Back, the 30 s
  idle timeout, or hold Down on "New Timer").
- In the main window, another timer's alarm takes over at once, or it is held
  while the user is busy (an alarm or an edit screen) and takes over when the
  user is free.
- When the app is closed, one wakeup is scheduled for the next alarm of ANY
  timer.

Log markers used here (see src/timer_list.c and src/main.c):

- TEST_STATE:list_alarm_held,slot=<n>,row=<r>   the list marked a row
- TEST_STATE:vibe,src=list_alarm                 the five short pulses
- TEST_STATE:list_alarm_takeover,slot=<n>        a held alarm left the list
- TEST_STATE:timer_list_hide                     the list window closed
- TEST_STATE:alarm_held,slot=<n>                 held in the main window
- TEST_STATE:main_alarm_takeover,slot=<n>        takeover in the main window
- TEST_STATE:alarm_start                         the alarm screen vibrates

The input guard (400 ms after a takeover) is compiled out on aplite. Its
timing is covered by the unit tests in test/test_main_logic.c; these tests
press only after the guard window, except the aplite-only "no guard" test.
"""

import logging
import time

import pytest
from PIL import Image

from .conftest import (
    PROJECT_ROOT,
    Button,
    LogCapture,
    wait_past_input_guard,
)

logger = logging.getLogger(__name__)

# List geometry (src/timer_list.c): rows are ROW_HEIGHT tall; the bell icon is
# drawn ALARM_ICON_X from the left edge, centered vertically in its row.
ROW_HEIGHT = 46
ALARM_ICON_X = 4
BELL_IMAGE = PROJECT_ROOT / "resources" / "images" / "icon_list_alarm~bw.png"

# The list refreshes every 500 ms. The host clock and the emulator clock can
# drift apart under load, so the window around the expected end time is wide.
HELD_EARLY_S = 2.0
HELD_LATE_S = 5.0

IDLE_TIMEOUT_S = 30.0

ROUND_PLATFORMS = ("chalk", "gabbro")


####################################################################################################
# Log helper
#

class _Logs:
    """Raw-log view of a LogCapture.

    LogCapture.wait_for_state() drops every state it skips, so two events that
    arrive close together cannot both be checked with it. This helper searches
    the raw lines instead, from a position that the test sets with mark().
    """

    def __init__(self, platform):
        self.capture = LogCapture(platform)
        self.capture.start()
        self.pos = 0

    def lines(self, since=None):
        start = self.pos if since is None else since
        return self.capture.get_all_logs()[start:]

    def mark(self):
        """Search only the lines that arrive after this call. Returns the position."""
        self.pos = len(self.capture.get_all_logs())
        return self.pos

    def find(self, needle, since=None):
        for line in self.lines(since):
            if needle in line:
                return line
        return None

    def count(self, needle, since=None):
        return sum(1 for line in self.lines(since) if needle in line)

    def index(self, needle, since=0):
        """Position of the first line that contains needle, or -1."""
        for i, line in enumerate(self.capture.get_all_logs()[since:]):
            if needle in line:
                return since + i
        return -1

    def wait(self, needle, timeout=5.0, since=None):
        """Wait for a line that contains needle. Returns its state dict, or None."""
        deadline = time.time() + timeout
        while True:
            line = self.find(needle, since)
            if line is not None:
                state = self.capture._parse_state_line(line)
                return state if state is not None else {"event": needle}
            if time.time() >= deadline:
                return None
            time.sleep(0.05)

    def dump(self, since=0):
        return [line for line in self.lines(since) if "TEST_STATE" in line]

    def stop(self):
        self.capture.stop()


####################################################################################################
# Setup helpers
#

def _press_and_wait(emulator, logs, press, needle, what, timeout=5.0):
    """Press a button and wait for the log line it must produce."""
    since = len(logs.capture.get_all_logs())
    press()
    state = logs.wait(needle, timeout=timeout, since=since)
    assert state is not None, f"{what}: no '{needle}' in the logs: {logs.dump(since)}"
    return state


def _hold(emulator, button, seconds=1.0):
    time.sleep(0.3)  # settle, so the hold is not joined to the press before it
    emulator.hold_button(button)
    time.sleep(seconds)
    emulator.release_buttons()
    time.sleep(0.3)


def _wait_for_counting(logs, since):
    """Wait for the edit screen to expire to Counting (3 s after the last press)."""
    state = logs.wait("TEST_STATE:mode_change", timeout=8.0, since=since)
    assert state is not None, f"The edit did not expire to Counting: {logs.dump(since)}"
    return state


def _make_short_countdown(emulator, logs, seconds, since, start=True):
    """From New mode, make a countdown of `seconds` in the active slot.

    The time is set in EditSec after New mode has expired, so the result does
    not depend on how soon after the launch the first press arrives.

    The app must be in New mode (a fresh launch, or after Select on "New
    Timer"), and `since` must be a log position from before that mode started.
    Returns the host time at which the countdown started (None if not started).
    """
    # New expires to a running stopwatch; pause it, then hold Select to reset
    # it to 0:00 in EditSec
    _wait_for_counting(logs, since)
    _press_and_wait(emulator, logs, emulator.press_select, "TEST_STATE:button_select", "pause")
    since = len(logs.capture.get_all_logs())
    _hold(emulator, Button.SELECT)
    state = logs.wait("TEST_STATE:long_press_select", timeout=5.0, since=since)
    assert state is not None and state.get("m") == "EditSec", (
        f"Hold Select did not open EditSec: {logs.dump(since)}"
    )

    # EditSec: Back = +60 s, Up = +20 s, Select = +5 s, Down = +1 s
    minutes, rest = divmod(seconds, 60)
    ups, rest = divmod(rest, 20)
    selects, downs = divmod(rest, 5)
    since = len(logs.capture.get_all_logs())
    for _ in range(minutes):
        _press_and_wait(emulator, logs, emulator.press_back, "TEST_STATE:button_back", "+60 s")
    for _ in range(ups):
        _press_and_wait(emulator, logs, emulator.press_up, "TEST_STATE:button_up", "+20 s")
    for _ in range(selects):
        _press_and_wait(emulator, logs, emulator.press_select, "TEST_STATE:button_select", "+5 s")
    for _ in range(downs):
        _press_and_wait(emulator, logs, emulator.press_down, "TEST_STATE:button_down", "+1 s")

    # A timer set in EditSec stays paused when the edit expires
    state = _wait_for_counting(logs, since)
    assert int(state.get("tl", -1)) == seconds * 1000, f"Wrong timer length: {state}"
    if not start:
        return None
    state = _press_and_wait(emulator, logs, emulator.press_select,
                            "TEST_STATE:button_select", "start")
    assert state.get("p") == "0", f"The countdown did not start: {state}"
    return time.time()


def _exit_app(emulator):
    """Back in Counting mode (no alarm) exits the app and saves the timers."""
    emulator.press_back()
    time.sleep(1.0)


def _open_list(emulator, logs):
    """Open the app (user launch) and wait for the Timer List.

    Returns (show state, position of the timer_list_show line, host time of it).
    """
    since = len(logs.capture.get_all_logs())
    emulator.open_app_via_menu()
    show = logs.wait("TEST_STATE:timer_list_show", timeout=10.0, since=since)
    assert show is not None, f"The Timer List did not open: {logs.dump(since)}"
    shown_at = time.time()
    position = logs.index("TEST_STATE:timer_list_show", since)
    # timer_list_show is logged at the start of the window push animation; a
    # press sent before it settles is swallowed
    time.sleep(1.0)
    return show, position, shown_at


def _select_new_timer(emulator, logs):
    """Select "New Timer" (row 0) in the list. Returns the log position before it."""
    since = len(logs.capture.get_all_logs())
    emulator.press_select()
    assert logs.wait("TEST_STATE:timer_list_select_new", timeout=5.0, since=since) is not None, (
        f"Select on New Timer did not open New mode: {logs.dump(since)}"
    )
    return since


class _Scene:
    """A Timer List that is open with a short countdown about to end."""

    def __init__(self, logs, end_at, show, list_pos, shown_at):
        self.logs = logs
        self.end_at = end_at        # host time at which the short countdown ends
        self.show = show            # timer_list_show state
        self.list_pos = list_pos    # log position of timer_list_show
        self.shown_at = shown_at    # host time of timer_list_show
        self.rows = int(show.get("list_count", -1))


def _one_short_timer_in_list(emulator, seconds=20, start=True):
    """Slot 0 = a short countdown. Exit, then reopen so the Timer List shows.

    List rows: 0 = New Timer, 1 = the short countdown (slot 0).
    """
    logs = _Logs(emulator.platform)
    started = _make_short_countdown(emulator, logs, seconds, since=0, start=start)
    _exit_app(emulator)
    show, pos, shown_at = _open_list(emulator, logs)
    end_at = started + seconds if started is not None else None
    return _Scene(logs, end_at, show, pos, shown_at)


def _two_timers_saved(emulator, short_seconds=30):
    """Slot 0 = a 5 min countdown, slot 1 = a short countdown. The app is
    closed when this returns. Returns (logs, host time the short one ends)."""
    logs = _Logs(emulator.platform)
    _make_short_countdown(emulator, logs, 300, since=0)
    _exit_app(emulator)
    _open_list(emulator, logs)
    since = _select_new_timer(emulator, logs)
    started = _make_short_countdown(emulator, logs, short_seconds, since=since)
    _exit_app(emulator)
    return logs, started + short_seconds


def _two_timers_in_list(emulator, short_seconds=30):
    """The two timers of _two_timers_saved(), with the Timer List open.

    The list sorts countdowns soonest first, so the rows are: 0 = New Timer,
    1 = the short countdown (slot 1), 2 = the 5 min countdown (slot 0). The
    short timer's row number is NOT its slot number.
    """
    logs, end_at = _two_timers_saved(emulator, short_seconds)
    show, pos, shown_at = _open_list(emulator, logs)
    return _Scene(logs, end_at, show, pos, shown_at)


def _keep_list_open(emulator):
    """Restart the list's 30 s idle timeout. Up on the top row does nothing
    else (on another row it moves the selection up)."""
    emulator.press_up()


def _wait_in_list(emulator, logs, needle, until, since):
    """Wait for a log line while the Timer List stays open. A press every 10 s
    keeps the idle timeout from closing the list."""
    while True:
        state = logs.wait(needle, timeout=min(10.0, max(0.1, until - time.time())), since=since)
        if state is not None or time.time() >= until:
            return state
        _keep_list_open(emulator)


def _wait_for_held(emulator, scene, slot, row=None, keep_open=True):
    """Wait until the list marks `slot` as a held alarm, near its end time.

    With keep_open, presses keep the idle timeout away during the wait, and
    one more press after it gives the test a full 30 s with the list open.
    """
    logs = scene.logs
    needle = f"TEST_STATE:list_alarm_held,slot={slot},"
    until = max(time.time(), scene.end_at) + HELD_LATE_S
    if keep_open:
        held = _wait_in_list(emulator, logs, needle, until, scene.list_pos)
    else:
        held = logs.wait(needle, timeout=until - time.time(), since=scene.list_pos)
    since = scene.list_pos
    assert held is not None, (
        f"The list did not hold the alarm of slot {slot}. "
        f"alarm_start lines: {logs.count('TEST_STATE:alarm_start', since)}, "
        f"list_alarm_held lines: {logs.count('TEST_STATE:list_alarm_held', since)}, "
        f"timer_list_hide lines: {logs.count('TEST_STATE:timer_list_hide', since)}. "
        f"Logs: {logs.dump(since)}"
    )
    arrived = time.time()
    assert arrived >= scene.end_at - HELD_EARLY_S, (
        f"The alarm was held {scene.end_at - arrived:.1f} s before the countdown ended"
    )
    if row is not None:
        assert int(held.get("row", -1)) == row, f"The mark is on the wrong row: {held}"
    if keep_open:
        _keep_list_open(emulator)
    return held


def _assert_list_still_open(scene, vibes=1):
    """The held alarm did not close the list or start the alarm vibration."""
    logs = scene.logs
    since = scene.list_pos
    assert logs.count("TEST_STATE:vibe,src=list_alarm", since) == vibes, (
        f"Expected {vibes} five-pulse signal(s): {logs.dump(since)}"
    )
    assert logs.count("TEST_STATE:alarm_start", since) == 0, (
        f"The alarm vibration started behind the list: {logs.dump(since)}"
    )
    assert logs.count("TEST_STATE:timer_list_hide", since) == 0, (
        f"The list closed: {logs.dump(since)}"
    )
    assert logs.count("alarm_takeover", since) == 0, (
        f"An alarm took over while the list was open: {logs.dump(since)}"
    )


def _assert_alarm_on_screen(logs, since, length_ms=None):
    """The main window shows a vibrating alarm in Counting mode."""
    alarm = logs.wait("TEST_STATE:alarm_start", timeout=5.0, since=since)
    assert alarm is not None, f"The alarm did not start: {logs.dump(since)}"
    assert alarm.get("m") == "Counting", f"Wrong mode: {alarm}"
    assert alarm.get("v") == "1", f"The alarm does not vibrate: {alarm}"
    if length_ms is not None:
        assert int(alarm.get("tl", -1)) == length_ms, f"The wrong timer is on screen: {alarm}"
    return alarm


def _assert_down_snoozes(emulator, logs):
    """A Down after the guard window snoozes, so the alarm screen is on top."""
    wait_past_input_guard()
    since = len(logs.capture.get_all_logs())
    emulator.press_down()
    state = logs.wait("TEST_STATE:button_down", timeout=5.0, since=since)
    assert state is not None, f"Down did nothing: {logs.dump(since)}"
    assert logs.count("TEST_STATE:input_blocked", since) == 0, "Down was blocked by the guard"
    assert logs.count("TEST_STATE:alarm_stop", since) == 1, (
        f"The alarm was not vibrating before the Down: {logs.dump(since)}"
    )
    assert state.get("m") == "Counting", f"Wrong mode: {state}"
    assert state.get("v") == "0", f"Down did not snooze: {state}"
    assert state.get("c") == "0", f"The snoozed timer is not a countdown: {state}"
    return state


def _seconds(state):
    minutes, seconds = state.get("t", "0:00").split(":")
    return int(minutes) * 60 + int(seconds)


####################################################################################################
# Screenshot helper
#

def _alarm_icon_match(img, row, selected):
    """Share (0..1) of the pixels in the row's icon box that match the bell.

    On an unselected (light) row the bell is dark; on the selected (black) row
    it is light. A row with no icon has text in the box, which matches badly.
    """
    bell = Image.open(BELL_IMAGE).convert("RGBA")
    width, height = bell.size
    x0 = ALARM_ICON_X
    y0 = row * ROW_HEIGHT + (ROW_HEIGHT - height) // 2
    gray = img.convert("L")
    match = 0
    for y in range(height):
        for x in range(width):
            ink = bell.getpixel((x, y))[3] > 127
            dark = gray.getpixel((x0 + x, y0 + y)) < 128
            if dark == (ink != selected):
                match += 1
    return match / float(width * height)


def _assert_row_marked(emulator, name, row, selected=False, unmarked_row=None):
    """Screenshot the list and check the bell icon on `row`."""
    if emulator.platform in ROUND_PLATFORMS:
        return  # round displays center the rows; the pixel positions differ
    img = emulator.screenshot(name)
    match = _alarm_icon_match(img, row, selected)
    assert match >= 0.9, (
        f"[{emulator.platform}] No alarm icon on row {row} (match {match:.2f})"
    )
    if unmarked_row is not None:
        other = _alarm_icon_match(img, unmarked_row, False)
        assert other < 0.8, (
            f"[{emulator.platform}] Alarm icon on row {unmarked_row}, which has no alarm "
            f"(match {other:.2f})"
        )


####################################################################################################
# Timer List: hold, mark, signal
#

class TestListHoldsAlarm:
    """A countdown that ends while the Timer List is open is held and marked."""

    def test_slot0_alarm_is_held_then_back_takes_over(self, emulator):
        """
        1.5 and 1.6: the "vibrates unseen" case. Slot 0 is the timer that the
        main window under the list checks.

        1. Save one 20 s countdown, exit, reopen: the Timer List shows
        2. At its end: the row is marked, five pulses, no alarm vibration, the
           list stays open
        3. Back: the alarm screen opens, vibrating
        4. Down after the guard window snoozes
        5. Exit and reopen: the list has one more entry (Back kept the implicit
           stopwatch)
        """
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs

        _wait_for_held(emulator, scene, slot=0, row=1)
        time.sleep(1.0)
        _assert_list_still_open(scene)
        _assert_row_marked(emulator, "held_slot0", row=1)
        _assert_list_still_open(scene)

        since = logs.mark()
        emulator.press_back()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"Back did not open the held alarm: {logs.dump(since)}"
        )
        assert logs.wait("TEST_STATE:timer_list_hide", timeout=5.0) is not None, (
            f"The list did not close: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=20000)
        _assert_down_snoozes(emulator, logs)

        # Back kept the implicit new timer as a stopwatch
        _exit_app(emulator)
        show, _, _ = _open_list(emulator, logs)
        logs.stop()
        assert int(show.get("list_count", -1)) == scene.rows + 1, (
            f"Expected one more list entry after a Back takeover: {scene.show} -> {show}"
        )

    def test_slot1_alarm_is_held_then_select_other_timer_takes_over(self, emulator):
        """
        1.5a and 1.6: the "does not ring" case. The ending timer is slot 1, and
        its list row (1) is not its slot number... the list sorts soonest first.

        1. Slot 0 = 5 min, slot 1 = 30 s; reopen: the Timer List shows
        2. At the end of slot 1: row 1 is marked and row 2 is not
        3. Select the 5 min timer: the held alarm opens instead
        4. Down after the guard window snoozes
        5. Exit and reopen: no extra list entry (Select discarded the implicit
           stopwatch)
        """
        scene = _two_timers_in_list(emulator, short_seconds=30)
        logs = scene.logs

        _wait_for_held(emulator, scene, slot=1, row=1)
        time.sleep(1.0)
        _assert_list_still_open(scene)
        _assert_row_marked(emulator, "held_slot1", row=1, unmarked_row=2)

        # Move to the 5 min timer (row 2) and select it
        emulator.press_down()
        emulator.press_down()
        since = logs.mark()
        emulator.press_select()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=1", timeout=5.0) is not None, (
            f"Select did not open the held alarm: {logs.dump(since)}"
        )
        # The short timer is on screen, not the 5 min timer that was selected
        _assert_alarm_on_screen(logs, since, length_ms=30000)
        _assert_down_snoozes(emulator, logs)

        _exit_app(emulator)
        show, _, _ = _open_list(emulator, logs)
        logs.stop()
        assert int(show.get("list_count", -1)) == scene.rows, (
            f"Expected no extra list entry after a Select takeover: {scene.show} -> {show}"
        )

    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_delete_moves_held_timer_to_lower_slot(self, emulator):
        """
        1.5b: deleting the 5 min timer (slot 0) moves the short timer from
        slot 1 to slot 0. It is still watched: the list holds slot 0 at its end.
        """
        scene = _two_timers_in_list(emulator, short_seconds=30)
        logs = scene.logs

        emulator.press_down()
        emulator.press_down()  # row 2 = the 5 min timer
        since = len(logs.capture.get_all_logs())
        _hold(emulator, Button.DOWN)
        assert logs.wait("TEST_STATE:timer_list_delete", timeout=5.0, since=since) is not None, (
            "Hold Down did not delete the 5 min timer"
        )
        assert time.time() < scene.end_at, "The setup was too slow; the countdown already ended"

        _wait_for_held(emulator, scene, slot=0)
        assert logs.count("TEST_STATE:list_alarm_held,slot=1", scene.list_pos) == 0

        since = logs.mark()
        emulator.press_back()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"Back did not open the held alarm: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=30000)
        logs.stop()

    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_deleted_countdown_is_not_held(self, emulator):
        """1.5c: a watched countdown that the user deletes is never marked."""
        scene = _two_timers_in_list(emulator, short_seconds=30)
        logs = scene.logs

        emulator.press_down()  # row 1 = the short timer
        since = len(logs.capture.get_all_logs())
        _hold(emulator, Button.DOWN)
        assert logs.wait("TEST_STATE:timer_list_delete", timeout=5.0, since=since) is not None, (
            "Hold Down did not delete the short timer"
        )
        assert time.time() < scene.end_at, "The setup was too slow; the countdown already ended"

        time.sleep(max(0.0, scene.end_at - time.time()) + 3.0)
        logs.stop()
        since = scene.list_pos
        assert logs.count("TEST_STATE:list_alarm_held", since) == 0, logs.dump(since)
        assert logs.count("TEST_STATE:vibe,src=list_alarm", since) == 0, logs.dump(since)

    def test_overdue_countdown_at_open_is_not_held(self, emulator):
        """
        1.5d: a countdown whose alarm the user silenced before the app closed
        is overdue at the next open. It is not held, and Back exits as before.
        """
        logs = _Logs(emulator.platform)
        _make_short_countdown(emulator, logs, 10, since=0)
        assert logs.wait("TEST_STATE:alarm_start", timeout=20.0, since=0) is not None, (
            "The 10 s timer did not alarm"
        )
        wait_past_input_guard()
        state = _press_and_wait(emulator, logs, emulator.press_back,
                                "TEST_STATE:button_back", "silence")
        assert state.get("v") == "0", f"Back did not silence the alarm: {state}"
        _exit_app(emulator)

        show, pos, _ = _open_list(emulator, logs)
        time.sleep(3.0)
        assert logs.count("TEST_STATE:list_alarm_held", pos) == 0, logs.dump(pos)
        assert logs.count("TEST_STATE:vibe,src=list_alarm", pos) == 0, logs.dump(pos)

        since = logs.mark()
        emulator.press_back()
        time.sleep(2.0)
        logs.stop()
        assert logs.count("alarm_takeover", since) == 0, logs.dump(since)
        assert logs.count("TEST_STATE:alarm_start", since) == 0, logs.dump(since)

    def test_paused_countdown_is_not_held(self, emulator):
        """1.5d: a paused countdown is never marked."""
        scene = _one_short_timer_in_list(emulator, seconds=20, start=False)
        logs = scene.logs
        time.sleep(3.0)
        assert logs.count("TEST_STATE:list_alarm_held", scene.list_pos) == 0
        assert logs.count("TEST_STATE:vibe,src=list_alarm", scene.list_pos) == 0

        since = logs.mark()
        emulator.press_back()
        time.sleep(2.0)
        logs.stop()
        assert logs.count("alarm_takeover", since) == 0, logs.dump(since)
        assert logs.count("TEST_STATE:alarm_start", since) == 0, logs.dump(since)

    def test_open_just_before_the_end_shows_the_list(self, emulator):
        """
        1.5k (D13): the user opens the app a few seconds before a countdown
        ends. The list shows as usual, and the alarm is held in it.
        """
        logs, end_at = _two_timers_saved(emulator, short_seconds=30)
        # Reopen about 3 s before the end (the open and its settle take ~3 s)
        time.sleep(max(0.0, end_at - time.time() - 6.0))
        show, pos, shown_at = _open_list(emulator, logs)
        scene = _Scene(logs, end_at, show, pos, shown_at)
        assert logs.count("TEST_STATE:list_alarm_held", pos) == 0 or time.time() >= end_at - 1.0, (
            "The alarm was held before the countdown ended"
        )

        _wait_for_held(emulator, scene, slot=1, row=1)
        time.sleep(1.0)
        logs.stop()
        _assert_list_still_open(scene)


####################################################################################################
# Timer List: how a held alarm takes over
#

class TestListTakeover:
    """Each way to leave the list while an alarm is held."""

    def test_idle_timeout_takes_over(self, emulator):
        """
        1.5d2: with no press, the held alarm takes over when the list's 30 s
        idle timeout ends. The app does not go to the background.
        """
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1, keep_open=False)

        timeout = max(0.0, scene.shown_at + IDLE_TIMEOUT_S - time.time()) + 8.0
        takeover = logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=timeout,
                             since=scene.list_pos)
        idle_for = time.time() - scene.shown_at
        assert takeover is not None, (
            f"The held alarm did not take over at the idle timeout: {logs.dump(scene.list_pos)}"
        )
        assert idle_for >= IDLE_TIMEOUT_S - 4.0, (
            f"The takeover came {idle_for:.1f} s after the list opened; expected ~30 s"
        )
        _assert_alarm_on_screen(logs, scene.list_pos, length_ms=20000)
        logs.stop()
        assert logs.count("TEST_STATE:timer_list_idle_background", scene.list_pos) == 0, (
            "The app went to the background with an alarm held"
        )

    def test_select_new_timer_keeps_alarm_held_until_edit_ends(self, emulator):
        """
        1.5d3: Select on "New Timer" opens New mode as before. The alarm stays
        held in New and EditSec, and takes over when the edit expires.
        """
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1)

        since = logs.mark()
        emulator.press_select()  # row 0 = New Timer
        assert logs.wait("TEST_STATE:timer_list_select_new", timeout=5.0) is not None, (
            f"Select on New Timer did not open New mode: {logs.dump(since)}"
        )
        state = _press_and_wait(emulator, logs, emulator.press_select,
                                "TEST_STATE:button_select", "+5 min")
        assert state.get("m") == "New", f"Not in New mode: {state}"
        assert logs.count("TEST_STATE:vibe,src=list_new", since) == 1, logs.dump(since)

        hold_pos = len(logs.capture.get_all_logs())
        _hold(emulator, Button.SELECT)
        state = logs.wait("TEST_STATE:long_press_select", timeout=5.0, since=hold_pos)
        assert state is not None and state.get("m") == "EditSec", (
            f"Hold Select did not open EditSec: {logs.dump(hold_pos)}"
        )
        assert logs.count("alarm_takeover", since) == 0, (
            f"The held alarm took over an edit screen: {logs.dump(since)}"
        )

        # The edit expires 3 s after the last press: the held alarm takes over
        takeover = logs.wait("TEST_STATE:main_alarm_takeover,slot=0", timeout=8.0, since=since)
        assert takeover is not None, (
            f"The held alarm did not take over when the edit ended: {logs.dump(since)}"
        )
        expired = logs.index("TEST_STATE:mode_change", hold_pos)
        assert 0 <= expired < logs.index("TEST_STATE:main_alarm_takeover", since), (
            f"The takeover came before the edit expired: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=20000)
        logs.stop()
        assert logs.count("TEST_STATE:list_alarm_takeover", since) == 0

    def test_select_held_row_takes_over(self, emulator):
        """1.5d4: Select on the held timer's row opens that timer's alarm."""
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1)

        emulator.press_down()  # row 1 = the held timer
        since = logs.mark()
        emulator.press_select()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"Select on the held row did not open its alarm: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=20000)
        logs.stop()

    def test_two_held_alarms_open_in_order(self, emulator):
        """
        1.5d4: with two held alarms, Back opens the one that ended first. When
        the user silences it, the second one takes over in the main window.
        """
        logs = _Logs(emulator.platform)
        # Slot 0: 1 min. Slot 1: 20 s, started about 15 s later, so it ends first.
        long_end_at = _make_short_countdown(emulator, logs, 60, since=0) + 60.0
        _exit_app(emulator)
        _open_list(emulator, logs)
        since = _select_new_timer(emulator, logs)
        started = _make_short_countdown(emulator, logs, 20, since=since)
        _exit_app(emulator)
        assert started + 20 < long_end_at - 5.0, "The setup was too slow for this test"

        show, pos, shown_at = _open_list(emulator, logs)
        scene = _Scene(logs, started + 20, show, pos, shown_at)
        _wait_for_held(emulator, scene, slot=1)
        until = max(time.time(), long_end_at) + HELD_LATE_S
        assert _wait_in_list(emulator, logs, "TEST_STATE:list_alarm_held,slot=0,", until, pos), (
            f"The list did not hold the second alarm: {logs.dump(pos)}"
        )
        _keep_list_open(emulator)
        time.sleep(0.5)
        _assert_list_still_open(scene, vibes=2)

        since = logs.mark()
        emulator.press_back()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=1", timeout=5.0) is not None, (
            f"Back did not open the alarm that ended first: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=20000)

        # Silence it after the guard window: the second held alarm takes over
        wait_past_input_guard()
        since = logs.mark()
        emulator.press_select()
        assert logs.wait("TEST_STATE:main_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"The second held alarm did not take over: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=60000)
        logs.stop()

    def test_hold_down_on_new_timer_takes_over(self, emulator):
        """
        1.5p (D4, D6): hold Down on "New Timer" discards the implicit timer and
        shows the held alarm; the app does not exit. The release of that Down
        does not delete or snooze the timer that took over (on aplite too,
        which has no input guard).
        """
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1)

        since = logs.mark()
        emulator.hold_button(Button.DOWN)  # row 0 = New Timer
        takeover = logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0)
        emulator.release_buttons()
        assert takeover is not None, (
            f"Hold Down on New Timer did not open the held alarm: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=20000)

        # The release changes nothing
        time.sleep(1.5)
        for event in ("long_press_down", "button_down", "alarm_stop"):
            assert logs.count(f"TEST_STATE:{event}", since) == 0, (
                f"The Down release acted on the alarm ({event}): {logs.dump(since)}"
            )
        # The app is open and the alarm still vibrates: a new Down snoozes it
        _assert_down_snoozes(emulator, logs)
        logs.stop()

    def test_no_guard_on_aplite_after_takeover(self, emulator):
        """
        1.5z (D6): aplite has no input guard. A Down pressed at once after the
        takeover snoozes the alarm.
        """
        if emulator.platform != "aplite":
            pytest.skip("Only aplite has no input guard")
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1)

        since = logs.mark()
        emulator.press_back()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"Back did not open the held alarm: {logs.dump(since)}"
        )
        emulator.press_down()
        state = logs.wait("TEST_STATE:button_down", timeout=5.0)
        logs.stop()
        assert state is not None, f"Down did nothing: {logs.dump(since)}"
        assert state.get("v") == "0", f"Down did not snooze on aplite: {state}"
        assert logs.count("TEST_STATE:input_blocked", since) == 0


####################################################################################################
# Timer List: actions that do not take over
#

class TestListDeleteWithHeldAlarm:
    """Hold Down and "Delete all" while an alarm is held."""

    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_hold_down_on_held_row_deletes_it(self, emulator):
        """
        1.5u: hold Down on the held timer's row deletes that timer and its
        alarm. The list stays open, and Back then exits as before.
        """
        scene = _two_timers_in_list(emulator, short_seconds=30)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=1, row=1)

        emulator.press_down()  # row 1 = the held timer
        since = logs.mark()
        _hold(emulator, Button.DOWN)
        assert logs.wait("TEST_STATE:timer_list_delete", timeout=5.0) is not None, (
            f"Hold Down did not delete the held timer: {logs.dump(since)}"
        )
        time.sleep(2.0)
        _assert_list_still_open(scene)

        since = logs.mark()
        emulator.press_back()
        time.sleep(2.0)
        logs.stop()
        assert logs.count("alarm_takeover", since) == 0, logs.dump(since)
        assert logs.count("TEST_STATE:alarm_start", since) == 0, logs.dump(since)

    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_hold_down_on_other_row_keeps_alarm_held(self, emulator):
        """
        1.5v: hold Down on another timer's row deletes that timer. The list
        stays open, the held row is still marked, and Back then takes over.
        """
        scene = _two_timers_in_list(emulator, short_seconds=30)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=1, row=1)

        emulator.press_down()
        emulator.press_down()  # row 2 = the 5 min timer
        since = logs.mark()
        _hold(emulator, Button.DOWN)
        assert logs.wait("TEST_STATE:timer_list_delete", timeout=5.0) is not None, (
            f"Hold Down did not delete the 5 min timer: {logs.dump(since)}"
        )
        time.sleep(1.0)
        _assert_list_still_open(scene)
        # The selection moved to the previous timer: the held row, now selected
        _assert_row_marked(emulator, "held_after_delete", row=1, selected=True)

        # The held timer moved from slot 1 to slot 0
        since = logs.mark()
        emulator.press_back()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"Back did not open the held alarm: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=30000)
        logs.stop()

    def test_select_delete_all_keeps_alarm_held(self, emulator):
        """
        1.5w: Select on "Delete all" shows the hint and deletes nothing. The
        list stays open, the row stays marked, and Back then takes over.
        """
        if emulator.platform == "aplite":
            pytest.skip("The Delete all row is compiled out on aplite (RAM)")
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1)

        emulator.press_down()
        emulator.press_down()  # row 2 = Delete all
        since = logs.mark()
        emulator.press_select()
        assert logs.wait("TEST_STATE:timer_list_delete_all_hint", timeout=5.0) is not None, (
            f"Select on Delete all did not show the hint: {logs.dump(since)}"
        )
        time.sleep(3.5)  # the hint hides after 3 s
        _assert_list_still_open(scene)
        _assert_row_marked(emulator, "held_after_hint", row=1)

        since = logs.mark()
        emulator.press_back()
        assert logs.wait("TEST_STATE:list_alarm_takeover,slot=0", timeout=5.0) is not None, (
            f"Back did not open the held alarm: {logs.dump(since)}"
        )
        _assert_alarm_on_screen(logs, since, length_ms=20000)
        logs.stop()

    @pytest.mark.flaky(reruns=2, reruns_delay=5)
    def test_hold_down_on_delete_all_exits_without_wakeup(self, emulator):
        """
        1.5w: hold Down on "Delete all" deletes every timer, also the held
        one, and exits. No alarm is left, so the app does not wake up.
        """
        if emulator.platform == "aplite":
            pytest.skip("The Delete all row is compiled out on aplite (RAM)")
        scene = _one_short_timer_in_list(emulator, seconds=20)
        logs = scene.logs
        _wait_for_held(emulator, scene, slot=0, row=1)

        emulator.press_down()
        emulator.press_down()  # row 2 = Delete all
        since = logs.mark()
        _hold(emulator, Button.DOWN)
        assert logs.wait("TEST_STATE:timer_list_delete_all", timeout=5.0) is not None, (
            f"Hold Down on Delete all did not clear the timers: {logs.dump(since)}"
        )

        time.sleep(20.0)
        logs.stop()
        for event in ("wakeup_launch", "init", "alarm_start", "alarm_takeover"):
            assert logs.count(event, since) == 0, (
                f"The app came back after Delete all ({event}): {logs.dump(since)}"
            )


####################################################################################################
# Main window
#

class TestMainWindowTakeover:
    """Another timer ends while the main window is open."""

    def test_second_alarm_is_held_behind_the_first(self, emulator):
        """
        1.5e: two countdowns end about 15 s apart. The first rings and is not
        silenced; the second is held. Select silences the first, and the second
        takes over at once, vibrating, with its real overtime on screen.
        """
        logs = _Logs(emulator.platform)
        # Slot 0: 1 min
        long_end_at = _make_short_countdown(emulator, logs, 60, since=0) + 60.0
        _exit_app(emulator)
        _open_list(emulator, logs)
        since = _select_new_timer(emulator, logs)
        # Slot 1: 25 s, on screen. It rings first.
        started = _make_short_countdown(emulator, logs, 25, since=since)
        assert started + 25 < long_end_at - 5.0, "The setup was too slow for this test"
        main_pos = len(logs.capture.get_all_logs())

        first = logs.wait("TEST_STATE:alarm_start", timeout=35.0, since=main_pos)
        assert first is not None, f"The first alarm did not start: {logs.dump(main_pos)}"
        assert int(first.get("tl", -1)) == 25000, f"The wrong timer rang first: {first}"

        # The second countdown ends behind the first alarm: it is held
        timeout = max(0.0, long_end_at - time.time()) + HELD_LATE_S
        held = logs.wait("TEST_STATE:alarm_held,slot=0", timeout=timeout, since=main_pos)
        held_at = time.time()
        assert held is not None, (
            f"The second alarm was not held. "
            f"alarm_start lines: {logs.count('TEST_STATE:alarm_start', main_pos)}. "
            f"Logs: {logs.dump(main_pos)}"
        )
        time.sleep(1.0)
        assert logs.count("alarm_takeover", main_pos) == 0, (
            f"The second alarm took over while the first was ringing: {logs.dump(main_pos)}"
        )
        assert logs.count("TEST_STATE:alarm_held,slot=0", main_pos) == 1

        # Silence the first: the held alarm takes over at once
        since = logs.mark()
        emulator.press_select()
        takeover = logs.wait("TEST_STATE:main_alarm_takeover,slot=0", timeout=3.0)
        assert takeover is not None, (
            f"The held alarm did not take over when the first was silenced: {logs.dump(since)}"
        )
        alarm = _assert_alarm_on_screen(logs, since, length_ms=60000)
        overtime = time.time() - held_at
        logs.stop()
        assert abs(_seconds(alarm) - overtime) <= 3.0, (
            f"The alarm screen shows {alarm.get('t')}, expected about {overtime:.0f} s"
        )


####################################################################################################
# App closed
#

class TestWakeupForAnyTimer:
    """On exit, the app schedules a wakeup for the next alarm of any timer."""

    def test_non_active_countdown_wakes_the_app(self, emulator):
        """
        1.5y (D12): the timer on screen ends in 2 min and a countdown in
        another slot ends in about 15 s. Exit with Back. The app wakes up at
        the other countdown's end and shows its alarm.
        """
        logs = _Logs(emulator.platform)
        # Slot 0: 30 s
        started = _make_short_countdown(emulator, logs, 30, since=0)
        end_at = started + 30
        _exit_app(emulator)
        # Slot 1: 2 min, on screen when the app exits
        _open_list(emulator, logs)
        since = _select_new_timer(emulator, logs)
        emulator.press_down()
        _press_and_wait(emulator, logs, emulator.press_down, "TEST_STATE:button_down", "+1 min")
        _wait_for_counting(logs, since)
        assert time.time() < end_at - 3.0, "The setup was too slow; the 30 s countdown ended"
        exit_pos = logs.mark()
        _exit_app(emulator)

        # Only a wakeup can launch the app now
        timeout = max(0.0, end_at - time.time()) + 10.0
        init = logs.wait("TEST_STATE:init", timeout=timeout)
        woke_at = time.time()
        assert init is not None, (
            f"The app did not wake up for the non-active countdown: {logs.dump(exit_pos)}"
        )
        assert woke_at >= end_at - 3.0, (
            f"The app woke up {end_at - woke_at:.1f} s before the countdown ended"
        )
        assert int(init.get("tl", -1)) == 30000, f"The wrong timer is on screen: {init}"
        if emulator.platform != "aplite":
            # The wakeup_launch marker is part of the input guard code
            assert logs.count("TEST_STATE:wakeup_launch", exit_pos) == 1, logs.dump(exit_pos)
        alarm = _assert_alarm_on_screen(logs, exit_pos, length_ms=30000)
        logs.stop()
        assert alarm.get("v") == "1"
