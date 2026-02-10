"""
Test Cases: Timer workflow tests.

Tests common timer workflows like editing a running timer, snoozing,
repeating, and other interactions with a completed timer.

Note: The app has specific timing behavior:
- 3-second inactivity timer transitions from New/EditSec to Counting mode
- Short timers (≤4s) are set via ControlModeEditSec mode
- Header shows "New"/"Edit" in edit modes, time duration in counting mode
- Chrono mode (counting up) shows duration with "-->" arrow in header
"""

import logging
import pytest
from PIL import Image
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
from .test_create_timer import (
    extract_text,
    normalize_time_text,
    has_time_pattern,
    has_repeat_indicator,
    matches_indicator_reference,
)

# Configure module logger
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", params=PLATFORMS)
def persistent_emulator(request, build_app):
    """
    Module-scoped fixture that launches the emulator once per platform.

    The fixture performs a "warm-up" cycle:
    1. Wipe storage, install app
    2. Long press Down to quit the app (sets app state for next launch)

    The app is left closed after warmup. The _setup_test_environment autouse
    fixture handles opening/closing the app before/after each test.
    """
    platform = request.param
    platform_opt = request.config.getoption("--platform")
    if platform_opt and platform != platform_opt:
        pytest.skip(f"Skipping test for {platform} since --platform={platform_opt} was specified.")

    save_screenshots = request.config.getoption("--save-screenshots")
    helper = EmulatorHelper(platform, save_screenshots)

    # Warm-up cycle to clear any stale state and set initial persist state
    logger.info(f"[{platform}] Starting warm-up cycle to clear stale state")
    helper.wipe()
    helper.install()
    logger.info(f"[{platform}] Waiting for emulator to stabilize (2s)")
    time.sleep(2)

    # Long press Down button to quit the app - this sets the app's persist state
    logger.info(f"[{platform}] Holding down button to quit app and set persist state")
    helper.hold_button(Button.DOWN)
    time.sleep(1)
    helper.release_buttons()
    logger.info(f"[{platform}] App quit via long press, persist state set")
    time.sleep(0.5)

    # Navigate to launcher: after first quit the watch lands on the watchface.
    # Press SELECT to enter the launcher so open_app_via_menu() can launch
    # the app with a single SELECT press.
    helper.press_select()
    time.sleep(0.5)

    logger.info(f"[{platform}] Emulator ready for tests")

    yield helper

    # Teardown: kill emulator
    logger.info(f"[{platform}] Tearing down - killing emulator")
    helper.kill()


def setup_short_timer(emulator, seconds=4):
    """
    Set up a short timer with the given number of seconds.

    Flow:
    1. App starts fresh in ControlModeNew at 0:00
    2. Wait 3.5s for auto-transition to ControlModeCounting (chrono at 0:00)
    3. Press Select to pause the chrono
    4. Long press Select to reset to 0:00 and enter ControlModeEditSec
       (paused Counting + long-press Select does reset + EditSec)
    5. Press Down N times to add N seconds (uses timer_increment since
       is_editing_existing_timer=false, so length_ms is incremented)
    6. Wait 3.5s for expire timer to transition to ControlModeCounting
    7. Press Select to unpause (timer was paused from step 4's start_ms=0)
    8. Timer is now counting down from N seconds

    After this function returns, the timer is running and counting down.
    """
    logger.info(f"[{emulator.platform}] Setting up {seconds}s timer: waiting for chrono mode")

    # Step 2: Wait for transition to chrono mode (0:00 counting up)
    time.sleep(2.5)

    # Step 3: Press Select to pause the chrono
    emulator.press_select()
    time.sleep(0.3)

    # Step 4: Long press Select to reset to 0:00 and enter EditSec
    # In paused Counting mode, long press Select does:
    # timer_reset() + start_ms=0 + control_mode=ControlModeEditSec
    # With is_editing_existing_timer=false (creating new timer)
    emulator.hold_button(Button.SELECT)
    time.sleep(1)  # Hold for 750ms+ (BUTTON_HOLD_RESET_MS)
    emulator.release_buttons()
    time.sleep(0.3)

    # Step 5: Press Down N times to add N seconds
    # Since is_editing_existing_timer=false, prv_update_timer uses
    # timer_increment() which adds to length_ms (not start_ms)
    for i in range(seconds):
        emulator.press_down()
        time.sleep(0.2)

    logger.info(f"[{emulator.platform}] Short timer set to {seconds}s, waiting for expire")

    # Step 6: Wait for expire timer (3s after last button press)
    # This transitions from ControlModeEditSec to ControlModeCounting
    # Sub-minute timers stay paused after edit expires, so we need to start manually.
    time.sleep(3.5)

    # Step 7: Press Select to start the timer (sub-minute timers stay paused after edit expires)
    emulator.press_select()
    time.sleep(0.3)

    logger.info(f"[{emulator.platform}] Short timer started, counting down from {seconds}s")


