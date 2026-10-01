## 0. Prerequisite

- [x] 0.1 Check that `list-alarm-takeover` is applied in the tree (its code is the reason for this change) and that the aplite link fails by about 1192 bytes; record the exact number
- [x] 0.2 Record the basalt size (`arm-none-eabi-size build/basalt/pebble-app.elf`) before this change. Build without aplite for this (a temporary edit of `targetPlatforms` in `appinfo.json`), and restore the file

## 1. Failing tests

- [x] 1.1 `test/Makefile`: add a second test binary, `run_test_timer_aplite`, that builds `src/timer.c` with `-DPBL_PLATFORM_APLITE` (and `src/mnemonic.c`, which must compile to nothing there), and add it to `make test`
- [x] 1.2 `test/test_timer_aplite.c` (D1): `timer_slot_create()` on an empty app gives the name "Timer 1"; a second gives "Timer 2"; after "Timer 1" is deleted, a new timer gets "Timer 1"; no two slots have the same name after a sequence of delete and create; a slot with a saved mnemonic name keeps it and its number is not counted
- [x] 1.3 `test/test_timer_aplite.c` (D5): `MAX_TIMERS` is 3; a fourth `timer_slot_create()` returns -1; `timer_persist_read()` with 5 saved slots (a fake persist store) loads slots 0 to 2 in order with their state, sets `timer_count` to 3, and deletes the keys of slots 3 and 4; a saved count of 3 or less loads as before; a negative count still resets
- [x] 1.4 `test/test_timer_aplite.c`: the watch helpers work with 3 slots (`timer_ended_mask()`, `timer_find_ended_countdown()`, `timer_slot_delete()` mask shift), so the alarm-delivery code is tested in the aplite configuration too
- [x] 1.5 Build check script or test (D2, D7): the aplite release binary has no `TEST_STATE` text (`strings build/aplite/pebble-app.bin`); the basalt release binary has it; an aplite test build has it
- [x] 1.5a (D8) Build check: the aplite binary has no reference to `app_message_open` (map file or `arm-none-eabi-nm` on the elf); the basalt binary has it
- [x] 1.6 Run the new tests and confirm they fail (1.2 fails on the mnemonic name, 1.3 on the reset of all timers, 1.5 because aplite does not link)

## 2. Implementation

- [x] 2.1 (D2) `src/utility.h` / `src/utility.c`: add `TEST_LOGS` (0 on aplite unless `TEST_BUILD` is defined, 1 otherwise); with 0, `TEST_LOG` expands to a checked expression that is not run, and `test_log_state()` is a macro that expands to nothing; `prv_get_mode_name()` and the `test_log_state()` body are inside `#if TEST_LOGS`
- [x] 2.2 (D2) `src/main.c`, `src/timer.c`: change the plain `APP_LOG` debug and info lines ("Up long press", "Reverse direction", "Timer data", "Old version") to `TEST_LOG`; keep the error line in `assert()`
- [x] 2.3 (D3) `wscript`: when the environment variable `QT_TEST_BUILD` is `1`, add `-DTEST_BUILD` to the C flags of every platform; print one line that says "test build" or "release build"
- [x] 2.4 (D3) `test/functional/conftest.py`: set `QT_TEST_BUILD=1` in `EmulatorHelper.build()`
- [x] 2.5 Build aplite and record the result after the log trim (D6: measure after each trim)
- [x] 2.6 (D1) `src/timer.h`: add `MNEMONIC_FEATURE` (1 everywhere, 0 on aplite); `src/mnemonic.c`: put the tables and `mnemonic_generate_name()` inside `#if MNEMONIC_FEATURE`
- [x] 2.7 (D1) `src/timer.c`: with `MNEMONIC_FEATURE` 0, `timer_assign_name()` writes "Timer N" with the lowest N that no other slot's name uses; no `localtime()` call on that path
- [x] 2.8 Build aplite and record the result after the mnemonic trim
- [x] 2.9 (D5) `src/timer.h`: `MAX_TIMERS` 3 on aplite; update the comment there
- [x] 2.10 (D5) `src/timer.c`: in `timer_persist_read()`, when the saved count is more than `MAX_TIMERS`, load the first `MAX_TIMERS` slots, set the count, and delete the persist keys of the others; keep the reset for a negative count
- [x] 2.10a (D8) `src/settings.h`: add `SETTINGS_SYNC_FEATURE` (1 everywhere, 0 on aplite); `src/settings.c`: with 0, leave out `prv_inbox_received()`, the request and retry functions, the retry timer, and the `app_message_*` calls in `settings_init()`; `settings_init()` still sets the defaults, loads saved settings, and saves them
- [x] 2.10b (D8) Check that no aplite functional test sends a setting (`send_app_message_int`); skip on aplite any test that does
- [x] 2.11 Build aplite (release) and record the heap and the code size. If the heap is below 1600 bytes, take the D6 steps (32-bit time math where safe, shorter strings) and measure again; stop and report before any step that touches alarm-delivery code
- [x] 2.12 (D4) Build the aplite test build and record the heap. Launch it on the aplite emulator and check the logs for `TEST_STATE:init`, `App fault`, and failed allocations. If it does not run, take the D4 fallback steps in order, and report if step 2 is reached

