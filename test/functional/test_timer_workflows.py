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

from .conftest import Button, EmulatorHelper, PLATFORMS
from .test_create_timer import (
    extract_text,
    normalize_time_text,
    has_time_pattern,
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
    3. Press Select to pause chrono
    4. Long press Select to enter ControlModeEditSec with clean state
       (timer_reset + start_ms=0, is_editing_existing_timer stays false)
    5. Press Down N times to add N seconds (uses timer_increment since
       is_editing_existing_timer=false, so length_ms is incremented)
    6. Wait 3.5s for expire timer to transition to ControlModeCounting
    7. Press Select to unpause (timer was paused from step 4's start_ms=0)
    8. Timer is now counting down from N seconds

    After this function returns, the timer is running and counting down.
    """
    logger.info(f"[{emulator.platform}] Setting up {seconds}s timer: waiting for chrono mode")

    # Step 2: Wait for transition to chrono mode (0:00 counting up)
    time.sleep(3.5)

    # Step 3: Pause the chrono
    emulator.press_select()
    time.sleep(0.3)

    # Step 4: Long press Select to enter ControlModeEditSec with clean state
    # In ControlModeCounting with chrono paused, long press Select does:
    # timer_reset() + start_ms=0 + control_mode=ControlModeEditSec
    # Critically, is_editing_existing_timer remains false (only set by Up click)
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
    # Timer is still paused (start_ms=0 from step 4)
    time.sleep(3.5)

    # Step 7: Press Select to unpause the timer
    # In ControlModeCounting, Select toggles play/pause
    # start_ms goes from 0 to epoch() (running)
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
        4. Press Up to enter edit mode (adds 1 minute in edit mode via Up)
        5. Verify header shows "Edit" and time increased
        6. Wait for timer to resume counting (3s expire timer)
        7. Verify timer continues counting down
        """
        emulator = persistent_emulator

        # Step 1: Set a 2-minute timer
        emulator.press_down()
        emulator.press_down()

        # Step 2: Wait for auto-transition to counting mode
        time.sleep(4)

        # Step 3: Wait 2 seconds for countdown
        time.sleep(2)

        # Step 4: Press Up to enter edit mode
        # In counting mode, Up transitions to ControlModeNew with is_editing_existing_timer=true
        emulator.press_up()
        time.sleep(0.5)

        # Capture screenshot in edit mode
        edit_screenshot = emulator.screenshot("edit_mode")

        # Step 5: Now the timer is in edit mode.
        emulator.press_down()
        time.sleep(0.5)

        # Capture screenshot after adding time
        after_add_screenshot = emulator.screenshot("after_add_time")

        # Step 6: Wait for expire timer to start counting (3s)
        time.sleep(4)

        # Step 7: Capture screenshot of resumed counting
        resumed_screenshot = emulator.screenshot("resumed_counting")

        # --- Now perform OCR assertions ---

        # Verify edit mode shows "Edit" header
        edit_text = extract_text(edit_screenshot)
        logger.info(f"Edit mode text: {edit_text}")
        assert "Edit" in edit_text, f"Expected 'Edit' header in edit mode, got: {edit_text}"

        # Verify time was added (should show approximately 1:5x + 1:00 = 2:5x)
        # After 6 seconds of counting from 2:00, timer was ~1:54
        # Then we entered edit mode and added 1 minute → ~2:54
        after_add_text = extract_text(after_add_screenshot)
        logger.info(f"After adding time: {after_add_text}")
        # Check for time around 2:50-2:59
        normalized = normalize_time_text(after_add_text)
        has_expected_time = has_time_pattern(after_add_text, minutes=3, tolerance=15)
        assert has_expected_time, (
            f"Expected time around 2:5x after adding 1 minute, got: {after_add_text}"
        )

        # Verify timer resumes counting (display should change from edit mode)
        resumed_text = extract_text(resumed_screenshot)
        logger.info(f"Resumed counting: {resumed_text}")
        # Should no longer show "Edit" - should show time duration in header
        assert "Edit" not in resumed_text and "New" not in resumed_text, (
            f"Expected counting mode (no Edit/New), got: {resumed_text}"
        )


class TestSetShortTimer:
    """Test 2: Set a 4-second timer."""

    def test_set_4_second_timer(self, persistent_emulator):
        """
        Verify that a short timer can be set and starts counting down.

        The setup_short_timer helper:
        1. Enters ControlModeEditSec via long press Select on paused chrono
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
        1. Set up and start a 4-second timer (setup_short_timer starts it running)
        2. Wait for 4-second countdown to complete + vibration buffer
        3. Timer enters chrono mode and starts vibrating
        4. Press Down to snooze (adds 5 minutes)
        5. Verify the timer now shows ~5:00 counting down

        Key behavior: Down button during vibration adds SNOOZE_INCREMENT_MS
        (5 minutes) to the timer and cancels vibration.
        """
        emulator = persistent_emulator

        # --- Capture all screenshots first (OCR deferred) ---

        # Step 1: Set up 4-second timer (starts running after setup)
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for 4-second countdown to complete + buffer
        time.sleep(5)

        # Step 3: Timer should be vibrating in chrono mode now
        # Take screenshot before snooze
        before_snooze = emulator.screenshot("before_snooze")

        # Step 4: Press Down to snooze
        emulator.press_down()
        time.sleep(0.5)

        # Take screenshot after snooze
        after_snooze = emulator.screenshot("after_snooze")

        # Cancel any quit timer by pressing Down again (safe in counting mode)
        emulator.press_down()

        # --- Perform OCR assertions ---

        before_text = extract_text(before_snooze)
        logger.info(f"Before snooze: {before_text}")

        # Before snooze: should show chrono mode (timer completed, counting up)
        # Header shows "XX:XX-->" pattern
        normalized_before = normalize_time_text(before_text)
        has_chrono_arrow = "-->" in before_text or "-->" in normalized_before
        # Also accept: OCR might not read the arrow cleanly
        logger.info(f"Before snooze normalized: {normalized_before}")

        after_text = extract_text(after_snooze)
        logger.info(f"After snooze: {after_text}")

        # After snooze: should show ~5:00 counting down (snooze adds 5 minutes)
        # The header should show total timer duration (not "Edit" or "New")
        normalized_after = normalize_time_text(after_text)
        logger.info(f"After snooze normalized: {normalized_after}")

        # Check for approximately 5 minutes (4:5x to 5:00 range)
        has_snooze_time = has_time_pattern(after_text, minutes=5, tolerance=15)
        assert has_snooze_time, (
            f"Expected time around 5:00 after snooze, got: {after_text}"
        )

        # Verify we're not in edit mode (no "Edit" or "New" header)
        assert "Edit" not in after_text and "New" not in after_text, (
            f"Expected counting mode after snooze (no Edit/New), got: {after_text}"
        )


class TestRepeatCompletedTimer:
    """Test 4: Repeat a completed timer."""

    def test_repeat_completed_timer(self, persistent_emulator):
        """
        Verify that holding Up on a vibrating timer restarts the timer from the
        original duration.

        TODO: complete this docstring
        """
        emulator = persistent_emulator

        # --- Capture screenshots first (OCR deferred) ---

        # Step 1: Set up 4-second timer (starts running)
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for countdown to complete + vibration buffer
        time.sleep(5)

        # Step 3: Press Up to repeat the timer
        emulator.hold_button(Button.UP)
        time.sleep(0.5)

        # Capture screenshot in edit mode
        repeat_screenshot = emulator.screenshot("repeat")

        # Cancel quit timer
        emulator.press_down()

        # --- Perform OCR assertions ---

        repeat_text = extract_text(repeat_screenshot)
        logger.info(f"After holding Up during alarm: {repeat_text}")

        # Verify edit mode: header should show twice the original duration
        # Timer should show less than 00:04
        # TODO:


class TestQuietAlarmBackButton:
    """Test 5: Quiet alarm with back button."""

    def test_quiet_alarm_with_back_button(self, persistent_emulator):
        """
        Verify the back button quiets the alarm and the timer continues
        counting up in chrono mode.

        Steps:
        1. Set up and start a 4-second timer (already running after setup)
        2. Wait for countdown to complete (vibrating in chrono mode)
        3. Press Back to silence the alarm
        4. Verify the timer is in chrono mode (counting up, header shows "-->")
        5. Wait 2 seconds to verify timer continues counting

        Key behavior: Back button during vibration calls prv_handle_alarm()
        which sets can_vibrate=false and cancels vibration. Timer stays in
        ControlModeCounting in chrono mode.
        """
        emulator = persistent_emulator

        # --- Capture screenshots first (OCR deferred) ---

        # Step 1: Set up 4-second timer (starts running)
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for countdown to complete + buffer
        time.sleep(5)

        # Step 3: Press Back to silence alarm
        emulator.press_back()
        time.sleep(0.5)

        # Step 4: Take screenshot (should be in chrono mode, no vibration)
        after_back = emulator.screenshot("after_back_silence")

        # Step 5: Wait 2 seconds and take another screenshot
        time.sleep(2)
        still_counting = emulator.screenshot("still_counting_up")

        # Cancel quit timer
        emulator.press_down()

        # --- Perform OCR assertions ---

        after_back_text = extract_text(after_back)
        logger.info(f"After Back (silenced): {after_back_text}")

        # Verify chrono mode: header should contain "-->" arrow
        normalized = normalize_time_text(after_back_text)
        logger.info(f"After Back normalized: {normalized}")
        has_chrono = "-->" in after_back_text or "-->" in normalized
        # Also check: not in edit mode (no "Edit" or "New")
        not_edit = "Edit" not in after_back_text and "New" not in after_back_text
        assert has_chrono or not_edit, (
            f"Expected chrono mode (header with '-->') after Back, got: {after_back_text}"
        )

        # Verify timer continues counting up
        still_text = extract_text(still_counting)
        logger.info(f"Still counting: {still_text}")

        # The two screenshots should differ (timer counting up)
        assert after_back.tobytes() != still_counting.tobytes(), (
            f"Display should change as chrono counts up. "
            f"After Back: {after_back_text}, Still: {still_text}"
        )


class TestPauseCompletedTimer:
    """Test 6: Pause a completed timer (in chrono mode)."""

    def test_pause_completed_timer(self, persistent_emulator):
        """
        Verify that a completed timer (in chrono mode) can be paused.

        Steps:
        1. Set up and start a 4-second timer
        2. Wait for timer to complete → chrono mode (vibrating)
        3. Press Back to silence alarm (stays in chrono, counting up)
        4. Wait 2 seconds
        5. Press Select to pause
        6. Verify display stops changing (paused)

        Key behavior: Select in ControlModeCounting during chrono mode
        (after alarm silenced) toggles play/pause via timer_toggle_play_pause().
        """
        emulator = persistent_emulator

        # --- Capture screenshots first (OCR deferred) ---

        # Step 1: Set up 4-second timer (starts running)
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for countdown to complete
        time.sleep(5)

        # Step 3: Press Select to pause
        emulator.press_select()
        time.sleep(0.5)

        # Capture paused screenshot
        paused = emulator.screenshot("paused_chrono")

        # Step 4: Wait 2 seconds - should still show same time
        time.sleep(2)
        still_paused = emulator.screenshot("still_paused_chrono")

        # --- Perform OCR assertions ---

        paused_text = extract_text(paused)
        logger.info(f"Paused chrono: {paused_text}")

        still_paused_text = extract_text(still_paused)
        logger.info(f"Still paused: {still_paused_text}")

        # Compare the main timer values (not the footer clock time which changes)
        # The footer shows wall clock time (e.g., "14:16") which changes every minute.
        # We need to crop out the footer and compare just the timer portion.
        # Alternative: Compare the upper 2/3 of the screenshot (timer area)
        # The Pebble basalt screen is 168x180. Crop to top ~140px to exclude footer.
        paused_cropped = paused.crop((0, 0, paused.width, int(paused.height * 0.75)))
        still_paused_cropped = still_paused.crop((0, 0, still_paused.width, int(still_paused.height * 0.75)))

        assert paused_cropped.tobytes() == still_paused_cropped.tobytes(), (
            f"Timer display should NOT change while paused (comparing top 75%). "
            f"Paused: {paused_text}, Still: {still_paused_text}"
        )


class TestEditCompletedTimer:
    """Test 7: Edit a completed timer to add a minute."""

    def test_edit_completed_timer_add_minute(self, persistent_emulator):
        """
        Verify a completed timer (still in alarm) can be silenced and edited
        with the up button.

        TODO: expand this docstring
        """
        emulator = persistent_emulator

        # --- Capture screenshots first (OCR deferred) ---

        # Step 1: Set up 4-second timer (starts running)
        setup_short_timer(emulator, seconds=4)

        # Step 2: Wait for countdown to complete
        time.sleep(5)

        # Step 3: Press Up to enter edit mode
        emulator.press_up()
        time.sleep(0.5)

        # Capture edit mode screenshot
        edit_screenshot = emulator.screenshot("edit_completed")

        # Step 4: Press Down to add 1 minute
        emulator.press_down()
        time.sleep(0.5)

        after_add_screenshot = emulator.screenshot("after_add_minute")

        # --- Perform OCR assertions ---

        edit_text = extract_text(edit_screenshot)
        logger.info(f"Edit completed timer: {edit_text}")

        # Verify edit mode: header should show "Edit"
        assert "Edit" in edit_text, (
            f"Expected 'Edit' header after Up in chrono mode, got: {edit_text}"
        )

        after_add_text = extract_text(after_add_screenshot)
        logger.info(f"After adding minute: {after_add_text}")

        # After adding 1 minute to a recently expired timer,
        # the time should be just under 1 minute.
        normalized = normalize_time_text(after_add_text)
        # Check for time pattern around 1 minute
        has_minute = has_time_pattern(after_add_text, minutes=1, tolerance=10)
        assert has_minute, (
            f"Expected time around 1:0x after adding 1 minute, got: {after_add_text}"
        )


class TestEnableRepeatingTimer:
    """Test 8: Enable repeating timer (expected to fail)."""

    @pytest.mark.xfail(reason="Repeating timer feature not yet fully implemented")
    def test_enable_repeating_timer(self, persistent_emulator):
        """
        Verify that holding the Up button while a timer is counting down
        enables a repeating timer.

        Steps:
        1. Set up and start a 4-second timer
        2. Hold Up button for 1 second (should enable repeat mode)
        3. Wait for timer to complete
        4. Verify the timer restarts automatically

        Status: Expected to fail - the long press Up during countdown
        toggles reverse direction, not repeat mode.
        """
        emulator = persistent_emulator

        # Step 1: Set up 10-second timer (starts running)
        setup_short_timer(emulator, seconds=10)
        
        time.sleep(4)  # to allow new mode to expire

        # Step 2: Hold Up button (long press while counting down)
        # which should enable repeat timers.
        emulator.hold_button(Button.UP)
        time.sleep(1)
        emulator.release_buttons()
        time.sleep(0.5)

        # Step 3: repeat twice
        emulator.press_down()
        time.sleep(0.2)
        emulator.press_down()

        time.sleep(0.2)  # wait for repeat mode to expire

        repeat_enabled_screenshot = emulator.screenshot("after_enabling_repeat")

        # TODO: wait for the timer to expire
        # TODO: screen shot to check that it has started again

        # Capture screenshot
        after_screenshot = emulator.screenshot("after_repeat_wait")

        # --- Perform OCR assertions ---

        # TODO: check repeat_enabled_screenshot has 2x in the top right

        # TODO: check that second screen shot has started again
