## 1. Settings — add voice_naming_enabled flag

- [x] 1.1 Add `APPMSG_KEY_VOICE_NAMING_ENABLED 14` constant and `voice_naming_enabled` field to `AppSettings` struct in `src/settings.c`
- [x] 1.2 Add `HANDLE(APPMSG_KEY_VOICE_NAMING_ENABLED, voice_naming_enabled)` in `prv_inbox_received` and default `false` in `settings_init`
- [x] 1.3 Expose `bool settings_get_voice_naming_enabled(void)` in `src/settings.h` and implement in `src/settings.c`
- [x] 1.4 Bump `PERSIST_SETTINGS_VERSION` and update `settings_init` defaults block
- [x] 1.5 Add `voice_naming_enabled` toggle to the General section of the settings HTML in `src/js/pebble-js-app.js` (label: "Voice Naming (Pebble 2 only)", default off) and wire it in the `save()` function and `sendSettingsToWatch`

## 2. Timer — expose timer_set_name()

- [x] 2.1 Add `void timer_set_name(uint8_t idx, const char *name)` declaration to `src/timer.h`
- [x] 2.2 Implement `timer_set_name` in `src/timer.c`: trim leading/trailing whitespace, truncate at word boundary to fit 19 chars (hard-truncate if single token > 19), write to `timer_slots[idx].name`, call `timer_save()`

## 3. Edit mode — Up+Back chord detection

Note: No raw Back subscription is needed (see design.md D1). `s_up_held` is already tracked via the existing raw Up handler. The chord is detected in `prv_back_click_handler`.

- [x] 3.1 In `src/main.c`, inside `#ifdef PBL_MICROPHONE`, add a `DictationSession *s_dictation_session` pointer (the `s_up_held` and `s_up_chord_consumed` booleans from the POC are already present and can be reused)
- [x] 3.2 At the top of `prv_back_click_handler`, inside `#ifdef PBL_MICROPHONE`, add: if `(control_mode == ControlModeEditSec || control_mode == ControlModeNew) && s_up_held && settings_get_voice_naming_enabled()`: set `s_up_chord_consumed = true`, call `prv_start_voice_rename()`, return
- [x] 3.3 Remove the POC flash/vibe chord handlers in `ControlModeEditSec` (Up+Down chord) and `ControlModeNew` (Up+Back chord) once the real dictation feature is wired up

## 4. Dictation session lifecycle

- [x] 4.1 Implement `prv_start_voice_rename()` in `src/main.c` (`#ifdef PBL_MICROPHONE`): create `DictationSession` with 64-byte buffer, enable confirmation and error dialogs, call `dictation_session_start`
- [x] 4.2 Implement `prv_dictation_callback(DictationSession *, DictationSessionStatus, char *, void *)`: on `DictationSessionStatusSuccess`, call `timer_set_name(active_idx, transcription)`; on any failure, do nothing
- [x] 4.3 Destroy `s_dictation_session` in the `ControlModeEditSec` window unload handler; set pointer to NULL after destroy

## 5. Spec files — write failing tests first

- [x] 5.1 Write a failing functional test in `test/functional/` that verifies `timer_set_name` truncates long text at a word boundary
- [x] 5.2 Write a failing functional test that verifies `timer_set_name` hard-truncates a single oversized token
- [x] 5.3 Write a failing functional test that verifies a failed dictation leaves the timer name unchanged
- [x] 5.4 Run tests and confirm they fail (`python -m pytest -v --platform=basalt` in `test/functional/`)

## 6. Implementation verification

- [x] 6.1 Build for emery platform and confirm no compile errors: `pebble build`
- [x] 6.2 Build for basalt (non-microphone) and confirm voice code is excluded: `pebble build --platform basalt`
- [x] 6.3 Re-run all tests and confirm they pass
- [x] 6.4 Update `docs/button-functions.md` with the new Up+Back chord gesture for `ControlModeEditSec` (emery only, `voice_naming_enabled`)
