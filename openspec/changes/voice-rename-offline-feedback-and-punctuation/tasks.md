## 1. Punctuation trimming (timer_set_name)

- [ ] 1.1 Add failing unit test(s) in `test/` for `timer_set_name()`: leading/trailing punctuation stripped ("...pasta!" → "pasta"), interior preserved ("mac & cheese" stays), punctuation-only input → empty name, existing whitespace cases still pass
- [ ] 1.2 Run the unit tests and confirm the new cases fail
- [ ] 1.3 Change the leading/trailing trim loops in `src/timer.c` `timer_set_name()` to strip all non-alphanumeric characters (not just whitespace)
- [ ] 1.4 Re-run unit tests and confirm all pass

## 2. Offline feedback on voice rename

- [ ] 2.1 Add a failing functional test in `test/functional/` (basalt/emery): starting voice rename while the phone is disconnected shows the no-phone icon, emits three short vibrations, and does NOT start dictation or change the timer name
- [ ] 2.2 Add/confirm a functional test that voice rename proceeds normally when the phone is connected
- [ ] 2.3 Add a functional test that the no-phone icon auto-dismisses after ~1 second, returning to `ControlModeEditSec`
- [ ] 2.4 Run the functional tests and confirm the offline-feedback tests fail
- [ ] 2.5 Verify whether the installed SDK exposes a reusable no-phone graphic; if not, add a small no-phone bitmap to `resources/images` and register it (PBL_MICROPHONE-gated)
- [ ] 2.6 In `src/main.c` `prv_start_voice_rename()`, pre-check `connection_service_peek_pebble_app_connection()`; if disconnected, show the no-phone icon, enqueue a three-short-pulse custom vibration pattern, and do not create/start a dictation session
- [ ] 2.7 Schedule a ~1-second `app_timer` to hide the icon and return to `ControlModeEditSec` with the timer name unchanged
- [ ] 2.8 Re-run the functional tests and confirm all pass

## 3. Docs and verification

- [ ] 3.1 Update `docs/button-functions.md` for the Up+Back voice-rename behavior when disconnected
- [ ] 3.2 Build the app (`conda-env/bin/pebble build`) and run the full functional + unit test suites; confirm green