class TestEditRunningTimer:
    """Test 1: Edit a running timer."""

    def test_edit_running_timer(self, persistent_emulator):
        """
        Verify that a running timer can be edited to add more time.

        Steps:
        1. Launch app and set a 2-minute timer (2x Down presses)
        2. Wait for auto-transition to counting mode (3s)
        3. Wait 2s for timer to count down a bit
        4. Press Up to enter edit mode
        5. Verify mode is "New" (edit existing timer) and time ~1:54
        6. Press Down to add 1 minute, verify time ~2:54
        7. Wait for mode transition back to Counting
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set a 2-minute timer
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=5.0)

        # Step 2: Wait for auto-transition to counting mode
        state_counting = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_counting is not None, "Did not receive mode_change to Counting"
        assert_mode(state_counting, "Counting")

        # Step 3: Wait 2 seconds for countdown
        time.sleep(2)

        # Step 4: Press Up to enter edit mode
        # In counting mode, Up transitions to ControlModeNew with is_editing_existing_timer=true
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None, "Did not receive button_up state"

        # Step 5: Verify we're in New mode (editing existing timer) with time ~1:54
        logger.info(f"Edit mode state: {state_edit}")
        assert_mode(state_edit, "New")
        assert_time_approximately(state_edit, minutes=1, seconds=54, tolerance=10)

        # Step 6: Press Down to add 1 minute
        emulator.press_down()
        state_after_add = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_after_add is not None, "Did not receive button_down after adding time"

        # Verify time increased by ~1 minute
        logger.info(f"After adding time state: {state_after_add}")
        assert_mode(state_after_add, "New")
        assert_time_approximately(state_after_add, minutes=2, seconds=54, tolerance=10)

        # Step 7: Wait for mode transition back to Counting (3s expire timer)
        state_resumed = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_resumed is not None, "Did not receive mode_change back to Counting"

        logger.info(f"Resumed counting state: {state_resumed}")
        assert_mode(state_resumed, "Counting")
        assert_paused(state_resumed, False)

        capture.stop()


class TestSetShortTimer:
    """Test 2: Set a 4-second timer."""

    def test_set_4_second_timer(self, persistent_emulator):
        """
        Verify that a short timer can be set and starts counting down.

        The setup_short_timer helper:
        1. Enters ControlModeNew via Up button, then ControlModeEditSec via long press Select
        2. Adds seconds via Down button presses
        3. Waits for expire timer to transition to ControlModeCounting
        4. Presses Select to unpause the timer

        After setup, the timer is running. This test captures a screenshot
        immediately to verify the timer is counting down.
        """
        emulator = persistent_emulator

        # Set up 4-second timer (this takes ~8s and starts the timer running)
        setup_short_timer(emulator, seconds=4)

        # Capture screenshot immediately (timer should be counting down)
        running_screenshot = emulator.screenshot("short_timer_running")

        # --- Perform OCR assertions ---

        running_text = extract_text(running_screenshot)
        logger.info(f"Short timer running text: {running_text}")

        # Verify we're in counting mode (no "Edit" or "New" header)
        # Header shows total duration (e.g., "00:04")
        normalized = normalize_time_text(running_text)
        logger.info(f"Short timer normalized: {normalized}")

        # Timer should be counting down. Display shows time like "0:03" or "0:04"
        # The header shows "00:04" (total duration) and main shows remaining time
        import re
        has_short_time = bool(re.search(r'0[:\.]?0[0-6]', normalized))
        assert has_short_time, (
            f"Expected short time value (around 0:04), got: {running_text} (normalized: {normalized})"
        )

        # Verify NOT in edit mode
        assert "Edit" not in running_text and "New" not in running_text, (
            f"Expected counting mode (not edit), got: {running_text}"
        )


class TestSnoozeCompletedTimer:
    """Test 3: Snooze a completed timer."""

    def test_snooze_completed_timer(self, persistent_emulator):
        """
        Verify that a completed timer can be snoozed with the Down button.

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for alarm_start event
        3. Press Down to snooze (adds 5 minutes)
        4. Verify state shows approximately 5:00 counting down
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 4-second timer
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for alarm_start event
        logger.info("Waiting for alarm to start...")
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=15.0)
        if state_alarm is None:
            logger.error(f"All captured logs: {capture.get_all_logs()}")
            logger.error(f"State queue: {capture.get_state_logs()}")
        assert state_alarm is not None, "Timer did not alarm"
        assert_vibrating(state_alarm, True)
        logger.info(f"Alarm started: {state_alarm}")

        # Step 3: Press Down to snooze
        emulator.press_down()
        
        # Step 4: Wait for alarm_stop and button_down logs
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_snooze = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        # Verify snooze state
        assert state_stop is not None, "Alarm did not stop"
        assert state_snooze is not None, "Did not receive button_down state"
        logger.info(f"After snooze state: {state_snooze}")
        
        # After snooze: should show ~5:00 counting down
        assert_time_approximately(state_snooze, minutes=5, seconds=0, tolerance=5)
        assert_mode(state_snooze, "Counting")
        assert_paused(state_snooze, False)
        assert_vibrating(state_snooze, False)


