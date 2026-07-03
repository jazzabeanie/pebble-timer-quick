## 1. Data model: slots, name length, persistence

- [x] 1.1 Raise `MAX_TIMERS` in `src/timer.h` to 32 and enlarge `Timer.name` (proposed `char[40]`); add a `uint8_t lap_count` field and an `int64_t last_lap_ms` field (cumulative elapsed at the most recent lap; 0 = none) to `Timer`
- [x] 1.2 Bump `PERSIST_VERSION` in `src/timer.c`; confirm the version-mismatch reset path and the `count > MAX_TIMERS` validation still behave correctly with the new constants
- [x] 1.2a Verify all 32 slots actually persist and reload within the 4 KB per-app budget (fill to capacity, save, reload) on at least aplite and emery — the ceiling is below a naive `4096 / sizeof(Timer)` due to per-field overhead and shared settings/version keys, so this must be measured, not assumed
- [x] 1.3 Verify `timer_assign_name` and `timer_set_name` use `sizeof(name)` (not hard-coded 20) so they adapt to the larger buffer; fix the suffix logic to handle multi-digit collision suffixes if needed

## 2. Lap recording (timer module)

- [x] 2.1 Add `int8_t timer_slot_lap(uint8_t src_idx)` to `src/timer.h`/`timer.c`: allocate a free slot, copy the source `Timer`, convert the copy to a paused snapshot whose total equals the source's current elapsed, set `copy.last_lap_ms = src.last_lap_ms` (so the copy's split and cumulative display correctly), set its name to `Lap [n]: <src name>` (using `snprintf` so the END of the source name is trimmed when the prefix would overflow the buffer, keeping the prefix intact and the result null-terminated); then set `src.last_lap_ms = <total at snapshot>` and increment `src.lap_count`; return slot index or -1 when full
- [x] 2.1a Add `int64_t timer_get_split_ms(void)` returning `total − last_lap_ms` (equals the total when `last_lap_ms == 0`)
- [x] 2.2 Write failing unit tests in `test/test_timer.c` / `test/test_timer_multi.c` for: lap copy is paused at snapshot value, split/cumulative computed correctly for the copy (`last_lap_ms` carried) and for the running source after a lap, name is `Lap 1:`/`Lap 2:` incrementing, returns -1 at capacity, original's total unchanged, a long source name is trimmed at the end so the `Lap [n]: ` prefix stays intact and the result stays null-terminated within the buffer; confirm they fail
- [x] 2.3 Implement until 2.2 tests pass

## 3. Settings: Lap Stopwatch toggle

- [x] 3.1 Add `lap_stopwatch_enabled` (default false) to `AppSettings` and a new AppMessage key (`APPMSG_KEY_LAP_STOPWATCH_ENABLED = 15`) in `src/settings.c`; bump `PERSIST_SETTINGS_VERSION`
- [x] 3.2 Add `settings_get_lap_stopwatch_enabled()` to `src/settings.h`/`settings.c` and wire it into the inbox `HANDLE` block and the defaults struct
- [x] 3.3 Add the `Lap Stopwatch` toggle row and key `15` payload entry to `src/js/pebble-js-app.js`

## 4. Flash rendering override

- [x] 4.1 Add `drawing_set_slot_override(int8_t slot)` (and getter) to `src/drawing.h`/`drawing.c`; when set (≥0), `drawing_render` renders that slot as a paused Counting timer instead of the active slot
- [x] 4.2 Ensure all `timer_data`/`main_get_control_mode()` reads in the render path honor the override without changing `s_active_slot`
- [x] 4.3 Split/total display: change `prv_render_main_text` to use `timer_get_split_ms()` for the main value (identical output until a lap is recorded, so no `Lap Stopwatch` check needed here); in `prv_render_header_text`, when `settings_get_lap_stopwatch_enabled()` and the timer is a chrono, render the total prefixed with the count-up arrow (`-->%02d:%02d` / `-->%02d:%02d:%02d`) instead of the `00:00-->` base-length header; leave non-chrono and lapping-disabled headers unchanged

## 5. Lap flash state machine (main)

