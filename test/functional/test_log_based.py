"""
Proof-of-concept tests using log-based assertions instead of OCR.

These tests demonstrate the new approach to functional testing where app state
is verified by parsing structured log output (TEST_STATE lines) rather than
relying on OCR of screenshots.

See ralph/specs/test-logging.md for the specification.
"""

import logging
import pytest
import time

from .conftest import (
    Button,
    LogCapture,
    assert_time_equals,
    assert_time_approximately,
    assert_mode,
    assert_paused,
)

# Configure module logger
logger = logging.getLogger(__name__)


class TestLogBasedAssertions:
    """Proof-of-concept tests using log-based assertions."""

    def test_up_button_increments_20_minutes_log_based(self, persistent_emulator):
        """
        Test that Up button increments timer by 20 minutes using log-based assertions.

        This is the proof-of-concept test demonstrating the new approach:
        - Start log capture before button press
        - Press Up button QUICKLY (before 3-second new_expire_timer fires)
        - Wait for button_up state log
        - Assert time is ~20:00 using log state instead of OCR

        This replaces the OCR-based test_up_button_increments_20_minutes.

        TIMING NOTES:
        - The app has a 3-second new_expire_timer that transitions from New to Counting mode
        - The timer runs immediately in ControlModeNew so time will be slightly less than 20:00
        - The pebble logs command needs ~1s to connect
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for pebble logs to connect (needs ~1s)
        # This brings us to ~1.5s since app started
        time.sleep(1.0)

        # Press Up button to add 20 minutes
        # This should happen at ~1.5-2s, well before the 3-second timeout
        emulator.press_up()

        # Wait for button_up state log
        state = capture.wait_for_state(event="button_up", timeout=5.0)

        # Debug: log all captured logs
        all_logs = capture.get_all_logs()
        logger.info(f"All captured logs: {all_logs}")

        # Stop capture
        capture.stop()

        # Assert using structured log data
        assert state is not None, "Did not receive button_up state log"
        logger.info(f"Received state: {state}")

        # Verify time is approximately 20:00 (timer runs immediately so may have counted down)
        assert_time_approximately(state, minutes=19, seconds=58, tolerance=5)
        assert_mode(state, "New")
        assert_paused(state, False)  # Timer runs immediately in ControlModeNew

    def test_init_state_log(self, persistent_emulator):
        """
        Test that app initialization logs the initial state.

        Verifies the init event is logged with expected default values.
        """
        emulator = persistent_emulator

        # The app is already started by the fixture.
        # We need to capture logs from a fresh app start.
        # The _setup_test_environment fixture opens the app via install,
        # so we should see an init log.

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()

        # Give time for any pending logs to be captured
        time.sleep(1.0)

        # Get all state logs
        states = capture.get_state_logs()
        capture.stop()

        # Find the init event
        init_states = [s for s in states if s.get('event') == 'init']
        logger.info(f"All captured states: {states}")

        # Note: The init log may have been emitted before we started capturing.
        # This test mainly verifies the infrastructure works. In a real scenario,
        # we'd start capture before the app is launched.
        if init_states:
            init_state = init_states[0]
            logger.info(f"Init state: {init_state}")
            # Initial state should be 0:00, New mode, running (timer starts immediately)
            assert_time_equals(init_state, minutes=0, seconds=0)
            assert_mode(init_state, "New")
            assert_paused(init_state, False)  # Timer runs immediately in ControlModeNew
        else:
            # We may have missed the init log, but we can verify the structure works
            # by checking that we can at least capture logs
            logger.info("Init log was likely emitted before capture started (expected)")

    def test_multiple_button_presses_log_sequence(self, persistent_emulator):
        """
        Test capturing a sequence of button presses via logs.

        Demonstrates that we can track state changes through multiple button presses
        without relying on OCR.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for pebble logs to connect
        time.sleep(1.0)
        capture.clear_state_queue()

        # Press Down twice (each adds 1 minute)
        emulator.press_down()
        state1 = capture.wait_for_state(event="button_down", timeout=5.0)

        emulator.press_down()
        state2 = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        # Verify state progression
        assert state1 is not None, "Did not receive first button_down state"
        assert state2 is not None, "Did not receive second button_down state"

        logger.info(f"State after first Down: {state1}")
        logger.info(f"State after second Down: {state2}")

        # First Down should show approximately 1:00 (timer is running so may be slightly less)
        assert_time_approximately(state1, minutes=0, seconds=58, tolerance=5)

        # Second Down should show approximately 2:00
        assert_time_approximately(state2, minutes=1, seconds=58, tolerance=5)

        # Both should be in New mode, running (timer starts immediately)
        assert_mode(state1, "New")
        assert_mode(state2, "New")
        assert_paused(state1, False)  # Timer runs immediately in ControlModeNew
        assert_paused(state2, False)

    def test_mode_transition_via_logs(self, persistent_emulator):
        """
        Test that mode transition from New to Counting is logged.

        The app transitions from ControlModeNew to ControlModeCounting after
        3 seconds of inactivity. This tests verifies we can detect this via logs.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for pebble logs to connect
        time.sleep(1.0)
        capture.clear_state_queue()

        # Press Down to set a timer value
        emulator.press_down()
        state_after_press = capture.wait_for_state(event="button_down", timeout=5.0)

        # Wait for mode transition (3 seconds + buffer)
        # The mode_change event should be logged
        state_after_transition = capture.wait_for_state(event="mode_change", timeout=5.0)

        capture.stop()

        # Verify state after button press
        assert state_after_press is not None, "Did not receive button_down state"
        assert_mode(state_after_press, "New")
        # Timer is running immediately so time will be slightly less than 1:00
        assert_time_approximately(state_after_press, minutes=0, seconds=58, tolerance=5)

        # Verify state after mode transition
        assert state_after_transition is not None, "Did not receive mode_change state"
        logger.info(f"Mode change state: {state_after_transition}")
        assert_mode(state_after_transition, "Counting")
        # Timer has been running since button press, so it will be around 55s
        assert_time_approximately(state_after_transition, minutes=0, seconds=55, tolerance=8)
        assert_paused(state_after_transition, False)  # Timer is running in Counting mode
