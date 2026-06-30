## 1. Data model: slots, name length, persistence

- [ ] 1.1 Raise `MAX_TIMERS` in `src/timer.h` to the new limit (proposed 16) and enlarge `Timer.name` (proposed `char[40]`); add a `uint8_t lap_count` field to `Timer`
- [ ] 1.2 Bump `PERSIST_VERSION` in `src/timer.c`; confirm the version-mismatch reset path and the `count > MAX_TIMERS` validation still behave correctly with the new constants
- [ ] 1.3 Verify `timer_assign_name` and `timer_set_name` use `sizeof(name)` (not hard-coded 20) so they adapt to the larger buffer; fix the suffix logic to handle multi-digit collision suffixes if needed

## 2. Lap recording (timer module)

- [ ] 2.1 Add `int8_t timer_slot_lap(uint8_t src_idx)` to `src/timer.h`/`timer.c`: allocate a free slot, copy the source `Timer`, convert the copy to a paused snapshot at the current value, set its name to `Lap [n]: <src name>`, increment the source's `lap_count`; return slot index or -1 when full
- [ ] 2.2 Write failing unit tests in `test/test_timer.c` / `test/test_timer_multi.c` for: lap copy is paused at snapshot value, name is `Lap 1:`/`Lap 2:` incrementing, returns -1 at capacity, original unchanged; confirm they fail
- [ ] 2.3 Implement until 2.2 tests pass

## 3. Settings: Lap Stopwatch toggle

- [ ] 3.1 Add `lap_stopwatch_enabled` (default false) to `AppSettings` and a new AppMessage key (`APPMSG_KEY_LAP_STOPWATCH_ENABLED = 15`) in `src/settings.c`; bump `PERSIST_SETTINGS_VERSION`
- [ ] 3.2 Add `settings_get_lap_stopwatch_enabled()` to `src/settings.h`/`settings.c` and wire it into the inbox `HANDLE` block and the defaults struct
- [ ] 3.3 Add the `Lap Stopwatch` toggle row and key `15` payload entry to `src/js/pebble-js-app.js`

## 4. Flash rendering override

- [ ] 4.1 Add `drawing_set_slot_override(int8_t slot)` (and getter) to `src/drawing.h`/`drawing.c`; when set (≥0), `drawing_render` renders that slot as a paused Counting timer instead of the active slot
- [ ] 4.2 Ensure all `timer_data`/`main_get_control_mode()` reads in the render path honor the override without changing `s_active_slot`

## 5. Lap flash state machine (main)

- [ ] 5.1 Add flash state to `main_data`: lap slot index, flash deadline, 500 ms toggle `AppTimer`, and `s_flash_showing_lap`
- [ ] 5.2 Add a flash-tick callback that flips the override between the lap slot and none every 500 ms, redraws, and stops/clears at the 3 s deadline
- [ ] 5.3 In `prv_select_click_handler`, gate on `settings_get_lap_stopwatch_enabled()` + `ControlModeCounting` + running + not alarm: record a lap via `timer_slot_lap`, keep the original active, and start the flash instead of toggling play/pause
- [ ] 5.4 Handle re-lap: a Select press while the flash is active cancels the flash and records the next lap, restarting the flash
- [ ] 5.5 Clear the override and cancel the flash timer on flash expiry, on leaving Counting mode, and on window unload / app terminate

## 6. Timer List: Delete all, scrolling, post-delete selection

- [ ] 6.1 Add a synthetic pinned "Delete all" bottom row: include it in `s_total_rows`, draw the literal label, and return a sentinel from `prv_slot_for_row`
- [ ] 6.2 Hold-Down on the Delete all row deletes every timer (loop delete / reset count) and exits the app to the watchface
- [ ] 6.3 Select on the Delete all row shows a transient "hold Down to clear all timers" hint (AppTimer-driven overlay, mirroring the no-phone feedback pattern) and deletes nothing
- [ ] 6.4 Change `prv_down_long_click_handler` post-delete selection to the previous timer entry (`r - 1`); if the deleted timer was topmost (previous is the New Timer row) keep position `r` so the next timer shifts up; if no timers remain select the New Timer row; never select the Delete all row
- [ ] 6.5 Enlarge the Timer List row-drawing buffers (`line1[20]`/`line2[20]` in `prv_layer_update_proc`) so longer names display without being clipped to 19 chars
- [ ] 6.6 Confirm `prv_update_scroll`/`s_scroll_y` keep the selected row visible with the larger slot count plus the Delete all row

## 7. Functional tests

- [ ] 7.1 Add failing functional tests for recording a lap (paused copy created, original keeps running, active stays original) and the `Lap [n]:` naming/increment
- [ ] 7.2 Add failing functional tests for the flash window (re-lap on Select cancels and re-records) and for the no-free-slot guard
- [ ] 7.3 Add failing functional tests in `test_timer_list.py` for the Delete all row (hold Down clears all and exits; Select shows hint), list scrolling, and post-delete selection: previous timer selected on a normal delete, position kept (next shifts up) when deleting the topmost timer, New Timer selected when the last timer is deleted, and never landing on Delete all
- [ ] 7.4 Run the new functional tests, confirm they fail, implement/adjust, then confirm they pass; baseline-compare the basalt suite for pre-existing failures

## 8. Documentation

- [ ] 8.1 Update `docs/button-functions.md`: Counting-mode Select records a lap when Lap Stopwatch is enabled, the flash window, the Timer List "Delete all" row behaviors, and the changed post-delete selection
- [ ] 8.2 Update the Settings table in `docs/button-functions.md` with the `Lap Stopwatch` setting (default off)
- [ ] 8.3 Add a warning to `README.md` that updating to this version will erase any previously saved timers (persisted timers are reset on the `PERSIST_VERSION` bump)
