## Why

Two unrelated rough edges in everyday use:

1. **Voice rename gives no tactile signal.** After speaking a timer name the user has to keep watching the screen to know the transcription landed, and the SDK's confirmation dialog adds a second interaction for a rename that is trivially redone if wrong. The SDK offers no callback for "transcription arrived, awaiting confirmation", so the only way to buzz at that moment is to stop using the SDK confirmation screen.
2. **The app is effectively invisible in the launcher.** `resources/images/timer_icon~color.png` is drawn entirely in white pixels over transparency, so on the launcher's white unselected rows the icon disappears; it is only visible on the highlighted row.

## What Changes

- Disable the SDK dictation confirmation dialog (`dictation_session_enable_confirmation(..., false)`) so the result callback fires as soon as the transcription is ready.
- On a successful transcription, emit a **single** short vibration and apply the new name immediately. No confirmation screen — a wrong transcription is corrected by simply renaming again.
- On a dictation failure that ends by itself (no speech, connectivity, system abort, internal/recognizer error, disabled), emit **three** short vibrations and leave the name unchanged, so success and failure are told apart by feel alone.
- Stay silent when the user exits the dictation UI themselves (rejecting the transcription, or dismissing an error dialog) — they are already looking at the watch.
- **BREAKING** (behavioral): the transcription-review/re-record step disappears. A successful transcription commits without user acceptance.
- Repaint the launcher menu icon so its artwork is visible against the launcher's unselected (white/light) rows as well as the selected row, on both colour and black-and-white platforms.

## Capabilities

### New Capabilities
- `app-launcher-icon`: How the app's launcher/menu icon must render so it is legible on selected and unselected launcher rows across colour and B/W platforms.

### Modified Capabilities
- `voice-timer-rename`: Replaces the "dictation session presents a confirmation dialog before committing" requirement with immediate commit plus a short vibration signalling that the transcription completed, and adds a distinct three-pulse vibration on failures the user did not dismiss themselves.

## Impact

- `src/main.c`: `prv_dictation_callback` (one short pulse on success, three on failure via the existing `prv_three_pulse_vibe`), `prv_start_voice_rename` (confirmation disabled). Emery-only code path (`PBL_MICROPHONE`), so no aplite RAM impact.
- `resources/images/timer_icon~color.png` and `resources/images/timer_icon~bw.png`: artwork polarity/alpha regenerated. `appinfo.json` resource entry is unchanged.
- `openspec/specs/voice-timer-rename/spec.md`: confirmation-dialog requirement replaced.
- `docs/button-functions.md`: voice-rename row updated to note the immediate commit and the vibration.
- Tests: `test/functional/test_voice_rename_offline.py` (offline path must stay unaffected), plus a new asset-level check for the icon.