class TestRepeatCompletedTimer:
    """Test 4: Repeat a completed timer."""

    def test_repeat_completed_timer(self, persistent_emulator):
        """
        Verify that holding Up on a vibrating timer restarts the timer from the
        original duration.

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for alarm_start event
        3. Hold Up to repeat the timer
        4. Verify state shows alarm_stop and then long_press_up
        5. Verify timer restarts (back to 0:04)
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 4-second timer
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for alarm_start
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=10.0)
        assert state_alarm is not None, "Timer did not alarm"

        # Step 3: Hold Up to repeat
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()

        # Step 4: Wait for logs
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_repeat = capture.wait_for_state(event="long_press_up", timeout=5.0)

        capture.stop()

        # Verify repeat state
        assert state_stop is not None, "Alarm did not stop"
        assert state_repeat is not None, "Did not receive long_press_up state"
        logger.info(f"After repeat state: {state_repeat}")
        
        # Should show ~0:04 counting down
        # (It actually adds base_length_ms to length_ms, so it's 8s total, 4s elapsed)
        assert_time_approximately(state_repeat, minutes=0, seconds=4, tolerance=2)
        assert_mode(state_repeat, "Counting")
        assert_paused(state_repeat, False)
        assert_vibrating(state_repeat, False)


class TestQuietAlarmBackButton:
    """Test 5: Quiet alarm with back button."""

    def test_quiet_alarm_with_back_button(self, persistent_emulator):
        """
        Verify the back button quiets the alarm and the timer continues
        counting up in chrono mode.

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for alarm_start
        3. Press Back to silence
        4. Verify state shows alarm_stop and button_back
        5. Verify still in Counting mode, not vibrating, and approximately 0:04 (chrono)
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 4-second timer
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for alarm_start
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=10.0)
        assert state_alarm is not None, "Timer did not alarm"

        # Step 3: Press Back to silence
        emulator.press_back()
        
        # Step 4: Wait for logs
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_back = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        # Verify silenced state
        assert state_stop is not None, "Alarm did not stop"
        assert state_back is not None, "Did not receive button_back state"
        logger.info(f"After silence state: {state_back}")
        
        # Should show ~0:00 (chrono mode start)
        assert_mode(state_back, "Counting")
        assert_paused(state_back, False)
        assert_vibrating(state_back, False)
        assert_time_approximately(state_back, minutes=0, seconds=0, tolerance=2)


class TestPauseCompletedTimer:
    """Test 6: Pause a completed timer (in chrono mode)."""

    def test_pause_completed_timer(self, persistent_emulator):
        """
        Verify that a completed timer (in chrono mode) can be paused.

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for alarm_start
        3. Press Select to pause (also silences)
        4. Verify state shows alarm_stop and button_select
        5. Verify state is paused
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 4-second timer
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for alarm_start
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=10.0)
        assert state_alarm is not None, "Timer did not alarm"

        # Step 3: Press Select to pause
        emulator.press_select()
        
        # Step 4: Wait for logs
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_pause = capture.wait_for_state(event="button_select", timeout=5.0)

        capture.stop()

        # Verify paused state
        assert state_stop is not None, "Alarm did not stop"
        assert state_pause is not None, "Did not receive button_select state"
        logger.info(f"After pause state: {state_pause}")
        
        assert_mode(state_pause, "Counting")
        assert_paused(state_pause, True)
        assert_vibrating(state_pause, False)
        # Should show some time (around 0:00 chrono)
        assert_time_approximately(state_pause, minutes=0, seconds=0, tolerance=2)


class TestEditCompletedTimer:
    """Test 7: Edit a completed timer to add a minute."""

    def test_edit_completed_timer_add_minute(self, persistent_emulator):
        """
        Verify a completed timer can be silenced and edited with the up button.

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for alarm_start
        3. Press Up to enter edit mode (also silences)
        4. Press Down to add 1 minute
        5. Verify state is New mode and time is approximately 1:00
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 4-second timer
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for alarm_start
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=10.0)
        assert state_alarm is not None, "Timer did not alarm"

        # Step 3: Press Up to enter edit mode
        emulator.press_up()
        
        # Step 4: Wait for logs
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)

        assert state_stop is not None, "Alarm did not stop"
        assert state_edit is not None, "Did not receive button_up state"
        assert_mode(state_edit, "New")

        # Step 5: Press Down to add 1 minute
        emulator.press_down()
        state_down = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        # Verify added time
        assert state_down is not None, "Did not receive button_down state"
        logger.info(f"After adding minute state: {state_down}")
        
        assert_mode(state_down, "New")
        # Should show ~1:00 (it adds 1 minute to the recently expired timer)
        assert_time_approximately(state_down, minutes=1, seconds=0, tolerance=5)


