"""
Functional tests for voice-rename offline feedback.

When the user starts a voice rename (Up+Back chord in EditSec) while the phone is
disconnected, the app shows a no-phone-connected icon (plus three short vibration
pulses) instead of silently failing, then auto-dismisses back to EditSec after ~1s
with the timer name unchanged. When the phone is connected, the chord starts
dictation as usual and no connection feedback is shown.

These behaviors only exist on PBL_MICROPHONE platforms (everything except aplite).
"""

import logging
import os
import time

import pytest

from .conftest import (
    Button,
    LogCapture,
    assert_mode,
)

logger = logging.getLogger(__name__)

# AppMessage key for the voice_naming_enabled setting (see src/settings.c).
APPMSG_KEY_VOICE_NAMING_ENABLED = 14

# These tests require disconnecting Bluetooth (`pebble emu-bt-connection no`) AND
# driving buttons in the same session. In the current emulator/pypkjs harness,
# toggling the BT connection corrupts the QEMU button channel
# (`Exception decoding QemuInboundPacket.footer`) so button presses stop
# registering and the emulator wedges. The tests below encode the intended
# behavior and will run on a harness that supports BT-toggle + button input;
# set RUN_BT_TOGGLE_TESTS=1 to opt in there. They are skipped by default.
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BT_TOGGLE_TESTS") != "1",
    reason="Harness cannot toggle Bluetooth and drive buttons in the same session "
           "(emu-bt-connection corrupts the QEMU button channel). "
           "Set RUN_BT_TOGGLE_TESTS=1 to run on a supporting harness.",
)


class TestVoiceRenameOffline:
    """Up+Back voice rename gives feedback when the phone is disconnected."""

    def _skip_if_no_microphone(self, emulator):
        if emulator.platform == "aplite":
            pytest.skip("Voice rename requires PBL_MICROPHONE (not on aplite)")

    def _enter_edit_sec_with_voice(self, emulator, capture):
        """Enable voice naming and enter EditSec mode.

        Enabling the setting and toggling BT takes long enough that the app may
        have auto-transitioned New -> Counting. Press Up first (Counting -> New),
        then long-press Select (New -> EditSec), per the documented workflow.
        """
        # Enable voice naming via AppMessage (requires the phone connected).
        emulator.set_bt_connection(True)
        emulator.send_app_message_int(APPMSG_KEY_VOICE_NAMING_ENABLED, 1)
        time.sleep(0.5)

        # Press Up to ensure we are in New mode, then long-press Select for EditSec.
        capture.clear_state_queue()
        emulator.press_up()
        assert capture.wait_for_state(event="button_up", timeout=5.0) is not None
        emulator.hold_button(Button.SELECT)
        state = capture.wait_for_state(event="long_press_select", timeout=5.0)
        emulator.release_buttons()
        assert state is not None, "Did not reach EditSec via long-press Select"
        assert_mode(state, "EditSec")

    def test_offline_rename_shows_no_phone_feedback(self, persistent_emulator):
        """Disconnected: the chord shows the no-phone icon and does not rename."""
        emulator = persistent_emulator
        self._skip_if_no_microphone(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)

        try:
            self._enter_edit_sec_with_voice(emulator, capture)

            # Disconnect the phone, then start the voice rename.
            emulator.set_bt_connection(False)
            capture.clear_state_queue()
            emulator.press_up_back_chord()

            # The no-phone feedback event should fire; dictation is NOT started.
            state = capture.wait_for_state(event="voice_no_phone", timeout=5.0)
            assert state is not None, "No no-phone feedback shown while disconnected"
            assert_mode(state, "EditSec")
        finally:
            # Restore the connected state for subsequent tests in the module.
            emulator.set_bt_connection(True)
            capture.stop()

    def test_connected_rename_shows_no_feedback(self, persistent_emulator):
        """Connected: the chord starts dictation; no connection feedback appears."""
        emulator = persistent_emulator
        self._skip_if_no_microphone(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)

        try:
            self._enter_edit_sec_with_voice(emulator, capture)

            # Phone is connected; the chord should proceed to dictation.
            emulator.set_bt_connection(True)
            capture.clear_state_queue()
            emulator.press_up_back_chord()

            # No no-phone feedback event should be emitted when connected.
            state = capture.wait_for_state(event="voice_no_phone", timeout=2.0)
            assert state is None, "No-phone feedback shown even though phone is connected"
        finally:
            capture.stop()

    def test_offline_feedback_auto_dismisses(self, persistent_emulator):
        """Disconnected: the no-phone icon auto-dismisses to EditSec after ~1s."""
        emulator = persistent_emulator
        self._skip_if_no_microphone(emulator)
        capture = LogCapture(emulator.platform)
        capture.start()
        time.sleep(1.0)

        try:
            self._enter_edit_sec_with_voice(emulator, capture)

            emulator.set_bt_connection(False)
            capture.clear_state_queue()
            emulator.press_up_back_chord()

            shown = capture.wait_for_state(event="voice_no_phone", timeout=5.0)
            assert shown is not None, "No-phone feedback was never shown"

            # Within ~1s the feedback should auto-dismiss back to EditSec.
            dismissed = capture.wait_for_state(event="voice_no_phone_dismiss", timeout=3.0)
            assert dismissed is not None, "No-phone feedback did not auto-dismiss"
            assert_mode(dismissed, "EditSec")
        finally:
            emulator.set_bt_connection(True)
            capture.stop()