- [x] 5.1 Add flash state to `main_data`: lap slot index, flash deadline, 500 ms toggle `AppTimer`, and `s_flash_showing_lap`
- [x] 5.2 Add a flash-tick callback that flips the override between the lap slot and none every 500 ms, redraws, and stops/clears at the 3 s deadline
- [x] 5.3 In `prv_select_click_handler`, gate on `settings_get_lap_stopwatch_enabled()` + `ControlModeCounting` + running + not alarm: record a lap via `timer_slot_lap`, keep the original active, and start the flash instead of toggling play/pause
- [x] 5.3a Handle the capacity case: when `timer_slot_lap` returns -1, do not toggle play/pause or start the flash; instead show a "no free slots" warning overlay plus three short vibration pulses (reuse the `prv_show_no_phone_feedback` `{100,100,100,100,100}` pattern, factored into a shared helper), leaving the original timer running with its play/pause state unchanged
- [x] 5.4 Handle re-lap: a Select press while the flash is active cancels the flash and records the next lap, restarting the flash
- [x] 5.5 Clear the override and cancel the flash timer on flash expiry, on leaving Counting mode, and on window unload / app terminate
- [x] 5.6 Add an approaching-limit warning: a shared helper that, given the remaining free slots (`MAX_TIMERS - timer_count`), when ≤ 3 builds a "N slots left" message and enqueues the three-pulse `{100,100,100,100,100}` pattern. Call it after every successful timer/lap creation; do nothing when > 3 free
- [x] 5.7 Normal-timer presentation: on first creation that leaves ≤ 3 free, show the message via a 3-second AppTimer-driven overlay (mirroring `prv_show_no_phone_feedback`, held 3 s), then auto-dismiss
- [x] 5.8 Lap presentation: when the recorded lap left ≤ 3 free, set a flash flag (e.g. `s_flash_show_limit_warning`) so the flash "original" phase renders the warning message instead of the original timer while the "lap" phase keeps flashing the paused lap; clear the flag when the flash window ends
- [x] 5.9 Long-press Select restart: when `settings_get_lap_stopwatch_enabled()`, extend the chrono restart to also reset the lap session — zero the total and `last_lap_ms`, reset `lap_count` to 0 (next lap is `Lap 1`), and assign a new name via `timer_assign_name`; leave previously recorded lap slots untouched. With lapping disabled, keep the current restart (name preserved)

## 6. Timer List: Delete all, scrolling, post-delete selection

- [x] 6.1 Add a synthetic pinned "Delete all" bottom row: include it in `s_total_rows`, draw the literal label, and return a sentinel from `prv_slot_for_row`
- [x] 6.2 Hold-Down on the Delete all row deletes every timer (loop delete / reset count) and exits the app to the watchface
- [x] 6.3 Select on the Delete all row shows a transient "hold Down to clear all timers" hint (AppTimer-driven overlay, mirroring the no-phone feedback pattern) and deletes nothing
- [x] 6.4 Change `prv_down_long_click_handler` post-delete selection to the previous timer entry (`r - 1`); if the deleted timer was topmost (previous is the New Timer row) keep position `r` so the next timer shifts up; if no timers remain select the New Timer row; never select the Delete all row
- [x] 6.5 Enlarge the Timer List row-drawing buffers (`line1[20]`/`line2[20]` in `prv_layer_update_proc`) so longer names display without being clipped to 19 chars
- [x] 6.6 Confirm `prv_update_scroll`/`s_scroll_y` keep the selected row visible with the larger slot count plus the Delete all row

## 7. Functional tests

