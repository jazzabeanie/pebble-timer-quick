"""
Test Cases: Wakeup input guard.

When an alarm (wakeup event) launches the app, presses that start within
WAKEUP_INPUT_GUARD_MS (300 ms) of launch are ignored. The emulator cannot press
reliably inside a 300 ms window, so the timing itself is covered by the unit
tests in test/test_main_logic.c. This test drives a real wakeup launch and
checks that the launch is detected and that a press after the window acts.

The guard is compiled out on aplite (24KB app region), so this test is
skipped there.
"""

import logging
import time

import pytest

from .conftest import (
    LogCapture,
    assert_mode,
    assert_time_approximately,
    assert_vibrating,
)
from .test_timer_workflows import setup_short_timer

logger = logging.getLogger(__name__)

# Countdown long enough to exit the app before it elapses
WAKEUP_TIMER_SECONDS = 10


class TestWakeupInputGuard:
    """An alarm launch is guarded, and a press after the guard window acts."""

    def test_press_after_guard_window_snoozes(self, emulator):
        """
        Steps:
        1. Start a short countdown and exit the app with Back
        2. Wait for the alarm to relaunch the app (wakeup_launch)
        3. Wait past the 300 ms guard window, then press Down
        4. Verify that the alarm is snoozed (~5:00 counting down)
        """
        if emulator.platform == "aplite":
            pytest.skip("Wakeup input guard is compiled out on aplite (RAM)")
        capture = LogCapture(emulator.platform)
        capture.start()

        setup_short_timer(emulator, seconds=WAKEUP_TIMER_SECONDS)
        capture.clear_state_queue()

        # Exit while counting: Back quits and schedules the wakeup
        emulator.press_back()

        launch = capture.wait_for_state(event="wakeup_launch",
                                        timeout=WAKEUP_TIMER_SECONDS + 15.0)
        if launch is None:
            logger.error(f"All captured logs: {capture.get_all_logs()}")
        assert launch is not None, "App was not relaunched by the alarm wakeup"

        # The wakeup time is rounded down to whole seconds, so the app can open
        # up to 1s before the countdown elapses and the alarm starts.
        alarm = capture.wait_for_state(event="alarm_start", timeout=5.0)
        assert alarm is not None, "Alarm did not start after the wakeup launch"
        assert_vibrating(alarm, True)

        # Well past the guard window (launch log latency included)
        time.sleep(1.0)
        emulator.press_down()

        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_snooze = capture.wait_for_state(event="button_down", timeout=5.0)
        blocked = [line for line in capture.get_all_logs() if "TEST_STATE:input_blocked" in line]
        capture.stop()

        assert not blocked, f"Press after the guard window was blocked: {blocked}"
        assert state_stop is not None, "Alarm did not stop"
        assert state_snooze is not None, "Did not receive button_down state"
        assert_time_approximately(state_snooze, minutes=5, seconds=0, tolerance=5)
        assert_mode(state_snooze, "Counting")
        assert_vibrating(state_snooze, False)
