## Why

The `list-alarm-takeover` change adds about 2.5 KB of alarm-delivery code. On aplite (24 KB app region) the app no longer links: `region APP overflowed by 1192 bytes`. A failed aplite link also stops `pebble build` for every other platform, so the app cannot be built at all.

The rule for aplite is that no timer may fail to ring, so the alarm-delivery code stays. The space must come from RAM that has nothing to do with alarms. This is the follow-up that design D6 of `list-alarm-takeover` planned.

Measured on 2026-10-01 (aplite, with `list-alarm-takeover` applied):

| Build | Result |
|---|---|
| Before `list-alarm-takeover` | 23303 of 24576 bytes, heap 1273 |
| With `list-alarm-takeover`, no trim | overflow 1192 |
| No mnemonic names | saves 1016 |
| No test log output | saves 1408 |
| `MAX_TIMERS` 5 to 3 | saves 112 |
| No phone settings message code | saves 848 |
| The first three | heap 1344 |
| All four | heap about 2190 |

Found during the work (2026-10-01), on the aplite emulator:

- The app faults on aplite at the first screen change, also before `list-alarm-takeover` (old `master`: `Invalid pointer: (../src/animation.c:141)`, then `App fault`). Each text layout change starts 7 animations of about 56 bytes and does not stop the old ones. A few changes in quick succession fill the heap, the next allocation fails, and the app stops. A stopped app does not ring.
- The true heap is about 680 bytes less than the build reports (`Free RAM available (heap)` 2928 gave a heap of 2132 bytes). So a test build with a reported heap of 668 bytes cannot start.
- The button hint icons are stored as PNG. Aplite cannot decode most of them (62 `PNG decoding failed` lines in one run); only a few show.

| Build (aplite) | Release heap | Test build heap |
|---|---|---|
| The four trims | 2928 | 668 (does not start) |
| + animation fix | 3052 | 792 (does not start) |
| + no button hint icons | 5160 | 2884 |

## What Changes

The trims apply to aplite only. The other platforms do not change, except for the animation fix, which is in shared code and does not change what the user sees.

- **No mnemonic names on aplite.** A new timer gets the name "Timer N" (N is the lowest number that no other timer uses). `src/mnemonic.c` and its lookup tables are not linked on aplite.
- **No test log output in the aplite release build.** `TEST_LOG` and `test_log_state()` compile to nothing there. A test build option turns them on again, so that the functional tests can still read `TEST_STATE` lines.
- **No phone settings message code on aplite.** The code that receives settings from the phone is compiled out there. It has no effect on aplite today: `app_message_open()` fails with `APP_MSG_OUT_OF_MEMORY`, because the inbox needs 8200 bytes and the heap has about 1.3 KB (checked on the aplite emulator, 2026-10-01). Aplite uses the default settings, as it does now. This trim is the one that puts the aplite heap above the ~1.6 KB floor.
- **BREAKING (aplite only): 3 timer slots, not 5.** `MAX_TIMERS` goes from 5 to 3 on aplite. If more than 3 timers are saved from an older version, the first 3 are loaded and the others are dropped.
- **No button hint icons on aplite** (user decision, 2026-10-01). The icons at the screen edges that show what each button does, and the icons shown during an alarm, are compiled out there. Most of them cannot load on aplite today. This gives the heap that the test build needs to run. The bell icon of the Timer List stays.
- **An animation never stops the app.** A text field's running animation is replaced, not added to. An animation uses one allocation, not three. If the allocation fails, the value jumps to its end and the app goes on. This is in shared code; the motion on screen is the same.
- **Finish the aplite verification of `list-alarm-takeover`** (its open tasks 3.3 and 3.4): record the aplite heap and code size, also with a marked list row, and run the unit tests and the functional suite on aplite, including `test_list_alarm_takeover.py`.
- No alarm-delivery code is removed or gated: the watch mask, the held alarm, the takeover, the list icon and five pulses, the next-event wakeup with its backups, and the pending alarm all stay on aplite.
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
- `aplite-footprint`: The aplite build fits its 24 KB app region with a minimum heap, the alarm-delivery code is never the code that is trimmed, the test log output is a build option on aplite, aplite runs with the default settings (no phone settings sync), aplite has no button hint icons, and a full heap does not stop the app.

### Modified Capabilities
- `mnemonic-naming`: On aplite a new timer gets the name "Timer N" instead of a mnemonic name. The duplicate-name suffix rule does not apply there.
- `multi-timer-management`: The aplite slot limit goes from 5 to 3. More than 3 saved timers from an older version are cut to the first 3.

## Impact

- `src/timer.h`: `MAX_TIMERS` 3 on aplite; a new `MNEMONIC_FEATURE` flag (0 on aplite).
- `src/timer.c`: `timer_assign_name()` gives "Timer N" when `MNEMONIC_FEATURE` is 0; `timer_persist_read()` loads the first `MAX_TIMERS` slots when more are saved, instead of resetting all timers.
- `src/mnemonic.c`: compiled out on aplite.
- `src/utility.h` / `src/utility.c`: a `TEST_LOGS` flag (0 in the aplite release build, 1 everywhere else and in a test build). `TEST_LOG` and `test_log_state()` compile to nothing when it is 0.
- `src/main.c`, `src/timer.c`: the three plain `APP_LOG` debug lines go through `TEST_LOG`, so they also leave the aplite release build.
- `src/settings.h` / `src/settings.c`: a `SETTINGS_SYNC_FEATURE` flag (0 on aplite). With 0, the AppMessage code is compiled out and `settings_init()` only loads the defaults.
- `src/drawing.h` / `src/drawing.c`: a `BUTTON_ICONS_FEATURE` flag (0 on aplite). With 0, the icon bitmaps are not loaded and the icon draw code is compiled out. A text field's animation is stopped before a new one starts.
- `src/animation.c`: one allocation per animation; a failed allocation sets the value to its end.
- `test/Makefile`: new unit test binaries for the aplite configuration (`run_test_timer_aplite`, `run_test_drawing_aplite`) and for the animations (`run_test_animation`).
- `wscript`: a build option (environment variable) that defines `TEST_BUILD`.
- `test/functional/conftest.py`: builds with the test option. Tests that depend on mnemonic names or on 5 slots skip or adjust on aplite.
- `openspec/changes/list-alarm-takeover/tasks.md`: tasks 3.3 and 3.4 are completed by this change.
- Saved data: the timer data format does not change, so `PERSIST_VERSION` stays the same.
- Risk: the aplite test build keeps the logs (about 2.3 KB), so its heap is much less than that of the release build. With the first four trims it did not start. The icon trim (D9) gives it a heap of 2884 bytes. The design covers this (D4).
