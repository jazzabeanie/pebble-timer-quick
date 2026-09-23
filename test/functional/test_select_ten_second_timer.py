"""
Test Case: a 10-second timer set with Select counts down on time.

SUSPECTED BUG - WATCH CLOSELY. A user saw a 10 s timer count up to 12 s
before counting down, and another time "stumble" around 8 s. The cause is not
confirmed. This test follows the user's flow and checks the remaining time at
several points and the alarm time. A failure here may be a real app bug, so
investigate it (check the logged t= values and times) before treating it as
emulator flakiness. Do not add a flaky/rerun marker to this test.

Flow:
1. Start a timer (a fresh launch starts New mode with a running timer)
2. Let the edit expire, so it goes to Counting as a stopwatch (chrono)
3. Press Select to pause it
4. Hold Select to restart into EditSec, paused at 0:00
5. Press Select twice to add 10 seconds
6. Let the edit expire (a sub-minute timer stays paused)
7. Press Select to start the countdown
8. Sample the remaining time with Down presses (in Counting mode, Down only
   logs the state; it does not change the timer)
9. Check that the alarm starts 10 s after the start
"""

import logging
import time

import pytest

from .conftest import (
    Button,
    LogCapture,
    assert_mode,
    assert_paused,
    parse_time,
)

logger = logging.getLogger(__name__)

TIMER_SECONDS = 10
# The host sees each log line a little after the watch writes it, and t= is
# rounded down to whole seconds, so allow 1.5 s between expected and logged.
TOLERANCE_S = 1.5
SAMPLE_AT_S = (2.0, 5.0, 8.0)


def _seconds(state: dict) -> int:
    minutes, seconds = parse_time(state["t"])
    return minutes * 60 + seconds


def _wait(capture: LogCapture, event: str, what: str, timeout: float = 5.0) -> dict:
    state = capture.wait_for_state(event=event, timeout=timeout)
    if state is None:
        logger.error(f"All captured logs: {capture.get_all_logs()}")
    assert state is not None, f"No '{event}' state after: {what}"
    logger.info(f"{what}: {state}")
    return state


@pytest.mark.suspected_bug(
    "A 10 s timer was seen counting up to 12 s, and stumbling around 8 s")
class TestSelectTenSecondTimer:
    """A 10 s timer set with Select x2 counts down on time and rings at 10 s."""

    def test_ten_second_timer_counts_down_on_time(self, emulator):
        capture = LogCapture(emulator.platform)
        capture.start()
        try:
            self._run(emulator, capture)
        finally:
            capture.stop()

    def _run(self, emulator, capture):
        # 1-2. The fresh launch runs a New timer; its edit expires to a stopwatch
        state = _wait(capture, "mode_change", "edit expired to Counting", timeout=6.0)
        assert_mode(state, "Counting")
        assert state["c"] == "1", f"Expected a stopwatch (chrono), got: {state}"

        # 3. Pause the stopwatch
        emulator.press_select()
        state = _wait(capture, "button_select", "Select pauses the stopwatch")
        assert_paused(state, True)

        # 4. Hold Select: reset into EditSec, paused at 0:00
        emulator.hold_button(Button.SELECT)
        time.sleep(1.0)
        emulator.release_buttons()
        state = _wait(capture, "long_press_select", "hold Select resets into EditSec")
        assert_mode(state, "EditSec")
        assert state["t"] == "0:00", f"Expected 0:00 after reset, got: {state}"

        # 5. Select twice: +5 s each
        for expected in ("0:05", "0:10"):
            emulator.press_select()
            state = _wait(capture, "button_select", f"Select adds 5 s (expect {expected})")
            assert state["t"] == expected, f"Expected {expected}, got: {state}"

        # 6. The edit expires; a sub-minute timer stays paused at 0:10
        state = _wait(capture, "mode_change", "edit expired", timeout=6.0)
        assert_mode(state, "Counting")
        assert_paused(state, True)
        assert state["t"] == "0:10", f"Expected 0:10 before the start, got: {state}"

        # 7. Start the countdown
        emulator.press_select()
        state = _wait(capture, "button_select", "Select starts the countdown")
        start = time.time()
        assert_paused(state, False)
        assert state["c"] == "0", f"Expected a countdown, got: {state}"

        # 8. Sample the remaining time
        for at in SAMPLE_AT_S:
            delay = start + at - time.time()
            if delay > 0:
                time.sleep(delay)
            emulator.press_down()
            state = _wait(capture, "button_down", f"sample at ~{at:.0f} s")
            elapsed = time.time() - start
            expected = TIMER_SECONDS - elapsed
            shown = _seconds(state)
            logger.info(f"sample: {elapsed:.2f} s after start, expected ~{expected:.2f} s left, "
                        f"logged t={state['t']}")
            assert state["c"] == "0", f"Countdown turned into a stopwatch early: {state}"
            assert shown <= TIMER_SECONDS, f"Remaining time is above {TIMER_SECONDS} s: {state}"
            assert abs(shown - expected) <= TOLERANCE_S, (
                f"At {elapsed:.2f} s after the start, expected ~{expected:.2f} s left, "
                f"but the timer shows t={state['t']}")

        # 9. The alarm starts 10 s after the start
        state = _wait(capture, "alarm_start", "alarm", timeout=TIMER_SECONDS + 5.0)
        rang_after = time.time() - start
        logger.info(f"alarm started {rang_after:.2f} s after the start")
        assert state["v"] == "1", f"Alarm is not vibrating: {state}"
        assert abs(rang_after - TIMER_SECONDS) <= TOLERANCE_S, (
            f"Alarm started {rang_after:.2f} s after the start, expected ~{TIMER_SECONDS} s")
