import logging
import pytest
import time

from .conftest import (
    Button,
    LogCapture,
    assert_mode,
    assert_backlight,
    assert_vibrating,
)

# Configure module logger
logger = logging.getLogger(__name__)

class TestBacklight:
    """Tests for automatic backlight control."""

    def test_backlight_on_in_edit_mode(self, persistent_emulator):
        """Test 2: Backlight turns on when entering edit mode."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for log connection
        time.sleep(1.0)
        capture.clear_state_queue()

        # Initial state (ControlModeNew) - backlight should be ON
        # Note: Init state might have been missed, so we check after a button press
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        
        assert state is not None
        assert_mode(state, "New")
        assert_backlight(state, True)

        capture.stop()

    def test_backlight_off_in_counting_mode(self, persistent_emulator):
        """Test 3: Backlight turns off when entering counting mode."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for log connection
        time.sleep(1.0)
        capture.clear_state_queue()

        # Set a 20-minute timer (adds time but stays in New mode)
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        assert_backlight(state, True)

        # Wait for mode transition to Counting
        state = capture.wait_for_state(event="mode_change", timeout=10.0)
        
        assert state is not None
        assert_mode(state, "Counting")
        assert_backlight(state, False)

        capture.stop()

    def test_backlight_on_during_alarm(self, persistent_emulator):
        """Test 1: Backlight turns on when alarm starts."""
        emulator = persistent_emulator
        if emulator.platform == "aplite":
            pytest.xfail("Aplite frequently crashes due to memory pressure during this sequence.")
        capture = LogCapture(emulator.platform)
        capture.start()

        # Wait for log connection (more time for aplite)
        is_aplite = emulator.platform == "aplite"
        wait_time = 3.0 if is_aplite else 1.0
        time.sleep(wait_time)
        capture.clear_state_queue()

        # Set a very short timer
        # 1. Wait for chrono mode, pause, then enter EditSec via long-press Select
        time.sleep(3.5)
        emulator.press_select()  # Pause chrono
        time.sleep(0.3)
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        assert capture.wait_for_state(event="long_press_select", timeout=10.0 if is_aplite else 5.0) is not None

        # 2. Press Select twice to add 10 seconds (5s each)
        emulator.press_select()
        assert capture.wait_for_state(event="button_select", timeout=10.0 if is_aplite else 5.0) is not None
        emulator.press_select()
        assert capture.wait_for_state(event="button_select", timeout=10.0 if is_aplite else 5.0) is not None

        # 3. Wait for mode transition to Counting
        assert capture.wait_for_state(event="mode_change", timeout=15.0 if is_aplite else 10.0) is not None

        # 4. Start the timer (it stays paused for sub-minute timers from EditSec)
        emulator.press_select()
        assert capture.wait_for_state(event="button_select", timeout=10.0 if is_aplite else 5.0) is not None

        # 5. Wait for alarm to start
        state = capture.wait_for_state(event="alarm_start", timeout=25.0 if is_aplite else 20.0)
        assert state is not None
        assert_vibrating(state, True)
        assert_backlight(state, True)

        # 6. Silence alarm with Back button
        emulator.press_back()
        state = capture.wait_for_state(event="button_back", timeout=10.0)
        assert state is not None
        assert_vibrating(state, False)
        # Back button in counting mode (not edit) should turn off backlight
        assert_backlight(state, False)

        capture.stop()

    def test_backlight_on_in_edit_sec_mode(self, persistent_emulator):
        """Test: Backlight turns on in EditSec mode."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # Enter EditSec mode
        emulator.hold_button(Button.SELECT)
        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        
        assert state is not None
        assert_mode(state, "EditSec")
        assert_backlight(state, True)

        capture.stop()

    def test_backlight_on_in_edit_repeat_mode(self, persistent_emulator):
        """Test: Backlight turns on in EditRepeat mode."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # 1. Set a timer (requires mode change to Counting)
        emulator.press_up()
        capture.wait_for_state(event="mode_change", timeout=10.0)

        # 2. Long-press Up to enter EditRepeat mode
        emulator.hold_button(Button.UP)
        state = capture.wait_for_state(event="long_press_up", timeout=5.0)
        
        assert state is not None
        assert_mode(state, "EditRepeat")
        assert_backlight(state, True)

        capture.stop()

    def test_backlight_stays_on_when_silencing_to_edit_mode(self, persistent_emulator):
        """Test 7: Backlight stays on when alarm is silenced by entering edit mode."""
        emulator = persistent_emulator
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)
        capture.clear_state_queue()

        # 1. Set a short timer and wait for alarm
        emulator.hold_button(Button.SELECT)
        time.sleep(1)
        emulator.release_buttons()
        capture.wait_for_state(event="long_press_select")
        emulator.press_select()
        capture.wait_for_state(event="mode_change", timeout=10.0)
        emulator.press_select() # Start it
        capture.wait_for_state(event="alarm_start", timeout=15.0)

        # 2. Press Up to silence alarm and enter edit mode
        emulator.press_up()
        state = capture.wait_for_state(event="button_up", timeout=5.0)
        
        assert state is not None
        assert_vibrating(state, False)
        assert_mode(state, "New")
        assert_backlight(state, True)

        capture.stop()
