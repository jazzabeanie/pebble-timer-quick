## Context

Two independent fixes are bundled here because both are small and neither touches the other's code.

**Voice rename.** `prv_start_voice_rename` (`src/main.c:584`) creates a `DictationSession` with `dictation_session_enable_confirmation(session, true)`, so the SDK shows its own review screen and `prv_dictation_callback` (`src/main.c:554`) only runs after the user accepts or rejects. The SDK's dictation surface (`pebble.h:2067-2157` in SDK 4.9.169) is exactly: create / destroy / start / stop / enable_confirmation / enable_error_dialogs plus one completion callback. There is **no** hook for "transcription arrived, awaiting confirmation" — so as long as the built-in confirmation screen is used, the app cannot know that moment exists, let alone vibrate at it.

**Menu icon.** `appinfo.json` declares `images/timer_icon.png` as `IMAGE_ICON` with `"menuIcon": true`, resolved per platform to `resources/images/timer_icon~color.png` (colour) and `~bw.png` (B/W). Pixel inspection of the colour variant: every non-transparent pixel is RGB `(255,255,255)` with varying alpha — pure white artwork on transparency. The launcher does not recolour menu icons, so on its white unselected rows the icon vanishes; it only appears on the highlighted row. The `~bw.png` variant is the opposite: fully opaque, black artwork on a solid white box (no alpha at all), which paints a white rectangle rather than compositing.

Constraints: the voice path is `#ifdef PBL_MICROPHONE`, so aplite's RAM ceiling is not a factor. The emulator cannot exercise dictation (no microphone / no phone transcription), so verification of the voice change is unit-level plus manual on-watch confirmation.

## Goals / Non-Goals

**Goals:**
- A single short vibration the instant a voice transcription is ready, with the name applied immediately.
- A distinct three-pulse vibration when a dictation attempt fails, so success and failure are distinguishable without looking at the watch.
- A launcher icon that reads on both selected and unselected launcher rows, on colour and B/W platforms.
- Automated regression coverage for both, at the level each is actually testable.

**Non-Goals:**
- Any in-app confirmation/review UI for transcriptions. A wrong transcription is fixed by repeating the rename gesture — explicitly the user's call.
- Changing the rename gesture, the phone-disconnected feedback, or name truncation/trimming rules.
- Redesigning the icon artwork. Only its rendering polarity/alpha changes; the glyph stays the same.
- Touching any other icon resource (action-bar, increment icons, etc.).

## Decisions

### Decision 1: Disable the SDK confirmation dialog and commit on the result callback

`dictation_session_enable_confirmation(s_dictation_session, false)`. The callback then fires as soon as transcription completes, which is precisely the "waiting for confirmation" moment the user wants marked — the wait itself is removed. In `prv_dictation_callback`, on `DictationSessionStatusSuccess`, call `vibes_short_pulse()` alongside the existing `timer_set_name` + `main_force_redraw`.

Ordering: vibrate **after** `timer_set_name` succeeds, so the buzz can never signal a rename that did not happen.

### Decision 1b: Non-user-exit failures get the existing three-pulse pattern

The SDK's failure statuses split cleanly into two groups (`pebble.h:2069-2096`):

| Status | Doc comment | Vibration |
| --- | --- | --- |
| `FailureTranscriptionRejected` | "User rejected transcription and exited UI" | silent |
| `FailureTranscriptionRejectedWithError` | "User exited UI after transcription error" | silent |
| `FailureSystemAborted` | "Too many errors occurred during transcription and the UI exited" | three pulses |
| `FailureNoSpeechDetected` | "No speech was detected and UI exited" | three pulses |
| `FailureConnectivityError` | "No BT or internet connection" | three pulses |
| `FailureDisabled` | "Voice transcription disabled for this user" | three pulses |
| `FailureInternalError` | "Voice transcription failed due to internal error" | three pulses |
| `FailureRecognizerError` | "Cloud recognizer failed to transcribe speech" | three pulses |

The rule is *who ended the session*. The two `...Rejected...` statuses are the only ones whose doc comments say the **user** exited the UI; in both the user is looking at the watch and already knows nothing was renamed, so a buzz adds nothing. Everything else ends without the user necessarily having acknowledged it, and gets `prv_three_pulse_vibe()`.

Implementation is a `switch` (not an `if/else` on success) so each status is named explicitly and a future SDK addition does not silently inherit the wrong branch. One buzz means "renamed", three mean "nothing changed" — the same vocabulary the offline path already uses (`prv_show_no_phone_feedback`, `src/main.c:574`), so the feature stays internally consistent.

`prv_three_pulse_vibe` is defined under `#if LAP_FEATURE` (`src/main.c:317`), which is `1` on every non-aplite platform (`src/timer.h:21`); `PBL_MICROPHONE` excludes aplite, so the helper is always compiled wherever the dictation callback exists. No ungating or relocation is required — but the implementation should confirm this rather than assume it, since a link error here is the one way this decision fails.

*Alternative considered:* staying silent on failure. Rejected by the user — with the confirmation screen gone, a failed attempt would otherwise produce no feedback at all beyond the SDK's error dialog.

*Alternatives considered:* (a) keep the dialog and vibrate on commit — trivial, but the buzz lands after the user has already confirmed, so it signals nothing new; (b) build a custom in-app confirmation screen with our own vibration — full control, but a whole new UI mode and button map for a step the user does not want; (c) infer the confirmation screen from app-focus events — the dictation UI is one modal stack and does not reliably emit focus transitions between its internal screens. Rejected as guesswork.

`dictation_session_enable_error_dialogs` stays `true`: failures still get the SDK's on-screen explanation. Note this interacts with Decision 1b — see the risk below about error dialogs funnelling specific failures into `FailureTranscriptionRejectedWithError`.

