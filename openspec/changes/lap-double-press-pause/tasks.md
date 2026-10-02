## 1. Failing tests

- [x] 1.1 Add a `window_multi_click_subscribe` stub (and any needed declarations) to `test/pebble.h` / `test/test_main_logic.c`; record which Select subscriptions were made so tests can assert armed/disarmed
- [x] 1.2 `test/test_timer_multi.c`: add tests for `timer_pause_at` (chrono paused value equals `at_ms - start`) and `timer_slot_lap_at` (snapshot and `last_lap_ms` use `at_ms`)
- [x] 1.3 `test/test_main_logic.c`: add tests that double-press on a running lap stopwatch pauses at the first press-down time and creates no lap slot
- [x] 1.4 `test/test_main_logic.c`: add tests that multi-click is subscribed only while armed (running lap stopwatch in Counting mode) and not in New/EditSec, paused, countdown, or setting-off states, and not after `main_show_alarm` (alarm takeover)
- [x] 1.5 `test/functional/test_stopwatch_laps.py`: add `TestDoublePressPause` tests (use the `double_press_select` helper from 1.8): double-press pauses with no new lap; double-press during flash pauses; single Select resumes; edit-mode double tap still adds two increments
- [x] 1.6 `test/test_main_logic.c`: add tests that Select raw-down while armed sets the display freeze at the press time, that no freeze is set when not armed, and that the single, double, and long handlers, the lap-full path, and the 1 s timeout each clear it; a press-down during the lap flash cancels the flash and freezes the running stopwatch value, and a flash timer tick that fires before the press resolves does not change the frozen display
- [x] 1.7 `test/functional/test_stopwatch_laps.py`: add a test that the value shown right after Select press-down is frozen and equals the recorded lap value
- [x] 1.8 `test/functional/conftest.py`: add a `double_press_select()` helper with short holds, so that both press-downs are inside the 300 ms window (`press_select` holds for 250 ms and then waits 300 ms, so two calls cannot make a double press)
- [x] 1.9 `test/test_main_logic.c`: add a test that the double-click handler does nothing (no pause, no lap) when the wakeup input guard blocks the Select press
- [x] 1.10 `test/test_main_logic.c`: add a test that an alarm takeover (`main_show_alarm`) with the display frozen clears the freeze and the pending-press flag
- [x] 1.11 Build, run the new unit and functional tests, and confirm they fail

## 2. Timer helpers

- [x] 2.1 Add `timer_pause_at(int64_t at_ms)` to `src/timer.c` / `timer.h` (inside `LAP_FEATURE`)
- [x] 2.2 Add `timer_slot_lap_at(uint8_t slot, int64_t at_ms)`; make `timer_slot_lap` a wrapper that passes `epoch()`

## 3. Select handling in main.c

- [x] 3.1 Add `select_down_ms`, `select_press_pending`, and `select_multi_armed` fields to `main_data` (inside `LAP_FEATURE`)
- [x] 3.2 Record the first press-down time in `prv_select_raw_click_handler`; clear the pending flag in the single and double click handlers
- [x] 3.3 Make `prv_record_lap` use `timer_slot_lap_at(..., select_down_ms)`
- [x] 3.4 Add `prv_lap_double_press_armed()` and `prv_refresh_click_config()`; subscribe Select multi-click (2 clicks, 300 ms, last-click-only) in `prv_click_config_provider` only when armed
- [x] 3.5 Add `prv_select_double_click_handler`: return at once if `prv_press_blocked(BUTTON_ID_SELECT)` (wakeup input guard), then cancel the flash, `timer_pause_at(select_down_ms)`, finish the interaction with a `double_press_select` TEST_STATE log
- [x] 3.6 Add `drawing_set_freeze_ms` / `drawing_clear_freeze` to `src/drawing.c` (inside `LAP_FEATURE`): while set, the draw path evaluates the active timer at the frozen time and shows the millisecond field
- [x] 3.7 Set the freeze in the Select raw-down handler when armed, and cancel any active lap flash first so the frozen frame shows the running stopwatch; clear it in the single, double, and long handlers, the lap-full path, a safety `AppTimer` of about 1 s (1200 ms, see design D5), and `prv_terminate`
- [x] 3.8 Call `prv_refresh_click_config()` from `prv_finish_interaction` (after `prv_watch_arm()`, which can do an alarm takeover), `main_show_alarm`, the settings-changed callback, the Timer List return path, and the New-mode expire callback (also added: the Select click on an alarm, and the refresh callback when an alarm stops on its own)
- [x] 3.9 In `prv_refresh_click_config()`, on the change from armed to not armed, clear the freeze, cancel the safety timer, and clear `select_press_pending`

## 4. Verify

- [x] 4.1 Re-run the new unit and functional tests and confirm they pass
- [x] 4.2 Run the full basalt functional suite and compare to a baseline run of the same suite on `master` (153 tests, with 1 to 4 intermittent failures on the baseline too); fix existing lap tests that relied on an immediate lap after Select, and wait for `lap_recorded` between two Select presses in sequence so they are not read as a double press. Result (2026-10-02): 177 passed, 1 failed, 2 reruns. The failure is `test_create_timer.py::TestCreateTimer::test_down_button_increments_minutes` (an OCR test, flaky-marked; OCR reads `266` for `2:5x`). It also fails 2 of 3 attempts on the `master` build in isolation, and passes on some runs of the changed build, so it is not a regression. No existing lap test needed a change: they already wait for `lap_recorded`
- [x] 4.3 Build for aplite and confirm it still fits in RAM (the feature is compiled out)
- [x] 4.4 Check on the emulator that the Select long press and the raw reset animation still work after arm and disarm. Result: `test_long_press_restarts_after_arm_and_disarm` passes (pause, resume, then hold restarts), and the raw-down handler runs after arm and disarm (the freeze test passes). The reset animation was not inspected visually; its call in the raw-down handler is unchanged

## 5. Docs

- [x] 5.1 Update `docs/button-functions.md`: Counting-mode Select row, Lap Stopwatch section (double-press pause, display freeze at press-down, ~0.3 s lap flash delay, lap value at press-down), settings table row, and test references
