## Context

The Pebble SDK 4.x ships a `DictationSession` API (in `pebble.h` for the `emery` platform) that opens the microphone, streams audio to Nuance's cloud STT service, and returns a `char *` transcription via callback. This is the only voice-input mechanism available.

The app already handles per-timer naming via the mnemonic system (`src/mnemonic.c`). Timer names are stored in `timer_slots[i].name` — a `char[20]` field (19 usable bytes). Edit mode (`ControlModeEditSec`) is the natural hook point for voice rename, since it is where the user is already actively configuring a timer.

The standard Pebble click API has no simultaneous-button concept. Raw click handlers (`window_raw_click_subscribe`) fire on individual button-down and button-up events, making it possible to track concurrent holds in firmware. The `BUTTON_ID_BACK` raw handler requires careful handling because Back navigates up by default — we must intercept it before the system processes it (the SDK allows this in raw handlers).

## Goals / Non-Goals

**Goals:**
- Allow users to name a timer by voice while in `ControlModeEditSec`, triggered by holding Up + Back simultaneously.
- Gate the feature behind a `voice_naming_enabled` setting (default off).
- Restrict to `emery` platform using `PBL_IF_MICROPHONE_ELSE` / `#ifdef PBL_MICROPHONE`.
- Truncate transcription to 19 chars and trim whitespace before saving.
- Persist the new name in the existing `timer_slots[i].name` field.

**Non-Goals:**
- Voice control of timer duration or mode.
- Voice input on non-microphone platforms (aplite, basalt, chalk, diorite, gabbro).
- Offline / on-device STT (not available in this SDK).
- Confirmation UI for the transcribed name (we rely on the SDK's built-in confirmation dialog).

## Decisions

### D1: Gesture — simultaneous Up + Back hold via raw click handlers

**Decision:** Use `window_raw_click_subscribe` on both `BUTTON_ID_UP` and `BUTTON_ID_BACK` in `ControlModeEditSec`. Track `s_up_held` and `s_back_held` booleans. When both are true at the same time, trigger dictation.

**Alternatives considered:**
- *Double-tap Select in edit mode* — conflicts with existing Select behavior (advance seconds digit).
- *Long-press Up + Back chord via a dedicated SDK API* — no such API exists in SDK 4.x.
- *A new dedicated button combo (e.g., double-tap Back)* — multi-click on Back is disallowed by the SDK ("you cannot set a repeating, long or raw click handler on the back button because a long press on back exits the app"). Actually raw is allowed; the restriction is on long_click for back.

**Note:** Raw click intercepts Back before the system exit handler. We must call `window_stack_pop` explicitly if the user taps Back without Up being held (to preserve normal back navigation).

### D2: Platform guard — `PBL_IF_MICROPHONE_ELSE`

**Decision:** Wrap all dictation code in `#ifdef PBL_MICROPHONE`. The `voice_naming_enabled` setting is always synced from phone, but the raw-click handlers and dictation session are only registered/created on emery.

**Alternatives considered:**
- *Runtime check* — no reliable runtime API to detect microphone presence; compile-time guard is the Pebble-idiomatic approach.

### D3: Name storage — write directly to `timer_slots[i].name` via new `timer_set_name()`

**Decision:** Add `void timer_set_name(uint8_t idx, const char *name)` to `timer.c`/`timer.h`. This truncates to 19 chars, trims whitespace, and calls `timer_save()` to persist.

**Alternatives considered:**
- *Write name field directly in `main.c`* — breaks encapsulation; timer persistence logic lives in `timer.c`.

### D4: Transcription confirmation — enable SDK confirmation dialog

**Decision:** Call `dictation_session_enable_confirmation(session, true)` so the user can accept or re-record before the name is committed.

**Rationale:** Names are persistent. A confirmation step prevents accidental bad transcriptions. The SDK dialog is free UI.

### D5: Settings key — APPMSG key 14 for `voice_naming_enabled`

**Decision:** Use key `14` (next in sequence after key `13` = `multiple_timers_enabled`). Default `false` (opt-in).

## Risks / Trade-offs

- **[Risk] Dictation requires phone + internet connectivity** → Mitigation: SDK error dialogs handle this gracefully (`dictation_session_enable_error_dialogs(session, true)`). No special code needed.
- **[Risk] Raw Back handler suppresses system back navigation** → Mitigation: In the raw up-handler, only suppress Back exit if Up is also held; otherwise call `window_stack_pop` on Back-up to restore normal navigation.
- **[Risk] 19-char limit silently truncates long phrases** → Mitigation: `timer_set_name` truncates at a word boundary where possible, and the SDK confirmation dialog shows the full transcription so the user sees it before committing.
- **[Risk] `DictationSession` lifecycle in C — must destroy before window is popped** → Mitigation: Destroy session in the `ControlModeEditSec` unload/deinit hook.

## Open Questions

- Should the settings toggle be hidden on non-emery builds (JS can't detect platform), or always shown with a note that it only applies to Pebble 2? → Recommend: always show, add a help text line "Pebble 2 only".
- Word-boundary truncation vs. hard char truncation at 19 bytes — is a truncated word better or worse than a shorter clean name? → Default to word-boundary truncation (stop before the word that would overflow).
