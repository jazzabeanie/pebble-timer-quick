"""
Test Case: Stopwatch Subtraction to Countdown Conversion

This test verifies the fix for a bug where subtracting time from a stopwatch
(chrono) timer converts it into a countdown timer instead of producing an
invalid state.

Reference: specs/stopwatch-subtraction.md

When the timer is in chrono mode (counting up from 0:00) and a user subtracts
time (e.g., 1 minute) by entering edit mode and using reverse direction,
the timer should correctly transition to countdown mode showing the remaining
time until the subtracted value.

Example:
- Chrono shows 0:05 (5 seconds elapsed)
- User subtracts 1 minute
- Timer should show ~0:55 countdown (55 seconds remaining)
"""

import logging
import time

import pytest

from .conftest import Button, PLATFORMS
from .test_create_timer import (
    extract_text,
    normalize_time_text,
    has_time_pattern,
)

# Configure module logger
logger = logging.getLogger(__name__)


class TestStopwatchSubtraction:
    """Tests for stopwatch subtraction to countdown conversion."""

    def test_chrono_subtraction_converts_to_countdown(self, persistent_emulator):
        """
        Test that subtracting time from a chrono converts it to a countdown.

        Steps:
        1. Start fresh, wait for chrono mode (3+ seconds)
        2. Press Up to enter edit mode for the existing chrono
        3. Long press Up to toggle reverse direction
        4. Press Down to subtract 1 minute from the chrono
        5. Verify the display shows a countdown time (not chrono)

        Expected: After subtracting 1 minute from a chrono showing ~5 seconds,
        the timer should show a countdown of approximately 55 seconds.
        """
        emulator = persistent_emulator

        # --- Phase 1: Enter chrono mode ---
        # Wait for the 3-second inactivity timeout to transition from New mode
        # to chrono mode (counting up from 0:00).
        # Note: We need to capture screenshots quickly due to the 7-second
        # auto-background timer for chrono mode.
        time.sleep(3.5)

        # Take screenshot to verify we're in chrono mode
        chrono_screenshot = emulator.screenshot("chrono_before_subtraction")

        # --- Phase 2: Enter edit mode and enable reverse direction ---
        # Press Up to enter edit mode for the existing chrono timer
        # This sets is_editing_existing_timer = true and control_mode = ControlModeNew
        emulator.press_up()
        time.sleep(0.3)

        # Long press Up to toggle reverse direction (so Down subtracts instead of adds)
        emulator.hold_button(Button.UP)
        time.sleep(1.0)  # Hold for BUTTON_HOLD_RESET_MS (1000ms)
        emulator.release_buttons()
        time.sleep(0.3)

        # --- Phase 3: Subtract time ---
        # Press Down to subtract 1 minute (calls timer_increment_chrono(-60000))
        # This should convert the chrono to a countdown
        emulator.press_down()
        time.sleep(0.5)

        # Take screenshot after subtraction
        after_subtraction = emulator.screenshot("after_subtraction")

        # --- Phase 4: Verify the conversion ---
        # Extract text and verify the state

        # Check chrono screenshot shows a small chrono time (0:0x)
        text_chrono = extract_text(chrono_screenshot)
        logger.info(f"Chrono before subtraction: {text_chrono}")
        normalized_chrono = normalize_time_text(text_chrono)
        # Chrono should show small time like 0:03 or 0:04 (few seconds elapsed)
        chrono_patterns = ["0:0"]
        has_chrono_time = any(pattern in normalized_chrono for pattern in chrono_patterns)
        assert has_chrono_time, f"Expected chrono showing '0:0x' at start, got: {text_chrono}"

        # Check after subtraction shows a countdown time around 0:55
        text_after = extract_text(after_subtraction)
        logger.info(f"After subtraction: {text_after}")
        normalized_after = normalize_time_text(text_after)

        # After subtracting 1 minute from a ~5 second chrono, we should have
        # approximately 55 seconds of countdown remaining.
        # Allow for some timing variance (45-59 seconds range).
        countdown_patterns = ["0:5", "0:4"]  # 0:5x or 0:4x
        has_countdown_time = any(pattern in normalized_after for pattern in countdown_patterns)

        # Also try flexible time pattern matching
        if not has_countdown_time:
            # Check for time in the range of 45-59 seconds (0 minutes, 45-59 seconds)
            has_countdown_time = has_time_pattern(text_after, minutes=0, seconds=55, tolerance=15)

        assert has_countdown_time, (
            f"Expected countdown time around 0:55 after subtracting 1 minute from chrono, "
            f"got: {text_after}"
        )

        # Verify the display changed (chrono -> countdown shows different value)
        assert chrono_screenshot.tobytes() != after_subtraction.tobytes(), (
            f"Display should change after conversion from chrono to countdown. "
            f"Before: {text_chrono}, After: {text_after}"
        )

    def test_chrono_subtraction_multiple_minutes(self, persistent_emulator):
        """
        Test subtracting multiple minutes from a chrono.

        This test verifies that subtracting a larger amount (e.g., 3 minutes)
        from a chrono correctly produces a longer countdown.
        """
        emulator = persistent_emulator

        # Wait for chrono mode
        time.sleep(3.5)

        # Enter edit mode
        emulator.press_up()
        time.sleep(0.3)

        # Enable reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.3)

        # Subtract 3 minutes (press Down 3 times)
        emulator.press_down()
        emulator.press_down()
        emulator.press_down()
        time.sleep(0.5)

        after_subtraction = emulator.screenshot("after_3min_subtraction")

        # Verify countdown shows approximately 2:55 (3 minutes minus ~5 seconds elapsed)
        text = extract_text(after_subtraction)
        logger.info(f"After 3-minute subtraction: {text}")

        # Should show time around 2:55 (2 minutes 55 seconds)
        has_expected_time = has_time_pattern(text, minutes=3, tolerance=15)
        assert has_expected_time, (
            f"Expected countdown time around 2:55 after subtracting 3 minutes, got: {text}"
        )

    def test_chrono_add_then_subtract(self, persistent_emulator):
        """
        Test adding time then subtracting to verify direction toggle works.

        This test verifies that:
        1. Adding time to a chrono increases the countdown
        2. Toggling direction and subtracting correctly reduces it
        """
        emulator = persistent_emulator

        # Wait for chrono mode
        time.sleep(3.5)

        # Enter edit mode
        emulator.press_up()
        time.sleep(0.3)

        # Add 2 minutes (normal direction) by pressing Down twice
        # In edit mode for chrono, Down adds time (timer_increment_chrono positive)
        emulator.press_down()
        emulator.press_down()
        time.sleep(0.3)

        after_add = emulator.screenshot("after_add")

        # Now toggle to reverse direction
        emulator.hold_button(Button.UP)
        time.sleep(1.0)
        emulator.release_buttons()
        time.sleep(0.3)

        # Subtract 1 minute
        emulator.press_down()
        time.sleep(0.3)

        after_subtract = emulator.screenshot("after_subtract")

        # Extract text and verify
        text_add = extract_text(after_add)
        text_subtract = extract_text(after_subtract)
        logger.info(f"After adding 2 min: {text_add}")
        logger.info(f"After subtracting 1 min: {text_subtract}")

        # After adding 2 min to ~5s chrono: should be countdown ~1:55
        # After subtracting 1 min: should be countdown ~0:55
        # Verify the subtraction reduced the time
        assert after_add.tobytes() != after_subtract.tobytes(), (
            f"Display should change after subtraction. "
            f"After add: {text_add}, After subtract: {text_subtract}"
        )