class TestEnableRepeatingTimer:
    """Test 8: Enable repeating timer."""

    def test_enable_repeating_timer(self, persistent_emulator):
        """
        Verify that holding the Up button while a timer is counting down
        enables a repeating timer, starting at _x (no repeat) and requiring
        Down presses to increase to 3x for repeating.

        Steps:
        1. Set up and start a 10-second timer
        2. Long press Up to enable repeat edit mode (shows "_x", r=0)
        3. Press Down three times to increase to 3x (r=3)
        4. Wait for mode_change back to Counting
        5. Wait for timer to alarm and restart
        6. Verify repeat count decrements (r=3 -> r=2)
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 10-second timer
        setup_short_timer(emulator, seconds=10)

        # Step 2: Long press Up to enable repeat mode
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()

        state_repeat_init = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_repeat_init is not None, "Did not enter repeat mode"
        assert_mode(state_repeat_init, "EditRepeat")
        assert_repeat_count(state_repeat_init, 0) # Initially "_x" (0)

        # Step 3: Press Down three times (r: 0 -> 1 -> 2 -> 3)
        emulator.press_down() # 0 -> 1
        emulator.press_down() # 1 -> 2
        emulator.press_down() # 2 -> 3
        
        # Consume the 3 button_down logs
        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="button_down", timeout=2.0)
        state_r3 = capture.wait_for_state(event="button_down", timeout=2.0)
        assert_repeat_count(state_r3, 3)

        # Step 4: Wait for mode transition back to Counting
        state_counting = capture.wait_for_state(event="mode_change", timeout=5.0)
        assert state_counting is not None, "Did not return to counting mode"
        assert_mode(state_counting, "Counting")
        assert_repeat_count(state_counting, 3)

        # Step 5: Wait for timer_repeat (timer expires and restarts)
        logger.info("Waiting for timer to expire and restart...")
        state_repeat = capture.wait_for_state(event="timer_repeat", timeout=20.0)
        assert state_repeat is not None, "Timer did not repeat"
        
        # Step 6: Verify repeat count decrements after restart
        assert_repeat_count(state_repeat, 2)
        assert_time_approximately(state_repeat, minutes=0, seconds=10, tolerance=2)

        capture.stop()


class TestEditModeToggle:
    """Test 9: Edit mode toggle via long press select."""

    def test_long_press_select_toggles_new_to_editsec(self, persistent_emulator):
        """
        Verify that long pressing select while in ControlModeNew toggles to
        ControlModeEditSec, preserving the timer value.

        Steps:
        1. Set a 2-minute timer and wait for Counting mode
        2. Press Up to enter edit mode (ControlModeNew)
        3. Long press Select -> toggles to EditSec, value preserved
        4. Press Back button -> adds 60 seconds (confirms EditSec mode)
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set a 2-minute timer and wait for Counting mode
        emulator.press_down()
        emulator.press_down()
        # Wait for both presses and then the mode change
        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="mode_change", timeout=5.0)

        # Step 2: Press Up to enter edit mode
        emulator.press_up()
        state_edit = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "New")

        # Step 3: Long press Select to toggle to EditSec (preserving value)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_toggle = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_toggle is not None
        assert_mode(state_toggle, "EditSec")
        # Value should be preserved (~1:54 after some countdown)
        assert_time_approximately(state_toggle, minutes=1, seconds=54, tolerance=10)

        # Step 4: Press Back to add 60 seconds (confirms EditSec mode)
        emulator.press_back()
        state_back = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        assert state_back is not None
        assert_mode(state_back, "EditSec")

    def test_long_press_select_toggles_editsec_to_new(self, persistent_emulator):
        """
        Verify that long pressing select while in ControlModeEditSec toggles to
        ControlModeNew, preserving the timer value.

        Steps:
        1. Enter EditSec mode (via paused chrono + long-press Select)
        2. Add 20 seconds
        3. Long press Select -> toggles to New, value preserved
        4. Press Down -> adds 1 minute (confirms New mode)
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for chrono mode, pause it
        time.sleep(3.5)
        emulator.press_select()
        time.sleep(0.3)

        # Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_editsec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_editsec is not None
        assert_mode(state_editsec, "EditSec")

        # Add 20 seconds
        emulator.press_up()
        state_up = capture.wait_for_state(event="button_up", timeout=5.0)
        assert state_up is not None
        assert_time_equals(state_up, minutes=0, seconds=20)

        # Long press Select to toggle to New mode
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()

        state_toggle = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_toggle is not None
        assert_mode(state_toggle, "New")
        assert_time_equals(state_toggle, minutes=0, seconds=20)

        # Press Down to add 1 minute (confirms New mode)
        emulator.press_down()
        state_down = capture.wait_for_state(event="button_down", timeout=5.0)

        capture.stop()

        assert state_down is not None
        assert_time_equals(state_down, minutes=1, seconds=20)
        assert_mode(state_down, "New")


class TestEditSecModeToggle:
    """Test 10: Long press select in ControlModeEditSec toggles to New mode."""

    def test_long_press_select_in_edit_sec_mode_toggles_to_new(self, persistent_emulator):
        """
        Verify that long pressing select in ControlModeEditSec toggles to New mode
        preserving timer value.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for auto-chrono mode, pause it
        logger.info("Waiting for chrono mode (0:00 counting up)...")
        time.sleep(3.5)
        emulator.press_select()
        time.sleep(0.3)

        # Step 2: Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_reset = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_reset is not None
        assert_mode(state_reset, "EditSec")

        # Step 3: Press Up to add 20 seconds (verify we are in EditSec)
        emulator.press_up()
        state_up = capture.wait_for_state(event="button_up", timeout=5.0)
        assert_mode(state_up, "EditSec")
        assert_time_equals(state_up, minutes=0, seconds=20)

        # Step 4: Press Down to add 1 second (total 0:21)
        emulator.press_down()
        state_before = capture.wait_for_state(event="button_down", timeout=5.0)
        assert state_before is not None
        assert_time_equals(state_before, minutes=0, seconds=21)
        assert_mode(state_before, "EditSec")

        # Step 5: Long press Select -> should toggle to New mode
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_after = capture.wait_for_state(event="long_press_select", timeout=5.0)

        capture.stop()

        assert state_after is not None
        # Should be 0:21 but now in New mode
        assert_time_equals(state_after, minutes=0, seconds=21)
        assert_mode(state_after, "New")


