## Why

Timer names are currently generated automatically from a mnemonic system and are immutable — there's no way to give a timer a meaningful, human-chosen name. On Pebble hardware with a microphone (Pebble 2 / emery platform), the Dictation API can capture voice input, enabling a fast eyes-free rename directly from edit mode.

## What Changes

- Add a `voice_naming_enabled` boolean setting (default `false`) to the settings page, visible only in the Emery/voice-capable platform build or always shown but functionally no-ops on non-emery hardware.
- In `ControlModeEditSec`, detect a simultaneous Up + Back button hold gesture using raw click handlers; when `voice_naming_enabled` is true, launch a `DictationSession`.
- On successful transcription, truncate the result to 19 characters (the `name` field limit), trim leading/trailing whitespace, and write it into the active timer's `name` field.
- The mnemonic name immutability requirement is relaxed: a voice-captured name replaces the mnemonic name, and that new name persists.
- Feature is conditionally compiled for `emery` platform only using `PBL_IF_MICROPHONE_ELSE`.

## Capabilities

### New Capabilities
- `voice-timer-rename`: User can hold Up+Back simultaneously in edit mode to trigger voice dictation; the transcribed text becomes the timer's name. Gated by `voice_naming_enabled` setting. Emery platform only.

### Modified Capabilities
- `mnemonic-naming`: The immutability requirement is relaxed — a voice-provided name may replace the mnemonic name. The mnemonic name remains the default but is no longer permanent.

## Impact

- `src/settings.c` / `src/settings.h`: new `voice_naming_enabled` field and getter; new `APPMSG_KEY_VOICE_NAMING_ENABLED` (key 14)
- `src/js/pebble-js-app.js`: new toggle in the General section of the settings HTML page
- `src/main.c`: new raw click handlers for Up and Back in `ControlModeEditSec`; dictation session lifecycle management; `#ifdef PBL_MICROPHONE` guards
- `src/timer.c` / `src/timer.h`: expose a `timer_set_name(uint8_t idx, const char *name)` function to allow external rename
- Requires `capabilities` in `appinfo.json` to declare `microphone` or rely on platform guard
- No new dependencies; `DictationSession` API is already part of the Pebble SDK 4.x for emery
