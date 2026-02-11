import time
import pytest
from conftest import (LogCapture, Button, assert_mode, assert_is_chrono,
                      parse_time)


class TestEditElapsedTime:
    """Test that time elapsed during edit modes is properly tracked."""

    def test_chrono_edit_elapsed_time_deducted(self, persistent_emulator):
        """
        Open app, wait 2s, enter EditSec, wait 2s, add 20s.
        The timer should become a countdown and display less than 16s
        (at least 4s of elapsed time should be deducted).

        Workflow:
        1. App opens in New mode (0:00, chrono)
        2. Wait for auto-transition to Counting (~3s)
        3. Wait 2 seconds (chrono at ~5s)
        4. Press Up to enter New mode (preserving timer)
        5. Long-press Select to enter EditSec
        6. Wait 2 seconds
        7. Press Up to add 20 seconds
        8. Wait for mode transition to Counting
        9. Assert timer is a countdown (not chrono) showing < 16 seconds
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)  # Wait for log capture to connect

        # Wait for auto-transition from New to Counting (~3s)
        state = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state is not None, "Failed to auto-transition to Counting"
        assert_mode(state, "Counting")

        # Wait 2 seconds with chrono running
        time.sleep(2.0)

        # Press Up to enter New mode (preserves chrono timer value)
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Failed to enter New mode"
        assert_mode(state, "New")

        # Long-press Select to enter EditSec
        emulator.hold_button(Button.SELECT)
        time.sleep(1.5)
        emulator.release_buttons()
        time.sleep(0.3)

        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state is not None, "Failed to enter EditSec mode"
        assert_mode(state, "EditSec")

        # Wait 2 seconds in EditSec
        time.sleep(2.0)

        # Press Up to add 20 seconds
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Failed to register Up button press"
        print(f"State after +20s: time={state['t']}, chrono={state['c']}, "
              f"direction={state['d']}, bl={state['bl']}, tl={state['tl']}")

        # Wait for mode transition to Counting
        state = capture.wait_for_state(event="mode_change", timeout=10.0)
        assert state is not None, "Failed to transition to Counting mode"
        assert_mode(state, "Counting")
        print(f"State at Counting: time={state['t']}, chrono={state['c']}, "
              f"direction={state['d']}, bl={state['bl']}, tl={state['tl']}")

        # The timer should now be a countdown (not chrono) since we
        # added 20s past the chrono value
        assert_is_chrono(state, False)

        # With at least ~7s elapsed (3s auto + 2s wait + 2s edit),
        # plus 3s mode transition, the countdown from 20s should show
        # well under 16 seconds.
        minutes, seconds = parse_time(state['t'])
        total_seconds = minutes * 60 + seconds
        assert total_seconds < 16, (
            f"Expected timer to show less than 16 seconds "
            f"(elapsed time during edit should be deducted), "
            f"but got {state['t']} ({total_seconds}s)"
        )

        capture.stop()
