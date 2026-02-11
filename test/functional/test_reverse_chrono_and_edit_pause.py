"""
Test Cases: Reverse direction chrono and edit-pause behavior.

Test 1 - Reverse Direction Chrono from New Timer:
When the app opens fresh (ControlModeNew at 0:00), the user holds Up to switch
to reverse direction, then presses Up to add 20 minutes. With reverse direction,
this should create a chrono timer showing ~20:05 (as if 20 minutes have already
elapsed). After waiting another second, the chrono should continue counting up
to ~20:06.

Test 2 - Paused Timer Stays Paused After Edit:
When a user creates a 5-minute timer, lets edit mode expire (timer auto-starts),
pauses the timer, enters edit mode to add 5 more minutes, and lets edit mode
expire again, the timer should remain paused. The user explicitly paused before
editing, so the edit expiry should not auto-start the timer.
"""

import logging
import time

import pytest

from .conftest import (
    Button,
    PLATFORMS,
    LogCapture,
    assert_mode,
    assert_paused,
    assert_time_approximately,
    assert_direction,
    assert_is_chrono,
    assert_vibrating,
)

# Configure module logger
logger = logging.getLogger(__name__)


class TestReverseChrono:
    """Test: Adding time in reverse direction from a new timer creates a chrono."""

    def test_reverse_direction_creates_chrono(self, persistent_emulator):
        """
        Verify that opening the app, switching to reverse direction, and pressing
        Up to add 20 minutes creates a chrono timer at ~20:05 that continues
        counting up.

        Steps:
        1. App opens fresh in ControlModeNew at 0:00
        2. Hold Up to toggle reverse direction
        3. Press Up to add 20 minutes (in reverse = subtract from length)
        4. Wait for edit mode to expire (3.5s)
        5. Verify timer is chrono at ~20:08, mode is Counting
        6. Wait ~1.5s more
        7. Press Select to pause and capture state
        8. Verify time increased (chrono counting up) and is_chrono=true
        """
        emulator = persistent_emulator

        # Start log capture - wait for log stream to connect
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(2.0)
        capture.clear_state_queue()

        # Step 2: Hold Up to toggle reverse direction
        logger.info("Holding Up to toggle reverse direction...")
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        state_dir = capture.wait_for_state(event="long_press_up", timeout=5.0)
        if state_dir is None:
            logger.error(f"All captured logs: {capture.get_all_logs()}")
        assert state_dir is not None, "Did not receive long_press_up event"
        assert_direction(state_dir, forward=False)
        logger.info(f"Direction toggled to reverse: {state_dir}")

        # Step 3: Press Up to add 20 minutes (reverse direction → subtracts from length)
        emulator.press_up()
        state_add = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_add is not None, "Did not receive button_up event"
        logger.info(f"After adding 20 min in reverse: {state_add}")

        # Should show ~20:02 (20 min + ~2s elapsed) and be chrono
        assert_time_approximately(state_add, minutes=20, seconds=2, tolerance=5)
        assert_is_chrono(state_add, is_chrono=True)
        assert_mode(state_add, "New")

        # Step 4: Wait for edit mode to expire
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)

        # Step 5: Verify mode transition to Counting
        state_expire = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_expire is not None, "Did not receive mode_change after edit expired"
        logger.info(f"After edit expired: {state_expire}")

        assert_mode(state_expire, "Counting")
        assert_is_chrono(state_expire, is_chrono=True)
        assert_paused(state_expire, False)  # Timer should be running
        assert_vibrating(state_expire, False)  # Should NOT be vibrating
        # Time should be ~20:06 (20 min + ~6s elapsed since app start)
        assert_time_approximately(state_expire, minutes=20, seconds=6, tolerance=5)

        # Step 6-7: Wait and pause to verify chrono is counting up
        time.sleep(1.5)
        emulator.press_select()
        state_pause = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_pause is not None, "Did not receive button_select event"
        logger.info(f"After pause: {state_pause}")

        capture.stop()

        # Step 8: Verify chrono continued counting up
        assert_is_chrono(state_pause, is_chrono=True)
        assert_paused(state_pause, True)
        # Time should be ~20:08 (~1.5s more than at mode_change)
        assert_time_approximately(state_pause, minutes=20, seconds=8, tolerance=5)


