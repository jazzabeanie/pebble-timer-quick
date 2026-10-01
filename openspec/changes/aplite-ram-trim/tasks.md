## 0. Prerequisite

- [ ] 0.1 Check that `list-alarm-takeover` is applied in the tree (its code is the reason for this change) and that the aplite link fails by about 1192 bytes; record the exact number
- [ ] 0.2 Record the basalt size (`arm-none-eabi-size build/basalt/pebble-app.elf`) before this change. Build without aplite for this (a temporary edit of `targetPlatforms` in `appinfo.json`), and restore the file

## 1. Failing tests

- [ ] 1.1 `test/Makefile`: add a second test binary, `run_test_timer_aplite`, that builds `src/timer.c` with `-DPBL_PLATFORM_APLITE` (and `src/mnemonic.c`, which must compile to nothing there), and add it to `make test`
- [ ] 1.2 `test/test_timer_aplite.c` (D1): `timer_slot_create()` on an empty app gives the name "Timer 1"; a second gives "Timer 2"; after "Timer 1" is deleted, a new timer gets "Timer 1"; no two slots have the same name after a sequence of delete and create; a slot with a saved mnemonic name keeps it and its number is not counted
- [ ] 1.3 `test/test_timer_aplite.c` (D5): `MAX_TIMERS` is 3; a fourth `timer_slot_create()` returns -1; `timer_persist_read()` with 5 saved slots (a fake persist store) loads slots 0 to 2 in order with their state, sets `timer_count` to 3, and deletes the keys of slots 3 and 4; a saved count of 3 or less loads as before; a negative count still resets
- [ ] 1.4 `test/test_timer_aplite.c`: the watch helpers work with 3 slots (`timer_ended_mask()`, `timer_find_ended_countdown()`, `timer_slot_delete()` mask shift), so the alarm-delivery code is tested in the aplite configuration too
- [ ] 1.5 Build check script or test (D2, D7): the aplite release binary has no `TEST_STATE` text (`strings build/aplite/pebble-app.bin`); the basalt release binary has it; an aplite test build has it
- [ ] 1.5a (D8) Build check: the aplite binary has no reference to `app_message_open` (map file or `arm-none-eabi-nm` on the elf); the basalt binary has it
- [ ] 1.6 Run the new tests and confirm they fail (1.2 fails on the mnemonic name, 1.3 on the reset of all timers, 1.5 because aplite does not link)

## 2. Implementation

- [ ] 2.1 (D2) `src/utility.h` / `src/utility.c`: add `TEST_LOGS` (0 on aplite unless `TEST_BUILD` is defined, 1 otherwise); with 0, `TEST_LOG` expands to a checked expression that is not run, and `test_log_state()` is a macro that expands to nothing; `prv_get_mode_name()` and the `test_log_state()` body are inside `#if TEST_LOGS`
- [ ] 2.2 (D2) `src/main.c`, `src/timer.c`: change the plain `APP_LOG` debug and info lines ("Up long press", "Reverse direction", "Timer data", "Old version") to `TEST_LOG`; keep the error line in `assert()`
- [ ] 2.3 (D3) `wscript`: when the environment variable `QT_TEST_BUILD` is `1`, add `-DTEST_BUILD` to the C flags of every platform; print one line that says "test build" or "release build"
- [ ] 2.4 (D3) `test/functional/conftest.py`: set `QT_TEST_BUILD=1` in `EmulatorHelper.build()`
- [ ] 2.5 Build aplite and record the result after the log trim (D6: measure after each trim)
- [ ] 2.6 (D1) `src/timer.h`: add `MNEMONIC_FEATURE` (1 everywhere, 0 on aplite); `src/mnemonic.c`: put the tables and `mnemonic_generate_name()` inside `#if MNEMONIC_FEATURE`
- [ ] 2.7 (D1) `src/timer.c`: with `MNEMONIC_FEATURE` 0, `timer_assign_name()` writes "Timer N" with the lowest N that no other slot's name uses; no `localtime()` call on that path
- [ ] 2.8 Build aplite and record the result after the mnemonic trim
- [ ] 2.9 (D5) `src/timer.h`: `MAX_TIMERS` 3 on aplite; update the comment there
- [ ] 2.10 (D5) `src/timer.c`: in `timer_persist_read()`, when the saved count is more than `MAX_TIMERS`, load the first `MAX_TIMERS` slots, set the count, and delete the persist keys of the others; keep the reset for a negative count
- [ ] 2.10a (D8) `src/settings.h`: add `SETTINGS_SYNC_FEATURE` (1 everywhere, 0 on aplite); `src/settings.c`: with 0, leave out `prv_inbox_received()`, the request and retry functions, the retry timer, and the `app_message_*` calls in `settings_init()`; `settings_init()` still sets the defaults, loads saved settings, and saves them
- [ ] 2.10b (D8) Check that no aplite functional test sends a setting (`send_app_message_int`); skip on aplite any test that does
- [ ] 2.11 Build aplite (release) and record the heap and the code size. If the heap is below 1600 bytes, take the D6 steps (32-bit time math where safe, shorter strings) and measure again; stop and report before any step that touches alarm-delivery code
- [ ] 2.12 (D4) Build the aplite test build and record the heap. Launch it on the aplite emulator and check the logs for `TEST_STATE:init`, `App fault`, and failed allocations. If it does not run, take the D4 fallback steps in order, and report if step 2 is reached

