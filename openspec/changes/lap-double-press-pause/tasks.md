## 1. Failing tests

- [ ] 1.1 Add a `window_multi_click_subscribe` stub (and any needed declarations) to `test/pebble.h` / `test/test_main_logic.c`; record which Select subscriptions were made so tests can assert armed/disarmed
- [ ] 1.2 `test/test_timer_multi.c`: add tests for `timer_pause_at` (chrono paused value equals `at_ms - start`) and `timer_slot_lap_at` (snapshot and `last_lap_ms` use `at_ms`)
- [ ] 1.3 `test/test_main_logic.c`: add tests that double-press on a running lap stopwatch pauses at the first press-down time and creates no lap slot
- [ ] 1.4 `test/test_main_logic.c`: add tests that multi-click is subscribed only while armed (running lap stopwatch in Counting mode) and not in New/EditSec, paused, countdown, or setting-off states
- [ ] 1.5 `test/functional/test_stopwatch_laps.py`: add `TestDoublePressPause` tests: double-press pauses with no new lap; double-press during flash pauses; single Select resumes; edit-mode double tap still adds two increments
- [ ] 1.6 `test/test_main_logic.c`: add tests that Select raw-down while armed sets the display freeze at the press time, that no freeze is set when not armed, and that the single, double, and long handlers, the lap-full path, and the 1 s timeout each clear it; a press-down during the lap flash cancels the flash and freezes the running stopwatch value, and a flash timer tick that fires before the press resolves does not change the frozen display
- [ ] 1.7 `test/functional/test_stopwatch_laps.py`: add a test that the value shown right after Select press-down is frozen and equals the recorded lap value
- [ ] 1.8 Build, run the new unit and functional tests, and confirm they fail

## 2. Timer helpers

- [ ] 2.1 Add `timer_pause_at(int64_t at_ms)` to `src/timer.c` / `timer.h` (inside `LAP_FEATURE`)
- [ ] 2.2 Add `timer_slot_lap_at(uint8_t slot, int64_t at_ms)`; make `timer_slot_lap` a wrapper that passes `epoch()`

## 3. Select handling in main.c

- [ ] 3.1 Add `select_down_ms`, `select_press_pending`, and `select_multi_armed` fields to `main_data` (inside `LAP_FEATURE`)
- [ ] 3.2 Record the first press-down time in `prv_select_raw_click_handler`; clear the pending flag in the single and double click handlers
- [ ] 3.3 Make `prv_record_lap` use `timer_slot_lap_at(..., select_down_ms)`
- [ ] 3.4 Add `prv_lap_double_press_armed()` and `prv_refresh_click_config()`; subscribe Select multi-click (2 clicks, 300 ms, last-click-only) in `prv_click_config_provider` only when armed
- [ ] 3.5 Add `prv_select_double_click_handler`: cancel the flash, `timer_pause_at(select_down_ms)`, finish the interaction with a `double_press_select` TEST_STATE log
- [ ] 3.6 Add `drawing_set_freeze_ms` / `drawing_clear_freeze` to `src/drawing.c` (inside `LAP_FEATURE`): while set, the draw path evaluates the active timer at the frozen time and shows the millisecond field
- [ ] 3.7 Set the freeze in the Select raw-down handler when armed, and cancel any active lap flash first so the frozen frame shows the running stopwatch; clear it in the single, double, and long handlers, the lap-full path, a 1 s safety `AppTimer`, and `prv_terminate`
- [ ] 3.8 Call `prv_refresh_click_config()` from `prv_finish_interaction`, the settings-changed callback, the Timer List return path, and the New-mode expire callback
- [ ] 3.9 If `wakeup-input-guard` has already landed, apply its guard to the new double-click handler

## 4. Verify

- [ ] 4.1 Re-run the new unit and functional tests and confirm they pass
- [ ] 4.2 Run the full basalt functional suite; fix existing lap tests that relied on an immediate lap after Select (compare to the 141/0 baseline)
- [ ] 4.3 Build for aplite and confirm it still fits in RAM (the feature is compiled out)
- [ ] 4.4 Check on the emulator that the Select long press and the raw reset animation still work after arm and disarm

## 5. Docs

- [ ] 5.1 Update `docs/button-functions.md`: Counting-mode Select row, Lap Stopwatch section (double-press pause, display freeze at press-down, ~0.3 s lap flash delay, lap value at press-down), settings table row, and test references