class TestPausedTimerStaysPausedAfterEdit:
    """Test: A paused timer should remain paused after editing and letting edit mode expire."""

    def test_paused_timer_stays_paused_after_edit_expires(self, persistent_emulator):
        """
        Verify that when a user pauses a running countdown, enters edit mode
        to add more time, and lets edit mode expire, the timer remains paused.

        Steps:
        1. Press Select to create a 5-minute timer
        2. Wait for edit mode to expire (auto-starts counting down)
        3. Wait 1s for timer to count down a bit
        4. Press Select to pause the timer
        5. Press Up to enter edit mode (ControlModeNew)
        6. Press Select to add 5 more minutes
        7. Wait for edit mode to expire (3.5s)
        8. Verify timer is in Counting mode but PAUSED at ~9:55
        """
        emulator = persistent_emulator

        # Start log capture - wait for log stream to connect
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(2.0)
        capture.clear_state_queue()

        # Step 1: Press Select to add 5 minutes
        logger.info("Setting 5-minute timer...")
        emulator.press_select()
        state_set = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_set is not None, "Did not receive button_select event"
        assert_time_approximately(state_set, minutes=4, seconds=58, tolerance=5)
        assert_mode(state_set, "New")
        logger.info(f"Timer set to 5 minutes: {state_set}")

        # Step 2: Wait for edit mode to expire (timer auto-starts)
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)
        state_auto_start = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_auto_start is not None, "Did not receive mode_change"
        assert_mode(state_auto_start, "Counting")
        assert_paused(state_auto_start, False)  # Should be running
        logger.info(f"Timer auto-started: {state_auto_start}")

        # Step 3: Wait 1s for timer to count down
        time.sleep(1.0)

        # Step 4: Press Select to pause
        logger.info("Pausing timer...")
        emulator.press_select()
        state_pause = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_pause is not None, "Did not receive button_select for pause"
        assert_paused(state_pause, True)
        logger.info(f"Timer paused: {state_pause}")

        # Step 5: Press Up to enter edit mode
        logger.info("Entering edit mode...")
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None, "Did not receive button_up event"
        assert_mode(state_edit, "New")
        logger.info(f"Entered edit mode: {state_edit}")

        # Step 6: Press Select to add 5 more minutes
        logger.info("Adding 5 more minutes...")
        emulator.press_select()
        state_add = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_add is not None, "Did not receive button_select for add"
        # Should be approximately 9:55 (5 min added to ~4:55 remaining)
        assert_time_approximately(state_add, minutes=9, seconds=55, tolerance=10)
        logger.info(f"After adding 5 more minutes: {state_add}")

        # Step 7: Wait for edit mode to expire
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)
        state_after_expire = capture.wait_for_state(event="mode_change", timeout=5.0)

        capture.stop()

        assert state_after_expire is not None, "Did not receive mode_change after edit expired"
        logger.info(f"After edit expired: {state_after_expire}")

        # Verify the timer is in Counting mode
        assert_mode(state_after_expire, "Counting")

        # KEY ASSERTION: Timer should be PAUSED after edit mode expires
        # because the user explicitly paused it before entering edit mode.
        # Bug: prv_new_expire_callback calls timer_toggle_play_pause() when
        # timer_is_paused() && !was_edit_sec_mode, which unpauses the timer.
        assert_paused(state_after_expire, True), (
            "Paused timer should remain paused after edit mode expires. "
            "Expected paused=1 but timer was auto-started."
        )

        # Verify time is approximately what we expect
        assert_time_approximately(state_after_expire, minutes=9, seconds=55, tolerance=10)
