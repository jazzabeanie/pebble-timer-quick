import time
import pytest
from .conftest import (LogCapture, Button, assert_mode, assert_is_chrono,
                      parse_time)


class TestEditElapsedTime:
    """Test that time elapsed during edit modes is properly tracked."""

    def test_chrono_edit_elapsed_time_deducted(self, persistent_emulator):
        """
        This test makes sure that any time spent setting the timer is included
        in the time elapsed. The timer should have been considered started the
        moment the app was opened in new timer mode.

        Workflow:
        1. App opens in New mode (0:00)
        2. Immediately long-press Select to enter EditSec (prevent auto-start)
        3. Wait 4 seconds
        4. Press Up to add 20 seconds
        5. Wait for mode transition to Counting
        6. Assert timer is a countdown showing < 16 seconds
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)  # Wait for log capture to connect

        # Immediately enter EditSec to prevent auto-transition to Counting
        emulator.hold_button(Button.SELECT)
        time.sleep(1.1)
        emulator.release_buttons()
        time.sleep(0.3)

        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state is not None, "Failed to enter EditSec mode"
        assert_mode(state, "EditSec")

        # Wait (simulating user thinking/fumbling)
        time.sleep(1.5)

        # Press Up to add 20 seconds
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state is not None, "Failed to register Up button press"

        # Check time
        minutes, seconds = parse_time(state['t'])
        total_seconds = minutes * 60 + seconds

        # We waited over 4s
        # If the timer counts from app start, it should be significantly less than 20s.
        # 16s is a safe upper bound if we expect >4s deducted.
        assert total_seconds < 16, (
            f"Expected timer to show less than 16 seconds "
            f"(elapsed time since app start should be deducted), "
            f"but got {state['t']} ({total_seconds}s)"
        )

        capture.stop()