## 3. Tests on aplite and existing tests

- [ ] 3.1 `test/functional/test_mnemonic_names.py`: skip on aplite, and add a short aplite test that the first timer's row name is "Timer 1" (`name0` in `timer_list_show`)
- [ ] 3.2 Check every functional test that needs more than 3 slots or a "New Timer" row with 3 or more saved timers (`test_timer_list.py`, `test_hold_down_delete.py`, `test_stopwatch_laps.py`, `test_list_alarm_takeover.py`); skip or adjust on aplite. `test_list_alarm_takeover.py` uses at most 2 saved timers plus the implicit slot, which is exactly 3: check that each of its tests still gets a "New Timer" row on aplite
- [ ] 3.3 Re-run the new unit tests and the build check and confirm they pass
- [ ] 3.4 Run all unit tests (both timer binaries)

## 4. Verify

- [ ] 4.1 Aplite sizes (closes `list-alarm-takeover` task 3.3): record `Total footprint in RAM`, the heap, and `arm-none-eabi-size` for the aplite release build and the aplite test build, before and after this change, in this file
- [ ] 4.2 Aplite heap with a marked list row (closes the rest of task 3.3): run the release build on the aplite emulator with a held alarm in the Timer List; take a screenshot that shows the bell icon; check the logs for `App fault` and failed allocations (the release build has no `TEST_STATE` lines; use the emulator's own log output)
- [ ] 4.3 Aplite functional suite with the test build (closes `list-alarm-takeover` task 3.4): run the full suite with `--platform=aplite`, including `test_list_alarm_takeover.py` and `test_no_guard_on_aplite_after_takeover`; check the logs for `App fault` and failed allocations; compare the failures with a baseline run if one can be made
- [ ] 4.3a (D8) Basalt: check that settings sync still works (a functional test that sends a setting passes, for example a lap stopwatch test)
- [ ] 4.4 Basalt: run the full functional suite and compare with the result of `list-alarm-takeover` (172 tests, 168 passed, 4 intermittent icon tests); compare the basalt size with task 0.2 (the release binary must not change in size by more than the `APP_LOG` lines of 2.2)
- [ ] 4.5 Check that no alarm-delivery function is inside an aplite `#if`: `prv_watch_arm()`, `main_show_alarm()`, the D12 block of `prv_terminate()`, `prv_update_alarm_marks()`, `prv_alarm_take_over()`, and the watch helpers of `timer.c` are in the aplite map file or binary
- [ ] 4.6 Mark tasks 3.3 and 3.4 of `openspec/changes/list-alarm-takeover/tasks.md` complete, with a pointer to the numbers recorded here

## 5. Docs

- [ ] 5.1 `docs/button-functions.md`: in the Timer List section, change the aplite slot limit from 5 to 3; add that aplite timers are named "Timer N"; note that the aplite release build has no test logs and how to make a test build (`QT_TEST_BUILD=1 pebble build`); in the Settings section, add that the phone settings page has no effect on aplite (it uses the defaults)
- [ ] 5.2 `README.md`: add the test build option to the test instructions, and the aplite limits (3 timers, "Timer N" names, default settings only)
- [ ] 5.3 Update the comments in `src/timer.h` and `src/main.h` that give aplite RAM numbers
