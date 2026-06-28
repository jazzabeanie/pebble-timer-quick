## Why

Two rough edges in the voice rename feature: (1) starting a voice rename while the phone is disconnected (e.g. airplane mode) silently does nothing, leaving the user with no idea why — this is a bug; and (2) speech-to-text transcriptions can include leading/trailing punctuation (e.g. "...pasta!"), which currently gets saved verbatim instead of being cleaned up like surrounding whitespace already is.

## What Changes

- When the user initiates voice rename (Up+Back chord in `ControlModeEditSec`) while the phone is not connected, the system shows clear visual feedback (the SDK's no-phone-connected graphic) instead of silently failing.
- The connection state is checked up front via `connection_service_peek_pebble_app_connection()`; dictation is only started when connected.
- `timer_set_name()` strips ALL leading and trailing non-alphanumeric characters (punctuation, symbols) from a transcription, extending the existing whitespace-trimming behavior. Interior characters are untouched.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `voice-timer-rename`: Adds a requirement for offline/disconnected feedback when starting a rename, and broadens the name-trimming requirement from whitespace-only to all leading/trailing non-alphanumeric characters.

## Impact

- `src/main.c`: `prv_start_voice_rename()` (connection pre-check + feedback), and supporting feedback UI.
- `src/timer.c`: `timer_set_name()` trimming logic.
- Tests: `test/functional/` (offline feedback + punctuation behavior), `test/` (unit tests for `timer_set_name()` trimming).
- SDK APIs: `connection_service_peek_pebble_app_connection()`; existing `dictation_session_*` usage unchanged.