- [x] 7.1 Add failing functional tests for recording a lap (paused copy created, original keeps running, active stays original) and the `Lap [n]:` naming/increment
- [x] 7.2 Add failing functional tests for the flash window (re-lap on Select cancels and re-records) and for the no-free-slot guard: at capacity, Select records no lap, shows the warning overlay, emits three short vibrations, and leaves the original running with its play/pause state unchanged
- [x] 7.2a Add failing functional tests for the approaching-limit warning: creating a normal timer that leaves ≤ 3 free shows the message (3 s) with three vibrations and none while > 3 free; recording a lap that leaves ≤ 3 free shows the message in place of the original during the flash while the paused lap keeps flashing; warning repeats on each creation near the limit
- [x] 7.2b Add failing functional tests for the split/total display: with lapping enabled, before the first lap main == header and the header shows the total with the `-->` prefix; after a lap the main restarts and counts the new split while the header keeps the total; a lap slot shows its split (main) and cumulative (`-->` header); with lapping disabled the header still shows `00:00-->` and main shows the total
- [x] 7.2c Add failing functional tests for long-press Select: with lapping enabled it restarts the stopwatch, resets lap numbering (next lap is `Lap 1`), and gives it a new name while leaving prior lap slots intact; with lapping disabled it restarts without renaming
- [x] 7.3 Add failing functional tests in `test_timer_list.py` for the Delete all row (hold Down clears all and exits; Select shows hint), list scrolling, and post-delete selection: previous timer selected on a normal delete, position kept (next shifts up) when deleting the topmost timer, New Timer selected when the last timer is deleted, and never landing on Delete all
- [x] 7.4 Run the new functional tests, confirm they fail, implement/adjust, then confirm they pass; baseline-compare the basalt suite for pre-existing failures

## 8. Documentation

- [x] 8.1 Update `docs/button-functions.md`: Counting-mode Select records a lap when Lap Stopwatch is enabled, the flash window, the split/total display (main = split, header = total with `-->` prefix), long-press Select restart-and-rename when lapping is enabled, the Timer List "Delete all" row behaviors, and the changed post-delete selection
- [x] 8.2 Update the Settings table in `docs/button-functions.md` with the `Lap Stopwatch` setting (default off)
- [x] 8.3 Add a warning to `README.md` that updating to this version will erase any previously saved timers (persisted timers are reset on the `PERSIST_VERSION` bump)

## 9. Spec amendments (2026-07-03): flash timing, disabled header, aplite settings note

- [x] 9.1 Change the lap flash timing in `src/main.c`: `FLASH_TICK_MS` 500 → 1000 and `FLASH_WINDOW_MS` 3000 → 5000 (1 s lap / 1 s original, auto-dismiss after 5 s)
- [x] 9.2 Update the flash functional tests (`test_stopwatch_laps.py::TestLapFlash`, `TestSplitTotalDisplay`, `TestLongPressRestart`) for the 1 s cadence and 5 s window (phase counts, waits after "let the flash window end", and the re-lap press spacing)
- [x] 9.3 Lapping-disabled stopwatch header: in `prv_format_header_text` (`src/drawing.c`), when the timer is a chrono, `timer_get_length_ms() == 0` (a genuine stopwatch, not an overtime countdown), and `Lap Stopwatch` is disabled, show the time of day the stopwatch was started, prefixed with `@` and followed by the arrow (e.g. `@12:45-->`, formatted per `clock_is_24h_style()` like the footer) instead of `00:00-->`. The `length_ms == 0` check keeps an overtime countdown (`length_ms > 0`) on the existing base-length `MM:SS-->` branch, unaffected. For a running stopwatch derive the start as `epoch() - elapsed`; paused stopwatches reuse the same formula and accept the resulting pause drift (see design.md Open Questions, resolved). Keep `#if LAP_FEATURE` gating so aplite retains the previous `00:00-->` header
- [x] 9.4 Update `test_stopwatch_laps.py::TestSplitTotalDisplay::test_header_unchanged_when_lapping_disabled` (header is now `@HH:MM-->` start time, not `00:00-->`) and add a test that an overtime countdown's header stays `NN:NN-->` (no `@`, base length) with `Lap Stopwatch` disabled
- [x] 9.5 Label the `Lap Stopwatch` row in `src/js/pebble-js-app.js` so the aplite limitation is clear (e.g. `Lap Stopwatch (not on original Pebble)`)
- [x] 9.6 Update `docs/button-functions.md` and `README.md` for the new flash timing (1 s / 1 s, 5 s), the `@`-prefixed start-time header when lapping is disabled, and the aplite limitations (no laps / Delete all / warnings; 5 slots, 20-char names)
