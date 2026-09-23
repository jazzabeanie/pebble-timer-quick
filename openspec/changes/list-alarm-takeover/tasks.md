## 0. Prerequisite

- [ ] 0.1 Archive (or at least commit) `wakeup-input-guard`, because this change builds on its guard code in `src/main.c`

## 1. Failing tests

- [ ] 1.1 `test/test_timer_multi.c`: tests for `timer_running_countdown_mask()`: a running countdown with time left is set; paused, overdue, and chrono slots are not set
- [ ] 1.2 `test/test_timer_multi.c`: tests for `timer_find_ended_countdown()`: -1 when none has ended; the ended slot when one has; the first to end when two have; ended slots outside the mask are ignored
- [ ] 1.3 `test/test_main_logic.c`: `main_show_alarm()` after a switch to an ended countdown slot leaves the main window in Counting mode on that slot and vibrating
- [ ] 1.4 `test/test_main_logic.c`: after `main_show_alarm()`, a press-down at +100 ms, a Back at +100 ms, and a release with no press-down are all ignored (the alarm keeps vibrating, the app does not pop); a Down press at +600 ms snoozes
- [ ] 1.5 Functional test `test/functional/test_list_alarm_takeover.py`: save a ~15 s countdown, exit with Back, reopen (user launch) so the Timer List shows, then wait for `list_alarm_takeover` and `alarm_start` (`m=Counting`, `v=1`); skip on aplite
- [ ] 1.6 Functional test: after the takeover, silence the alarm and quit, reopen, and check that the Timer List has one more entry (the kept stopwatch)
- [ ] 1.7 Run the new tests and confirm they fail

## 2. Implementation

- [ ] 2.1 `src/timer.c` / `timer.h`: add `timer_running_countdown_mask()` and `timer_find_ended_countdown(uint32_t mask)`, with a compile-time check that `MAX_TIMERS <= 32`
- [ ] 2.2 `src/main.c`: move the guard start in `prv_initialize` into `prv_start_input_guard()`
- [ ] 2.3 `src/main.c` / `main.h`: add `main_show_alarm()`: Counting mode, clear reverse direction, stop the edit-expire timer, start the guard, record the interaction, cancel the main app timer, and run `prv_app_timer_callback(NULL)` at once
- [ ] 2.4 `src/timer_list.c`: in `prv_window_load`, store `s_watch_mask` before the implicit slot is created
- [ ] 2.5 `src/timer_list.c`: in `prv_refresh_callback`, call `timer_find_ended_countdown(s_watch_mask)`; on a hit, set the active slot, keep the implicit slot, log `TEST_STATE:list_alarm_takeover,slot=<n>`, call `main_show_alarm()`, and pop the list
- [ ] 2.6 `src/timer_list.c`: add `prv_mask_remove_slot()` and call it after a single-timer delete (hold Down on an existing timer)
- [ ] 2.7 Wrap all new code in `WAKEUP_GUARD_FEATURE` so that it is compiled out on aplite

## 3. Verify

- [ ] 3.1 Re-run the new tests and confirm they pass
- [ ] 3.2 Run all unit tests and the full basalt functional suite (compare to the 153-test baseline; `test_timer_counts_down` is a known OCR flake)
- [ ] 3.3 Build for aplite and confirm that the text and data sizes are unchanged from before this change

## 4. Docs

- [ ] 4.1 Update `docs/button-functions.md`: in the Timer List section, describe the alarm takeover (kept stopwatch, input guard), with its test references
- [ ] 4.2 In the Wakeup Input Guard section, note that the guard also starts at a Timer List alarm takeover
