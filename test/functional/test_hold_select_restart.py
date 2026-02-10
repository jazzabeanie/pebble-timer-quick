"""
Test Cases: Hold Select Restart (Pause-Preserving) - Spec #20

Tests that long-press Select in ControlModeCounting preserves the paused/running
state when restarting both countdown and chrono timers. Also tests that restarting
a repeating timer restores the full repeat count via base_repeat_count.
"""

import logging
import pytest
import time

from .conftest import (
    Button,
    EmulatorHelper,
    PLATFORMS,
    LogCapture,
    assert_time_equals,
    assert_time_approximately,
    assert_mode,
    assert_paused,
    assert_vibrating,
    assert_repeat_count,
)
from .test_timer_workflows import setup_short_timer

# Configure module logger
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """Module-scoped fixture that launches the emulator once per platform."""
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")

    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Warm-up cycle
    logger.info(f"[{platform}] Starting warm-up cycle")
    helper.wipe()
    helper.install()
    time.sleep(2)

    # Long press Down to quit and set persist state
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    time.sleep(0.5)

    logger.info(f"[{platform}] Emulator ready for tests")
    yield helper

    helper.kill()


class TestRestartRunningCountdown:
    """Test 1: Restart running countdown preserves running state."""

    def test_restart_running_countdown_preserves_running(self, persistent_emulator):
        """
        Steps:
        1. Create a 1-minute timer, let it start counting
        2. Wait a few seconds
        3. Long press Select
        4. Verify: timer restarts at ~1:00, still running, in Counting mode
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Set a 1-minute timer (press Down once in New mode)
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)

        # Wait for auto-transition to counting
        state_counting = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_counting is not None, "Did not transition to Counting"
        assert_mode(state_counting, "Counting")
        assert_paused(state_counting, False)

        # Wait a few seconds for timer to count down
        time.sleep(3)

        # Long press Select to restart
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_restart = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_restart is not None, "Did not receive long_press_select"
        logger.info(f"After restart state: {state_restart}")

        # Timer should be running (not paused), at ~1:00, in Counting mode
        assert_mode(state_restart, "Counting")
        assert_paused(state_restart, False)
        assert_time_approximately(state_restart, minutes=1, seconds=0, tolerance=3)


class TestLongPressPausedCountdownResetsToEditSec:
    """Test 2: Long press Select on paused countdown resets to 0:00 in EditSec."""

    def test_long_press_select_paused_countdown_resets_to_editsec(self, persistent_emulator):
        """
        Steps:
        1. Create a 1-minute timer, let it start counting
        2. Press Select to pause
        3. Long press Select
        4. Verify: timer resets to 0:00, paused, in EditSec mode
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Set a 1-minute timer
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)

        # Wait for counting mode
        state_counting = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_counting is not None
        assert_mode(state_counting, "Counting")

        # Wait a couple seconds
        time.sleep(2)

        # Press Select to pause
        emulator.press_select()
        state_paused = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_paused is not None
        assert_paused(state_paused, True)

        # Long press Select to reset to 0:00 and enter EditSec
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_reset = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_reset is not None, "Did not receive long_press_select"
        logger.info(f"After reset state: {state_reset}")

        # Timer should be at 0:00, paused, in EditSec mode
        assert_mode(state_reset, "EditSec")
        assert_paused(state_reset, True)
        assert_time_equals(state_reset, minutes=0, seconds=0)


class TestRestartRunningChrono:
    """Test 3: Restart running chrono preserves running state."""

    def test_restart_running_chrono_preserves_running(self, persistent_emulator):
        """
        Steps:
        1. Start app fresh, press Select to start chrono
        2. Wait a few seconds
        3. Long press Select
        4. Verify: chrono restarts at ~0:00, still running, in Counting mode
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for auto-transition to chrono (0:00 counting up)
        time.sleep(3.5)
        state_chrono = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_chrono is not None, "Did not enter chrono mode"
        assert_mode(state_chrono, "Counting")

        # Let chrono run for a few seconds
        time.sleep(3)

        # Long press Select to restart chrono
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_restart = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_restart is not None, "Did not receive long_press_select"
        logger.info(f"After restart state: {state_restart}")

        # Chrono should be running (not paused), at ~0:00
        assert_mode(state_restart, "Counting")
        assert_paused(state_restart, False)
        assert_time_approximately(state_restart, minutes=0, seconds=0, tolerance=3)


class TestLongPressPausedChronoResetsToEditSec:
    """Test 4: Long press Select on paused chrono resets to 0:00 in EditSec."""

    def test_long_press_select_paused_chrono_resets_to_editsec(self, persistent_emulator):
        """
        Steps:
        1. Start app fresh, let it auto-transition to chrono
        2. Wait, then press Select to pause
        3. Long press Select
        4. Verify: resets to 0:00, paused, in EditSec mode
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for chrono mode
        time.sleep(3.5)
        state_chrono = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_chrono is not None
        assert_mode(state_chrono, "Counting")

        # Let chrono run a bit
        time.sleep(3)

        # Press Select to pause
        emulator.press_select()
        state_paused = capture.wait_for_state(event="button_select", timeout=5.0)
        assert state_paused is not None
        assert_paused(state_paused, True)

        # Long press Select to reset to 0:00 and enter EditSec
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_reset = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_reset is not None, "Did not receive long_press_select"
        logger.info(f"After reset state: {state_reset}")

        # Should be at 0:00, paused, in EditSec mode
        assert_mode(state_reset, "EditSec")
        assert_paused(state_reset, True)
        assert_time_equals(state_reset, minutes=0, seconds=0)