class TestEditRepeatModeNoOp:
    """Test 11: Long press select in ControlModeEditRepeat does nothing."""

    def test_long_press_select_in_edit_repeat_mode_does_nothing(self, persistent_emulator):
        """
        Verify that long pressing select in ControlModeEditRepeat has no effect.
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set a 2-minute timer and wait for countdown
        emulator.press_down()
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="mode_change", timeout=5.0)

        # Step 2: Long press Up to enable repeat mode
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        state_before = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_before is not None
        assert_mode(state_before, "EditRepeat")

        # Step 3: Long press Select -> should do nothing
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_after = capture.wait_for_state(event="long_press_select", timeout=5.0)

        capture.stop()

        assert state_after is not None
        assert_mode(state_after, "EditRepeat")
        # repeat_count should be same (0)
        assert_repeat_count(state_after, 0)


class TestRepeatTimerDuringAlarm:
    """Test 12: Holding Up during alarm repeats the current timer."""

    def test_hold_up_during_alarm_repeats_timer(self, persistent_emulator):
        """
        Verify that holding the Up button while the alarm is vibrating
        repeats the current timer from its original duration.

        This tests the specific interaction when the timer has completed
        and is actively alarming (vibrating). Holding Up should:
        1. Stop the alarm
        2. Restart the timer from its original duration

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for alarm_start event (timer vibrating)
        3. Hold Up button while alarm is active
        4. Verify alarm stops and timer restarts at original duration
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 4-second timer manually
        # Wait for app to enter chrono mode (0:00 counting up)
        logger.info("Waiting for chrono mode...")
        time.sleep(3.5)

        # Press Select to pause the chrono
        emulator.press_select()
        time.sleep(0.3)

        # Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.3)

        # Add 4 seconds by pressing Down 4 times
        for i in range(4):
            emulator.press_down()
            time.sleep(0.2)

        # Wait for edit mode to expire and transition to Counting mode
        # (Sub-minute timers now stay paused after edit expires)
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)

        # Press Select to start the paused timer
        logger.info("Pressing Select to start 4-second timer...")
        emulator.press_select()

        # Consume log events from setup
        capture.clear_state_queue()

        # Step 2: Wait for alarm_start
        logger.info("Waiting for alarm to start...")
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=15.0)
        if state_alarm is None:
            logger.error(f"All captured logs: {capture.get_all_logs()}")
        assert state_alarm is not None, "Timer did not alarm"
        assert_vibrating(state_alarm, True)
        logger.info(f"Alarm started: {state_alarm}")

        # Step 3: Hold Up to repeat the timer
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()

        # Step 4: Wait for alarm_stop and the repeat action
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_repeat = capture.wait_for_state(event="long_press_up", timeout=5.0)

        capture.stop()

        # Verify the alarm stopped
        assert state_stop is not None, "Alarm did not stop after holding Up"

        # Verify the timer was repeated
        assert state_repeat is not None, "Did not receive long_press_up state after holding Up during alarm"
        logger.info(f"After repeat state: {state_repeat}")

        # Should show ~0:04 (the original timer duration) and be counting down
        assert_time_approximately(state_repeat, minutes=0, seconds=4, tolerance=2)
        assert_mode(state_repeat, "Counting")
        assert_paused(state_repeat, False)
        assert_vibrating(state_repeat, False)

    def test_hold_up_during_longer_alarm_repeats_timer(self, persistent_emulator):
        """
        Verify that holding the Up button while the alarm is vibrating
        repeats the current timer from its original duration.

        This tests the specific interaction when the timer has completed
        and is actively alarming (vibrating). Holding Up should:
        1. Stop the alarm
        2. Restart the timer from its original duration

        Steps:
        1. Set up and start a 5-second timer
        2. Wait for alarm_start event (timer vibrating)
        3. Hold Up button while alarm is active
        4. Verify alarm stops and timer restarts at original duration
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Wait for chrono/counting mode, then pause
        time.sleep(3.5)
        emulator.press_select()
        time.sleep(0.3)

        # Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.3)

        # Add 10 seconds (Select adds +5s in EditSec mode)
        emulator.press_select()
        time.sleep(0.2)
        emulator.press_select()

        # Wait for edit mode to expire and transition to Counting mode
        # (Sub-minute timers now stay paused after edit expires)
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)

        # Press Select to start the paused timer
        logger.info("Pressing Select to start 10-second timer...")
        emulator.press_select()

        # Consume log events from setup
        capture.clear_state_queue()

        # Step 2: Wait for alarm_start
        logger.info("Waiting for alarm to start...")
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=12.0)
        if state_alarm is None:
            logger.error(f"All captured logs: {capture.get_all_logs()}")
        assert state_alarm is not None, "Timer did not alarm"
        assert_vibrating(state_alarm, True)
        logger.info(f"Alarm started: {state_alarm}")

        # Step 3: Hold Up to repeat the timer
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()

        # Step 4: Wait for alarm_stop and the repeat action
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_repeat = capture.wait_for_state(event="long_press_up", timeout=5.0)

        capture.stop()

        # Verify the alarm stopped
        assert state_stop is not None, "Alarm did not stop after holding Up"

        # Verify the timer was repeated
        assert state_repeat is not None, "Did not receive long_press_up state after holding Up during alarm"
        logger.info(f"After repeat state: {state_repeat}")

        # Should show ~0:10 (the original timer duration) and be counting down
        assert_time_approximately(state_repeat, minutes=0, seconds=10, tolerance=2)
        assert_mode(state_repeat, "Counting")
        assert_paused(state_repeat, False)
        assert_vibrating(state_repeat, False)

    def test_hold_up_during_longer_alarm_repeats_timer_old_method(self, persistent_emulator):
        """
        Verify that holding the Up button while the alarm is vibrating
        repeats the current timer from its original duration.

        This tests the specific interaction when the timer has completed
        and is actively alarming (vibrating). Holding Up should:
        1. Stop the alarm
        2. Restart the timer from its original duration

        Steps:
        1. Set up and start a 5-second timer
        2. Wait for alarm_start event (timer vibrating)
        3. Hold Up button while alarm is active
        4. Verify alarm stops and timer restarts at original duration
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 10-second timer manually
        # Wait for app to enter chrono mode (0:00 counting up)
        logger.info("Waiting for chrono mode...")
        time.sleep(3.5)

        # Press Select to pause the chrono
        emulator.press_select()
        time.sleep(0.3)

        # Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.3)

        # Add 10 seconds (Select adds +5s in EditSec mode)
        emulator.press_select()
        time.sleep(0.2)
        emulator.press_select()

        # Wait for edit mode to expire and transition to Counting mode
        # (Sub-minute timers now stay paused after edit expires)
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)

        # Press Select to start the paused timer
        logger.info("Pressing Select to start 10-second timer...")
        emulator.press_select()

        # Consume log events from setup
        capture.clear_state_queue()

        # Step 2: Wait for alarm_start
        logger.info("Waiting for alarm to start...")
        state_alarm = capture.wait_for_state(event="alarm_start", timeout=12.0)
        if state_alarm is None:
            logger.error(f"All captured logs: {capture.get_all_logs()}")
        assert state_alarm is not None, "Timer did not alarm"
        assert_vibrating(state_alarm, True)
        logger.info(f"Alarm started: {state_alarm}")

        # Step 3: Hold Up to repeat the timer
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()

        # Step 4: Wait for alarm_stop and the repeat action
        state_stop = capture.wait_for_state(event="alarm_stop", timeout=5.0)
        state_repeat = capture.wait_for_state(event="long_press_up", timeout=5.0)

        capture.stop()

        # Verify the alarm stopped
        assert state_stop is not None, "Alarm did not stop after holding Up"

        # Verify the timer was repeated
        assert state_repeat is not None, "Did not receive long_press_up state after holding Up during alarm"
        logger.info(f"After repeat state: {state_repeat}")

        # Should show ~0:10 (the original timer duration) and be counting down
        assert_time_approximately(state_repeat, minutes=0, seconds=10, tolerance=2)
        assert_mode(state_repeat, "Counting")
        assert_paused(state_repeat, False)
        assert_vibrating(state_repeat, False)


