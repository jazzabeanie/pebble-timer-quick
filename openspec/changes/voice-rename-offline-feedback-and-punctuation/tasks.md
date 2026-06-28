## 1. Punctuation trimming (timer_set_name)

- [x] 1.1 Add failing unit test(s) in `test/` for `timer_set_name()`: leading/trailing punctuation stripped ("...pasta!" → "pasta"), interior preserved ("mac & cheese" stays), punctuation-only input → empty name, existing whitespace cases still pass
- [x] 1.2 Run the unit tests and confirm the new cases fail
- [x] 1.3 Change the leading/trailing trim loops in `src/timer.c` `timer_set_name()` to strip all non-alphanumeric characters (not just whitespace)
- [x] 1.4 Re-run unit tests and confirm all pass

## 2. Offline feedback on voice rename

- [x] 2.1 Add a failing functional test in `test/functional/` (basalt/emery): starting voice rename while the phone is disconnected shows the no-phone icon, emits three short vibrations, and does NOT start dictation or change the timer name — `test_voice_rename_offline.py::test_offline_rename_shows_no_phone_feedback`
- [x] 2.2 Add/confirm a functional test that voice rename proceeds normally when the phone is connected — `test_voice_rename_offline.py::test_connected_rename_shows_no_feedback`
- [x] 2.3 Add a functional test that the no-phone icon auto-dismisses after ~1 second, returning to `ControlModeEditSec` — `test_voice_rename_offline.py::test_offline_feedback_auto_dismisses`
- [x] 2.4 Run the functional tests and confirm the offline-feedback tests fail — **Blocked in this harness:** `pebble emu-bt-connection no` corrupts the QEMU button channel (`Exception decoding QemuInboundPacket.footer`), so buttons stop registering and the emulator wedges. Confirmed via three isolation experiments (connected chord fires `button_back`; any button after BT-off is dropped). Same class of limitation the prior `voice-timer-naming` change documented. Tests are guarded with `pytestmark = skipif(RUN_BT_TOGGLE_TESTS != "1")` and skip by default with that reason.
- [x] 2.5 Verify whether the installed SDK exposes a reusable no-phone graphic; if not, add a small no-phone bitmap to `resources/images` and register it (PBL_MICROPHONE-gated) — verified no public SDK graphic exists; added `no_phone~bw.png`/`no_phone~color.png` and registered `IMAGE_NO_PHONE` in `appinfo.json` with `targetPlatforms` = mic platforms (all except aplite)
- [x] 2.6 In `src/main.c` `prv_start_voice_rename()`, pre-check `connection_service_peek_pebble_app_connection()`; if disconnected, show the no-phone icon, enqueue a three-short-pulse custom vibration pattern, and do not create/start a dictation session
- [x] 2.7 Schedule a ~1-second `app_timer` to hide the icon and return to `ControlModeEditSec` with the timer name unchanged
- [x] 2.8 Re-run the functional tests and confirm all pass — **Blocked (see 2.4).** Implementation instead verified by a clean multi-platform build and the unit suite; the offline path remains exercised by `test_voice_rename_offline.py` on any harness that supports BT-toggle + button input (`RUN_BT_TOGGLE_TESTS=1`).

## 3. Docs and verification

- [x] 3.1 Update `docs/button-functions.md` for the Up+Back voice-rename behavior when disconnected
- [x] 3.2 Build the app (`conda-env/bin/pebble build`) and run the full functional + unit test suites; confirm green — `pebble build` succeeds on all 6 platforms; unit suites green (`run_test_timer` 31, `run_test_timer_multi` 11, `run_test_mnemonic` 4); offline functional tests skip with a documented reason (see 2.4). `run_test_main`/`run_test_drawing` remain non-compiling against the host stub (pre-existing, unrelated to this change).