class TestRestartRepeatingTimerRestoresCount:
    """Test 5: Restart repeating timer restores full repeat count."""

    def test_restart_repeating_timer_restores_repeat_count(self, persistent_emulator):
        """
        Steps:
        1. Create a 15-second timer
        2. Enable repeating with count of 3
        3. Let timer expire once (repeat fires, count decrements to 2)
        4. Long press Select to restart
        5. Verify: repeat_count restored to 3, timer running
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Set up 15-second timer
        setup_short_timer(emulator, seconds=15)

        # Consume setup events
        capture.clear_state_queue()

        # Enter edit repeat mode: long-press Up while in Counting mode
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        state_repeat = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_repeat is not None
        assert_mode(state_repeat, "EditRepeat")
        assert_repeat_count(state_repeat, 0)

        # Press Down 3 times (r: 0 -> 1 -> 2 -> 3)
        emulator.press_down()
        emulator.press_down()
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="button_down", timeout=2.0)
        state_r3 = capture.wait_for_state(event="button_down", timeout=2.0)
        assert_repeat_count(state_r3, 3)

        # Wait for mode transition to Counting
        state_counting = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_counting is not None
        assert_mode(state_counting, "Counting")
        assert_repeat_count(state_counting, 3)

        # Wait for first timer_repeat event (count 3 -> 2)
        state_repeat_fire = capture.wait_for_state(event="timer_repeat", timeout=15.0)
        assert state_repeat_fire is not None, "Timer did not repeat"
        assert_repeat_count(state_repeat_fire, 2)

        # Now long press Select to restart the timer
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_restart = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_restart is not None, "Did not receive long_press_select"
        logger.info(f"After restart state: {state_restart}")

        # repeat_count should be restored to 3 (from base_repeat_count)
        assert_repeat_count(state_restart, 3)
        assert_mode(state_restart, "Counting")
        assert_paused(state_restart, False)


class TestRestartDuringAlarm:
    """Test 6: Restart during alarm."""

    def test_restart_during_alarm(self, persistent_emulator):
        """
        Steps:
        1. Create a short countdown timer (4 seconds)
        2. Let it expire (alarm starts)
        3. Long press Select to restart
        4. Verify: timer restarts running from base_length, no vibration
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Set up 4-second timer
        setup_short_timer(emulator, seconds=4)

        # Wait for alarm
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=15.0)
        assert state_alarm is not None, "Timer did not alarm"
        assert_vibrating(state_alarm, True)

        # Long press Select to restart
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        # The raw handler should stop vibration, then long press restarts
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_restart = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_stop is not None, "Alarm did not stop"
        assert state_restart is not None, "Did not receive long_press_select"
        logger.info(f"After restart state: {state_restart}")

        # Timer should restart running at approximately the original duration
        assert_mode(state_restart, "Counting")
        assert_paused(state_restart, False)
        assert_vibrating(state_restart, False)
        assert_time_approximately(state_restart, minutes=0, seconds=4, tolerance=2)


class TestEditModeToggle:
    """Test 7: Long press Select toggles between New and EditSec."""

    def test_toggle_new_editsec_preserves_value(self, persistent_emulator):
        """
        Steps:
        1. Enter ControlModeNew (press Up from Counting)
        2. Long press Select -> toggles to EditSec (preserving value)
        3. Add 1 second
        4. Long press Select again (in EditSec) -> toggles to New (preserving value)
        """
        emulator = persistent_emulator

        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Set a 1-minute timer and enter counting
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)
        state_counting = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_counting is not None
        assert_mode(state_counting, "Counting")

        # Press Up to enter New mode
        emulator.press_up()
        state_new = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_new is not None
        assert_mode(state_new, "New")

        # Long press Select -> should toggle to EditSec (preserving value)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_toggle1 = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_toggle1 is not None
        assert_mode(state_toggle1, "EditSec")
        # Value should be preserved (~0:57 after some countdown)
        assert_time_approximately(state_toggle1, minutes=0, seconds=57, tolerance=10)

        # Add 1 second to verify we're in EditSec
        emulator.press_down()
        state_down = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_down is not None
        assert_mode(state_down, "EditSec")

        # Long press Select again -> should toggle to New (preserving value)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_toggle2 = capture.wait_for_state(event="long_press_select", timeout=5.0)
        capture.stop()

        assert state_toggle2 is not None
        assert_mode(state_toggle2, "New")