class TestSubMinuteTimerStaysPaused:
    """Test 13: Sub-minute timers stay paused after edit mode expires."""

    def test_sub_minute_timer_stays_paused_after_edit_expires(self, persistent_emulator):
        """
        Verify that when creating a stopwatch with seconds (e.g., 10 seconds),
        it remains paused when edit mode expires and requires manual unpause.

        Current expected behavior (to be implemented):
        - After setting seconds in EditSec mode
        - When the 3-second inactivity timer expires
        - Timer should transition to Counting mode but remain PAUSED
        - User must press Select to start the timer

        Steps:
        1. Wait for app to enter chrono mode (0:00 counting up)
        2. Press Up to enter New mode (from Counting mode)
        3. Long press Select to enter EditSec mode
        4. Press Down 10 times to set 10 seconds
        5. Wait for edit mode to expire (3.5 seconds)
        6. Verify timer is in Counting mode but PAUSED at ~0:10
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Wait for auto-chrono mode (0:00 counting up)
        logger.info("Waiting for chrono mode...")
        time.sleep(3.5)

        # Consume any mode_change events from startup
        capture.wait_for_state(event="mode_change", timeout=2.0)

        # Step 2: Press Select to pause the chrono
        emulator.press_select()
        time.sleep(0.3)

        # Step 3: Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_edit = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_edit is not None
        assert_mode(state_edit, "EditSec")
        logger.info("Entered EditSec mode")

        # Step 4: Press Down 10 times to set 10 seconds
        for i in range(10):
            emulator.press_down()
            time.sleep(0.15)

        # Consume the button_down events
        for i in range(10):
            capture.wait_for_state(event="button_down", timeout=2.0)

        # Step 5: Wait for edit mode to expire (3 seconds after last button)
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)

        # Step 6: Wait for mode_change to Counting
        state_after_expire = capture.wait_for_state(event="mode_change", timeout=5.0)

        capture.stop()

        assert state_after_expire is not None, "Did not receive mode_change after edit expired"
        logger.info(f"After edit expired: {state_after_expire}")

        # Verify the timer is in Counting mode
        assert_mode(state_after_expire, "Counting")

        # KEY ASSERTION: Timer should be PAUSED after edit mode expires
        # (This is the new behavior being tested - currently it auto-starts)
        assert_paused(state_after_expire, True), (
            "Sub-minute timer should remain paused after edit mode expires. "
            "Expected paused=1 but timer auto-started."
        )

        # Verify time is approximately what we set
        assert_time_approximately(state_after_expire, minutes=0, seconds=10, tolerance=2)


class TestMinuteAndSecondsTimerStaysPaused:
    """Test 14: Timer with minutes and seconds stays paused after edit mode expires."""

    def test_minute_and_seconds_timer_stays_paused(self, persistent_emulator):
        """
        Verify that when creating a timer with both minutes AND seconds
        (e.g., 1 minute and 20 seconds), it remains paused when edit mode expires.

        This tests the case where seconds are added to a minute-based timer.

        Steps:
        1. Set a 1-minute timer (press Down once)
        2. Press Up to enter edit mode
        3. Long press Select to reset and enter EditSec mode
        4. Press Down 20 times to add 20 seconds
        5. Wait for edit mode to expire
        6. Verify timer is in Counting mode but PAUSED at 0:20
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set a 1-minute timer
        emulator.press_down()
        capture.wait_for_state(event="button_down", timeout=2.0)

        # Wait for countdown mode
        time.sleep(3.5)
        capture.wait_for_state(event="mode_change", timeout=5.0)

        # Step 2: Press Select to pause the countdown
        emulator.press_select()
        time.sleep(0.3)

        # Step 3: Long press Select to reset to 0:00 and enter EditSec (from paused Counting)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        state_edit_sec = capture.wait_for_state(event="long_press_select", timeout=5.0)
        assert state_edit_sec is not None
        assert_mode(state_edit_sec, "EditSec")
        assert_time_equals(state_edit_sec, minutes=0, seconds=0)
        logger.info("Entered EditSec mode at 0:00")

        # Step 4: Press Down 20 times to add 20 seconds
        for i in range(20):
            emulator.press_down()
            time.sleep(0.15)

        # Consume the button_down events
        for i in range(20):
            capture.wait_for_state(event="button_down", timeout=2.0)

        # Step 5: Wait for edit mode to expire
        logger.info("Waiting for edit mode to expire...")
        time.sleep(3.5)

        # Step 6: Wait for mode_change to Counting
        state_after_expire = capture.wait_for_state(event="mode_change", timeout=5.0)

        capture.stop()

        assert state_after_expire is not None, "Did not receive mode_change after edit expired"
        logger.info(f"After edit expired: {state_after_expire}")

        # Verify the timer is in Counting mode
        assert_mode(state_after_expire, "Counting")

        # KEY ASSERTION: Timer should be PAUSED after edit mode expires
        assert_paused(state_after_expire, True), (
            "Timer with seconds should remain paused after edit mode expires. "
            "Expected paused=1 but timer auto-started."
        )

        # Verify time is approximately 0:20
        assert_time_approximately(state_after_expire, minutes=0, seconds=20, tolerance=2)


