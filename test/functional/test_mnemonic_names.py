"""
Functional tests for mnemonic timer names in the Timer List view.

Verifies that line 1 of each existing timer entry in the Timer List
displays a mnemonic name (adjective + noun) rather than a duration string.
"""

import re
import time
import pytest

from .conftest import (
    EmulatorHelper,
    LogCapture,
)

# Pattern for a duration string (e.g. "0:05:00" or "00:05:00")
DURATION_PATTERN = re.compile(r'^\d{1,2}:\d{2}:\d{2}')

# Pattern for a mnemonic name: one or two lowercase words (with optional numeric suffix)
MNEMONIC_PATTERN = re.compile(r'^[a-z]')


def _create_timer_and_background(emulator: EmulatorHelper, platform: str):
    """Create a 5-minute countdown timer and background the app."""
    capture = LogCapture(platform)
    capture.start()
    time.sleep(0.5)

    emulator.press_select()
    state = capture.wait_for_state(event="button_select", timeout=5.0)
    capture.stop()
    assert state is not None, "No button_select event received"

    time.sleep(3.5)
    emulator.press_back()
    time.sleep(0.5)


class TestMnemonicNames:
    """Tests that the Timer List shows mnemonic names on line 1."""

    def test_timer_list_shows_name_not_duration(self, emulator):
        """
        5.5: Line 1 of an existing timer entry in the Timer List shows the mnemonic
        name, not a duration string like '00:05:00'.

        Flow:
        1. Create a timer and background the app
        2. Re-launch → Timer List appears
        3. Verify name0 in the log is a mnemonic name, not a duration string
        """
        platform = emulator.platform

        _create_timer_and_background(emulator, platform)

        capture = LogCapture(platform)
        capture.start()
        emulator.open_app_via_menu()
        time.sleep(1.0)

        state = capture.wait_for_state(event="timer_list_show", timeout=5.0)
        capture.stop()

        assert state is not None, (
            "Timer List was not shown. "
            f"All logs: {capture.get_all_logs()}"
        )

        name0 = state.get("name0", "")
        assert name0 != "", (
            f"name0 field is empty in timer_list_show state: {state}"
        )
        assert not DURATION_PATTERN.match(name0), (
            f"Line 1 still shows a duration string '{name0}' — mnemonic name not applied. "
            f"Full state: {state}"
        )
        assert MNEMONIC_PATTERN.match(name0), (
            f"name0 '{name0}' does not look like a mnemonic name. Full state: {state}"
        )