## 2a. Found during the work: the aplite fault and the test build (D4, D9, D10)

- [x] 2a.1 (D4) Launch the aplite test build: it does not start (reported heap 668, true heap about 0). Measure the true heap with a scratch build that logs `heap_bytes_free()`: it is about 680 bytes less than the reported heap
- [x] 2a.2 Find the cause of `Invalid pointer: (../src/animation.c:141)` and `App fault` on aplite (the release build and old `master`): text field animations pile up until the heap is full
- [x] 2a.3 (D10) Failing tests: `test/test_animation.c` (one allocation per animation; a failed allocation sets the value to its end and does not stop the app; two animations of one value still run in order; stop all leaves no stale list) and `test_text_layout_change_does_not_pile_up_animations` in `test/test_drawing.c`; confirm they fail
- [x] 2a.4 (D10) `src/animation.c`: `from` and `to` inside the node, one allocation, no stop of the app on a failed allocation, `animation_stop_all()` clears the list and the timer, the timer callback reads the next node before a step. `src/drawing.c`: stop a text field's animation before its new one starts. Confirm the tests pass
- [x] 2a.5 Scripted run of the aplite release build after the fix: no `App fault`; the Timer List shows the bell icon on a held row; Back shows the alarm in the main window
- [x] 2a.6 (D9) Measure the button hint icons on aplite in a scratch copy (release heap 3052 to 5024, test build 792 to 2748) and ask the user: the user chose the icon trim
- [x] 2a.7 (D9) Failing test: `run_test_drawing_aplite` (`test/test_drawing.c` built with `-DPBL_PLATFORM_APLITE`), `test_aplite_loads_and_draws_no_icons`; confirm it fails (35 loads)
- [x] 2a.8 (D9) `src/drawing.h`: `BUTTON_ICONS_FEATURE` (0 on aplite); `src/drawing.c`: the icon fields, loads, destroys, position code, draw functions, and the alarm icons block are inside `#if BUTTON_ICONS_FEATURE`. Confirm the test passes
- [x] 2a.9 (D9) Functional tests that check button hint icons: skip on aplite
- [x] 2a.11 (D9) `appinfo.json`: the repeat glyph (`IMAGE_ICON_REPEAT_ENABLE`, used by the Timer List) is a `bitmap` resource on aplite (stored as PBI, no decode) and stays a `png` resource on the other platforms. Before this, each Timer List open on aplite logged two failed PNG loads. An old `build/` directory keeps the old resource: run `pebble clean` once
- [x] 2a.12 `test/functional/test_backlight.py`: remove the aplite "expected failure" mark of `test_backlight_on_during_alarm` (the memory fault it names is fixed; the test passes on aplite). `test_create_timer.py::test_initial_state_shows_new`: accept the OCR misread "Nex" on aplite (the screenshot shows "New"). `test_repeat_counter_visibility.py::test_editrepeat_up_region_empty_during_flash_off`: skip on aplite (an icon test)
- [x] 2a.13 (D3) `test/functional/conftest.py`: `build()` fails if the build is not a test build (the build output line, and `TEST_STATE` in the aplite binary); at the end of a session that made a test build, a release build is made again so that `build/` does not keep the test build (`QT_KEEP_TEST_BUILD=1` skips this); `--collect-only` no longer stops the emulators of another session
- [x] 2a.10 `test/functional/conftest.py`: report every `App fault`, failed allocation, and failed image load of the app at the end of a run