class TestEditRepeatBackButton:
    """Test: Back button in ControlModeEditRepeat resets repeat count to 0."""

    def test_back_button_resets_repeat_count_to_zero(self, persistent_emulator):
        """
        Verify that pressing Back in ControlModeEditRepeat resets repeat_count to 0.

        Steps:
        1. Set up a short timer
        2. Long press Up to enable repeat mode (enters EditRepeat with count=0)
        3. Press Down 3 times to set repeat_count to 3
        4. Press Back to reset repeat_count
        5. Assert repeat_count is 0
        """
        emulator = persistent_emulator

        # Start log capture
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Step 1: Set up 10-second timer
        setup_short_timer(emulator, seconds=10)

        # Step 2: Long press Up to enable repeat mode
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()

        state_repeat_init = capture.wait_for_state(event="long_press_up", timeout=5.0)
        assert state_repeat_init is not None, "Did not enter repeat mode"
        assert_mode(state_repeat_init, "EditRepeat")
        assert_repeat_count(state_repeat_init, 0)

        # Step 3: Press Down 3 times (repeat_count: 0 -> 1 -> 2 -> 3)
        emulator.press_down()
        emulator.press_down()
        emulator.press_down()

        capture.wait_for_state(event="button_down", timeout=2.0)
        capture.wait_for_state(event="button_down", timeout=2.0)
        state_r3 = capture.wait_for_state(event="button_down", timeout=2.0)
        assert_repeat_count(state_r3, 3)

        # Step 4: Press Back to reset repeat count
        emulator.press_back()
        state_after_back = capture.wait_for_state(event="button_back", timeout=5.0)

        capture.stop()

        assert state_after_back is not None, "Did not receive button_back event"
        assert_mode(state_after_back, "EditRepeat")
        # KEY ASSERTION: Back should reset repeat_count to 0, not 1
        assert_repeat_count(state_after_back, 0)
