## 1. Voice rename: failing tests first

- [x] 1.1 Add `-DPBL_MICROPHONE` to the `test_main` target in `test/Makefile` and confirm `make test_main` builds (adding stubs as link errors demand)
- [x] 1.2 Add stubs next to the existing ones in `test/test_main_logic.c`: `dictation_session_create/destroy/start/stop`, `dictation_session_enable_confirmation`, `dictation_session_enable_error_dialogs`, `connection_service_peek_pebble_app_connection`; record the last `enable_confirmation` value so it can be asserted
- [x] 1.3 Replace the empty `vibes_short_pulse` and `vibes_enqueue_custom_pattern` stubs with counters that also record the last pattern's segments (plus a reset helper used in test setup)
- [x] 1.4 Write `test_dictation_success_vibrates_and_sets_name`: call `prv_dictation_callback` with `DictationSessionStatusSuccess` and "pasta"; expect the active slot's name is "pasta", exactly one short pulse, and zero custom patterns
- [x] 1.5 Write buzzing-failure tests for `FailureSystemAborted`, `FailureNoSpeechDetected`, `FailureConnectivityError`, `FailureDisabled`, `FailureInternalError`, and `FailureRecognizerError`: name unchanged, zero short pulses, and exactly one custom pattern matching the three-pulse segments
- [x] 1.6 Write silent-failure tests for `FailureTranscriptionRejected` and `FailureTranscriptionRejectedWithError` (user exited the UI themselves): name unchanged, zero short pulses, zero custom patterns
- [x] 1.7 Write `test_dictation_confirmation_disabled`: after `prv_start_voice_rename` with a connected phone, the recorded `enable_confirmation` value is `false`
- [x] 1.8 Run `make -C test test_main` and confirm the new tests FAIL for the expected reasons

## 2. Voice rename: implementation

- [x] 2.1 In `prv_start_voice_rename` (`src/main.c:596`), change `dictation_session_enable_confirmation(s_dictation_session, true)` to `false`; leave `enable_error_dialogs` as `true`
- [x] 2.2 In `prv_dictation_callback` (`src/main.c:554`), replace the success-only `if` with a `switch` on `status`: `Success` → `timer_set_name` then `vibes_short_pulse()`; `FailureTranscriptionRejected` and `FailureTranscriptionRejectedWithError` → do nothing; all remaining `Failure*` statuses → `prv_three_pulse_vibe()` (confirm the helper links: it is defined under `#if LAP_FEATURE` at `src/main.c:317`, which should be `1` on all `PBL_MICROPHONE` platforms — if it does not link, move it out of that block)
- [x] 2.3 Re-run `make -C test test_main` and confirm all tests pass
- [x] 2.4 Run the full unit suite (`make -C test test`) and confirm no regressions

## 3. Menu icon: failing asset check first

- [x] 3.1 Add an asset check (pytest module under `test/functional/`, no emulator required) asserting that for both `resources/images/timer_icon~color.png` and `~bw.png`, a meaningful share of non-transparent pixels are dark rather than near-white
- [x] 3.2 Run it and confirm it FAILS against the current all-white `~color.png`

## 4. Menu icon: artwork fix

- [x] 4.1 Regenerate `resources/images/timer_icon~color.png` as dark artwork over the existing alpha channel (invert RGB, preserve alpha, keep 25x25)
- [x] 4.2 Regenerate `resources/images/timer_icon~bw.png` with a real alpha channel so it composites instead of painting a solid white box
- [x] 4.3 Run the asset check from 3.1 and confirm it passes

## 5. Menu icon: visual verification (decides `~bw` polarity)

- [x] 5.1 Build (`conda-env/bin/pebble build`) and install on the basalt emulator; screenshot the launcher with the app row unselected and selected; confirm the icon reads in both
- [x] 5.2 Repeat on the aplite emulator for the `~bw.png` variant
- [x] 5.3 If either variant is invisible in one of the four states, flip that variant's polarity, regenerate, and repeat 5.1-5.2 until all four read (this resolves the design's open question)
- [x] 5.4 Save the four launcher screenshots under the change directory as evidence

## 6. Regression and documentation

- [x] 6.1 Run the basalt functional suite (`cd test/functional && python -m pytest -v --platform=basalt`) and compare against the 141-passed/0-failed baseline
- [x] 6.2 Update `docs/button-functions.md` (lines 65, 93, and the "Voice rename gesture" notes at 95-98): a successful transcription now commits immediately with a single short vibration and no confirmation screen; failures that end on their own give three short vibrations with the name unchanged; backing out of the dictation UI is silent; cite the new unit tests in the Tests column
- [ ] 6.3 Verify the voice rename end-to-end on a real emery watch (emulator cannot drive dictation): speak a name and feel one short buzz with the name applied and no review screen; back out of the dictation UI and feel nothing
- [ ] 6.4 On the same watch, resolve the design's open question: force a no-speech failure (start dictation and stay silent) and a connectivity failure (disconnect the phone mid-session), and record whether each buzzes three times or lands silently as `FailureTranscriptionRejectedWithError`; note the finding in the change before archiving, and raise it if the silent case feels wrong