### Decision 2: Repaint both icon variants, then verify empirically in the launcher

The colour variant is regenerated from the same glyph as **dark artwork over the existing alpha channel** (invert RGB, keep alpha), which reads against the launcher's white unselected rows and still separates from the highlighted row.

The B/W variant's correct polarity is *not* safely predictable — the classic launcher inverts the selected row (black background), so a black-on-transparent icon could disappear exactly where the colour one now works. Rather than guess, the implementation renders the launcher in the emulator for basalt (colour) and aplite (B/W), captures selected and unselected rows, and picks the polarity that is visible in all four cases. The `~bw.png` variant's missing alpha channel is fixed either way, so it composites instead of painting a white box.

*Alternative considered:* changing only `~color.png` and leaving `~bw.png` alone. Its solid white background is a latent version of the same bug, and it is one file — fix both while the emulator is already open.

### Decision 3: Test each at the level it is actually testable

- **Vibration:** unit test. `test/test_main_logic.c` `#include`s `src/main.c`, so `prv_dictation_callback` is directly callable — but only if `PBL_MICROPHONE` is defined for that build. Add `-DPBL_MICROPHONE` to the `test_main` target in `test/Makefile`, add stubs for the dictation API and `connection_service_peek_pebble_app_connection` next to the existing stubs in `test_main_logic.c`, and turn the empty `vibes_short_pulse` and `vibes_enqueue_custom_pattern` stubs into counters (the three-pulse helper goes through the custom-pattern call, so the two patterns are told apart by *which* counter moves, not by a pulse count). Tests then assert: success → name set, one `vibes_short_pulse`, zero custom patterns; each failure status → name unchanged, zero `vibes_short_pulse`, one custom pattern whose segments match the three-pulse shape.
- **Icon:** asset test, not a rendering test. The launcher is system UI and cannot be screenshotted by the functional harness. A small check (pytest in `test/functional/`, or a script the unit suite invokes) opens both PNGs and asserts a meaningful share of non-transparent pixels are dark — which is exactly the property that regressed. Actual legibility is confirmed once, manually, from the emulator launcher screenshots taken in Decision 2, and those screenshots are attached to the change.

*Alternative considered:* a functional emulator test for the vibration. The emulator has no microphone and no phone-side transcription, so dictation cannot be driven at all; `test_voice_rename_offline.py` is already skipped by default for related harness reasons. A unit test is the only automation available.

## Risks / Trade-offs

- **Users lose the chance to reject a bad transcription** → Accepted deliberately: renaming is a two-button gesture and re-running it overwrites the name. Documented in `docs/button-functions.md` so the behaviour change is discoverable.
- **With error dialogs enabled, real failures may reach the callback as `FailureTranscriptionRejectedWithError` rather than their specific status** — its doc comment is "user exited UI *after transcription error*", which suggests the SDK shows the error dialog and reports the user's dismissal of it, not the underlying cause. If so, the three-pulse branch would rarely fire in practice and most failures would land in the silent group. → This cannot be determined from the headers or the emulator (no microphone); task 6.3 checks it on a real emery watch by forcing a no-speech and a connectivity failure and observing whether either buzzes. If they land in the silent group and that feels wrong, the options are to buzz on `RejectedWithError` after all (the alternative already considered) or to disable error dialogs so specific statuses surface — both spec-visible changes, so revisit the spec rather than patching the code quietly.
- **The three-pulse helper sits behind `#if LAP_FEATURE`** → It is `1` on every platform where `PBL_MICROPHONE` is also set, so the combination is safe; a link error at task 2.2 is the signal that this reasoning was wrong, and the fix is to move the helper out of the `LAP_FEATURE` block.
- **Defining `PBL_MICROPHONE` in the unit build compiles previously-untested `#ifdef` code and may break the `test_main` build** → The newly-compiled region is small (dictation session lifecycle + no-phone feedback); missing symbols surface immediately as link errors and are stubbed alongside the existing stubs. If it proves invasive, fall back to a dedicated test binary with the define rather than changing the shared one.
- **Chosen icon polarity may look wrong on a platform not checked in the emulator** (chalk, diorite, emery, gabbro) → basalt and aplite are checked as the two rendering families; the others share one of those two variants and the same launcher behaviour.
- **The asset test could pass on artwork that is technically dark but still illegible** → It is a regression guard for the specific failure mode (all-white artwork), not a substitute for the one-time visual check.

## Migration Plan

No data, persistence, or settings migration. The `Voice Naming` setting, its default, and the Up+Back gesture are all unchanged. Rollback is reverting the commit; the icon PNGs are plain resource files and the dictation change is two lines.

## Open Questions

- ~~Final `~bw.png` polarity is decided by the emulator check in Decision 2, not in advance.~~ **Resolved:** no flip needed. Black-on-transparent is correct for both variants — the launcher *inverts* the icon on a B/W selected row, drawing the glyph white on the black highlight, so it stays legible. Evidence in `evidence/` (see `launcher_rows_zoomed.png`).
  - **Caveat on coverage:** the aplite emulator has no launcher menu (it offers a single "press select to launch your app" shortcut), so the B/W variant was verified on **diorite**, which renders the same `~bw.png` through the modern launcher. Aplite's own launcher remains visually unverified.
- Whether `FailureNoSpeechDetected` / `FailureConnectivityError` actually reach the callback while error dialogs are enabled, or arrive as `FailureTranscriptionRejectedWithError`. Resolved on-watch in task 6.3; the unit tests pin the mapping either way, so only the real-world frequency of each branch is in doubt.