## 3. Tests on aplite and existing tests

- [x] 3.1 `test/functional/test_mnemonic_names.py`: skip on aplite, and add a short aplite test that the first timer's row name is "Timer 1" (`name0` in `timer_list_show`)
- [x] 3.2 Check every functional test that needs more than 3 slots or a "New Timer" row with 3 or more saved timers (`test_timer_list.py`, `test_hold_down_delete.py`, `test_stopwatch_laps.py`, `test_list_alarm_takeover.py`); skip or adjust on aplite. `test_list_alarm_takeover.py` uses at most 2 saved timers plus the implicit slot, which is exactly 3: check that each of its tests still gets a "New Timer" row on aplite
- [x] 3.3 Re-run the new unit tests and the build check and confirm they pass
- [x] 3.4 Run all unit tests (both timer binaries)

## 4. Verify

- [x] 4.1 Aplite sizes (closes `list-alarm-takeover` task 3.3): record `Total footprint in RAM`, the heap, and `arm-none-eabi-size` for the aplite release build and the aplite test build, before and after this change, in this file
- [x] 4.2 Aplite heap with a marked list row (closes the rest of task 3.3): run the release build on the aplite emulator with a held alarm in the Timer List; take a screenshot that shows the bell icon; check the logs for `App fault` and failed allocations (the release build has no `TEST_STATE` lines; use the emulator's own log output)
- [x] 4.3 Aplite functional suite with the test build (closes `list-alarm-takeover` task 3.4): run the full suite with `--platform=aplite`, including `test_list_alarm_takeover.py` and `test_no_guard_on_aplite_after_takeover`; check the logs for `App fault` and failed allocations; compare the failures with a baseline run if one can be made
- [x] 4.3a (D8) Basalt: check that settings sync still works (a functional test that sends a setting passes, for example a lap stopwatch test)
- [x] 4.4 Basalt: run the full functional suite and compare with the result of `list-alarm-takeover` (172 tests, 168 passed, 4 intermittent icon tests); compare the basalt size with task 0.2 (the release binary must not change in size by more than the `APP_LOG` lines of 2.2)
- [x] 4.5 Check that no alarm-delivery function is inside an aplite `#if`: `prv_watch_arm()`, `main_show_alarm()`, the D12 block of `prv_terminate()`, `prv_update_alarm_marks()`, `prv_alarm_take_over()`, and the watch helpers of `timer.c` are in the aplite map file or binary
- [x] 4.6 Mark tasks 3.3 and 3.4 of `openspec/changes/list-alarm-takeover/tasks.md` complete, with a pointer to the numbers recorded here

## 5. Docs

- [x] 5.1 `docs/button-functions.md`: in the Timer List section, change the aplite slot limit from 5 to 3; add that aplite timers are named "Timer N"; note that the aplite release build has no test logs and how to make a test build (`QT_TEST_BUILD=1 pebble build`); in the Settings section, add that the phone settings page has no effect on aplite (it uses the defaults)
- [x] 5.2 `README.md`: add the test build option to the test instructions, and the aplite limits (3 timers, "Timer N" names, default settings only)
- [x] 5.3 Update the comments in `src/timer.h` and `src/main.h` that give aplite RAM numbers

## Results (2026-10-01)

### Measurements (aplite, `pebble build`)

"Heap" is `Free RAM available (heap)` of the build report. The true heap on the emulator is about 680 bytes less (the system line `Heap Usage for App <QuickTimer: Total Size ...>` gave 2132 for a reported 2928, 2060 for 2736, 1892 for 2568, 2372 for 3052).

| Step | text | data | bss | Total | Heap |
|---|---|---|---|---|---|
| 0.1 Before this change | | | | does not link | overflow 1192 |
| 2.5 After the log trim (C) | 21484 | 1292 | 728 | 23504 | 1072 |
| 2.8 After the mnemonic trim (B) | 20888 | 956 | 728 | 22572 | 2004 |
| 2.11 After `MAX_TIMERS` 3 (D) and the settings trim (S) | 20084 | 956 | 608 | 21648 | 2928 |
| 2a.4 After the animation fix (D10) | 19960 | 956 | 608 | 21524 | 3052 |
| 2a.8 After the icon trim (D9): **release build** | 17988 | 956 | 472 | 19416 | **5160** |
| 2a.8 **Test build** (`QT_TEST_BUILD=1`) | 20264 | 956 | 472 | 21692 | **2884** |

The log trim saved 2264 bytes, not the 1408 that the proposal measured: the `if (0)` form of `TEST_LOG` also removes the code that builds the arguments, and the plain `APP_LOG` lines went too.

The test log output costs 2276 bytes on aplite (20264 - 17988).

### Basalt (0.2 and 4.4)

| Build | text | data | bss | Total | Heap |
|---|---|---|---|---|---|
| 0.2 Before this change | 27788 | 1296 | 3384 | 32468 | 33068 |
| After the four trims (aplite only) | 27788 | 1296 | 3384 | 32468 | 33068 |
| After the animation fix (shared code) | 27664 | 1296 | 3384 | 32344 | 33192 |
| After the icon trim (aplite only) | 27664 | 1296 | 3384 | 32344 | 33192 |

The only change on basalt is the animation fix (124 bytes less).

### 2.12 / 2a.1: the aplite test build with the first four trims

Reported heap 668. The app did not start on the aplite emulator: no log line, and the launcher stayed on screen. D4 step 1 could save about 550 bytes (the 4 plain debug lines, the `list-alarm-takeover` lines through `test_log_state()`, a shorter format), which gives a true heap near 500 bytes: not enough. The icon trim (D9, user decision) solved it.

### 2a.2 / 2a.5: the aplite fault

- Old `master` (`ea1e389`, reported heap 1273) on the aplite emulator: `Invalid pointer: (../src/animation.c:141)` and `App fault` at launch.
- This change with the first four trims (reported heap 2928): the same fault at the first hold of Select.
- A scratch build that logs the free heap showed the cause: free heap 1488 after init, then 56 bytes less at each `animation_grect_start()` until 0.
- After the fix: the scripted run (New, pause, hold Select, +30 s, start, exit, open, wait in the Timer List, Back, Select, Back) has no `App fault`. The Timer List shows the bell icon on the held timer's row. Back shows the alarm in the main window.

### 3.2: tests that need more than 3 slots on aplite

No change was needed. Every test of `test_list_alarm_takeover.py` uses at most 3 slots and passes on aplite. `test_timer_list.py` and `test_hold_down_delete.py` pass on aplite. `test_stopwatch_laps.py` and the "Delete all" tests skip on aplite (`LAP_FEATURE`). 2.10b: every test that sends a setting skips on aplite.

### 3.3 / 3.4: unit tests and build check

- `make -C test test`: 228 tests pass in 9 binaries (`run_test_timer` 32, `run_test_main` 99, `run_test_drawing` 13, `run_test_timer_multi` 39, `run_test_mnemonic` 4, `run_test_epoch` 2, `run_test_timer_aplite` 18, `run_test_animation` 9, `run_test_drawing_aplite` 12).
- `test/check_build.sh`: all 10 checks pass.

### 4.1: final sizes (closes `list-alarm-takeover` task 3.3)

| Build | text | data | bss | Total footprint in RAM | Heap |
|---|---|---|---|---|---|
| Aplite, before `list-alarm-takeover` | | | | 23303 | 1273 |
| Aplite, with `list-alarm-takeover`, before this change | | | | does not link | overflow 1192 |
| Aplite release, after this change | 17988 | 956 | 472 | 19416 | 5160 |
| Aplite test build, after this change | 20264 | 956 | 472 | 21692 | 2884 |
| Basalt, before this change | 27788 | 1296 | 3384 | 32468 | 33068 |
| Basalt, after this change | 27664 | 1296 | 3384 | 32344 | 33192 |

### 4.2: aplite release build with a marked list row

Scripted run on the aplite emulator (release build, fixed waits, no test logs): a 30 s countdown, exit, open, wait in the Timer List until the countdown ends, Back, Select, Back. Screenshots: `aplite-release-run.png` in this directory (frame 5: the bell icon on the held row; frames 6 and 7: the alarm in the main window after Back). The emulator log has no `App fault`, no failed allocation, and no failed image load. System line at exit: `Heap Usage for App <QuickTimer: Total Size <4484B> Used <1308B>`, so the peak heap use with the list and the bell icon is 1308 of 4484 bytes.

### 4.3: aplite functional suite (closes `list-alarm-takeover` task 3.4)

`pytest --platform=aplite` with the test build: 110 passed, 2 failed, 1 expected failure, no `App fault`, no failed allocation. All of `test_list_alarm_takeover.py` passed (17) or skipped (2, the "Delete all" row), including `test_no_guard_on_aplite_after_takeover`. No baseline exists for a comparison: old `master` faults on aplite at launch.

The two failures and the expected failure are handled in 2a.12, and the 156 failed-PNG lines of that run (the repeat glyph of the Timer List) in 2a.11. After those changes, a second run of `test_backlight.py`, `test_timer_list.py`, `test_mnemonic_names.py`, `test_repeat_counter_visibility.py`, and `test_initial_state_shows_new` on aplite: 23 passed, 0 failed, and the summary "app faults and failed allocations" says none. The full aplite suite was not run again after 2a.11 and 2a.12.

### 4.3a / 4.4: basalt

`pytest --platform=basalt` (before the icon trim and 2a.11, which are aplite only): 168 passed, 4 failed, no app faults. The 4 failures passed on a second run: `test_editrepeat_back_icon`, `test_new_reverse_back_icon` (the known intermittent icon tests), `test_timer_counts_down` (OCR), and `test_non_active_countdown_wakes_the_app` (my own mistake: a `pytest --collect-only` in a second shell killed the emulator during that test). This is the same level as the result of `list-alarm-takeover` (172 tests, 168 passed, 4 intermittent). Settings sync on basalt works: the lap stopwatch tests, which send a setting, pass.

After 2a.11 (the resource entry of the repeat glyph), on basalt: `test_repeat_list_icon.py`, `test_timer_list.py`, `TestCountingIcons`, `test_wakeup_guard.py`: 22 passed, 0 failed.

The basalt binary has the same size before and after the icon trim (32344). Its hash is not the same, because the log lines carry `__LINE__` and lines moved in `drawing.c`.

### 4.5: alarm-delivery code in the aplite release binary

`arm-none-eabi-nm build/aplite/pebble-app.elf` has `prv_watch_arm`, `main_show_alarm`, `prv_update_alarm_marks`, `prv_alarm_take_over`, `prv_scan_countdowns`, `timer_ended_mask`, `timer_find_ended_countdown`, `timer_next_ending_slot`, `timer_next_watched_end_ms`, `timer_watch_add_running`, `timer_watch_restore`, `timer_alarm_mark_shown`, `timer_check_elapsed`, `wakeup_schedule`, and `vibes_enqueue_custom_pattern`. `prv_terminate()` (the D12 block) is inlined into `main`. No alarm-delivery function is inside an aplite `#if`.
