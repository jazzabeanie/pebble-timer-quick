## Context

Voice rename (`PBL_MICROPHONE` only) launches an SDK dictation session from the Up+Back chord in `ControlModeEditSec` (`src/main.c` `prv_start_voice_rename`, ~line 347). The session has `dictation_session_enable_error_dialogs(true)` set, which is supposed to surface connectivity problems. In practice, starting a rename in airplane mode produces no visible feedback — the user sees nothing happen and has no way to know a phone connection is required.

Separately, the transcription is cleaned by `timer_set_name()` (`src/timer.c`, ~line 354), which trims leading/trailing whitespace and truncates at a word boundary to fit the 19-char name field. Punctuation at the edges of a transcription (e.g. "...pasta!") is currently preserved.

## Goals / Non-Goals

**Goals:**
- Give the user clear, immediate feedback when a rename is attempted while the phone is disconnected.
- Detect the disconnected state proactively via `connection_service_peek_pebble_app_connection()` before starting dictation.
- Strip all leading/trailing non-alphanumeric characters (whitespace, punctuation, symbols) from transcriptions while preserving interior characters.

**Non-Goals:**
- Changing dictation behavior when the phone IS connected (existing flow unchanged).
- Live connection monitoring / auto-retry when the phone reconnects.
- Localization or stripping of non-ASCII alphanumerics beyond what `isalnum`-style checks cover.

## Decisions

### Decision: Pre-check connection before starting dictation
In `prv_start_voice_rename()`, call `connection_service_peek_pebble_app_connection()` first. If it returns `false`, show offline feedback and return without creating/starting the dictation session. This is more reliable than depending on the SDK error dialog, which is the observed silent-failure path in airplane mode.

*Alternative considered:* rely solely on `dictation_session_enable_error_dialogs`. Rejected — it's the current behavior and is the bug.

### Decision: Render the no-phone feedback ourselves
The Pebble app SDK does not expose a guaranteed public bitmap constant for the "phone disconnected" graphic. To match the app's existing icon pattern, bundle a small no-phone bitmap in the app's resources (alongside the existing `RESOURCE_ID_IMAGE_*` icons in `resources/images`) and display it for ~1 second, then auto-dismiss back to `ControlModeEditSec`. Display mechanism follows the app's existing window/layer conventions; the 1-second dismissal uses an `app_timer`.

### Decision: Three short vibration pulses on disconnect
On the disconnected path, emit three short vibration pulses to draw attention to the on-screen icon. Use a custom `VibePattern` of three short on/off segments via `vibes_enqueue_custom_pattern()` (rather than `vibes_short_pulse()` ×3, which does not reliably queue distinct pulses). The vibration fires once when the icon is shown.

*Alternative considered:* a text-only message. Rejected — the user specifically asked for an icon, and the app is icon-driven elsewhere. *Open question below covers verifying whether a usable SDK resource exists, which would let us drop the bundled asset.*

### Decision: Generalize trimming to non-alphanumeric in `timer_set_name()`
Replace the whitespace-only character checks in the leading/trailing trim loops with an alphanumeric test (`(c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')`) — i.e. trim anything that is not alphanumeric. Interior characters and the existing word-boundary truncation are unchanged. A transcription with no alphanumeric characters trims to an empty string.

*Alternative considered:* a curated punctuation set (`. , ! ? ; :`). Rejected — user asked to strip all non-alphanumeric edge characters, which is simpler and more predictable.

## Risks / Trade-offs

- [Bundled bitmap adds resource weight on emery] → The asset is tiny and only compiled under `PBL_MICROPHONE`.
- [Empty name after punctuation-only transcription] → Acceptable and specified; matches existing "trim to empty" edge behavior and is rare in practice. Confirm downstream code (list view, naming fallback) renders an empty name gracefully.
- [`connection_service_peek_*` reflects app-connection, not raw BT] → This is the correct signal for dictation, which needs the phone app; documented in the spec scenario.

## Open Questions

- Does the installed SDK expose a reusable disconnected/phone graphic (e.g. via a status or dialog resource) that would avoid bundling our own bitmap? Verify during implementation; if yes, prefer it.
