## Context

The aplite app region is 24576 bytes. It holds the code, the data, and the heap. Before `list-alarm-takeover` the app used 23303 bytes and had a heap of 1273 bytes, already below the ~1.6 KB floor that earlier work found (text rendering can fail below about 1.4 KB).

`list-alarm-takeover` adds about 2.5 KB on aplite (`main.c` +820, `timer.c` +776, `timer_list.c` +840 bytes of text). The link fails by 1192 bytes. Because `pebble build` builds every platform, no platform can be built now.

The user rule (2026-09-26): alarm reliability is more important than RAM on aplite. No alarm-delivery code may be trimmed. Trim RAM that has nothing to do with alarms.

Measurements, each made on aplite in a scratch copy of the tree with `list-alarm-takeover` applied (2026-10-01):

| Trim | Saves (bytes) | Result |
|---|---|---|
| None | 0 | overflow 1192 |
| B: no mnemonic names (a stub that writes "Timer N", no unique-number search) | 1016 | overflow 176 |
| C: no `TEST_LOG` / `test_log_state()` output | 1408 | heap 216 |
| D: `MAX_TIMERS` 5 to 3 | 112 | overflow 1080 |
| B + D (logs kept) | 1128 | overflow 64 |
| B + C | 2424 | heap 1232 |
| B + C + D | 2536 | heap 1344 |
| S: no phone settings message code (measured with B + D, logs kept) | 848 | heap 784 |
| B + C + D + S (sum of the measured savings) | 3384 | heap about 2190 |

The settings message code does not work on aplite today. Checked on the aplite emulator on 2026-10-01 with a baseline build and one added log line: `app_message_open(app_message_inbox_size_maximum(), 128)` returns `APP_MSG_OUT_OF_MEMORY` (4096), because the inbox needs 8200 bytes and the heap has about 1.3 KB. No settings message is received. On basalt the same call returns 0 and the messages arrive.

Existing patterns for platform flags: `LAP_FEATURE` in `src/timer.h` and `WAKEUP_GUARD_FEATURE` in `src/main.h` (1 everywhere, 0 on aplite). The build uses `-ffunction-sections` and `--gc-sections`, so a function that nothing calls is dropped.

## Goals / Non-Goals

**Goals:**
- The aplite release build links, with a heap of at least 1600 bytes (the floor that earlier work found; the four trims are measured at about 2190).
- All alarm-delivery code of `list-alarm-takeover` stays on aplite.
- The other platforms do not change: same names, same logs, same slot count.
- The aplite verification that `list-alarm-takeover` left open is done: sizes recorded, tests run.

**Non-Goals:**
- Phone settings sync on aplite. It does not work today, and this change removes its code there.
- Changes to alarm behavior.
- Size work on other platforms.

## Decisions

### D1. Mnemonic names are a platform feature (`MNEMONIC_FEATURE`)

Add `MNEMONIC_FEATURE` to `src/timer.h`: 1 everywhere, 0 on aplite. With 0:

- `timer_assign_name()` writes "Timer N". N is the lowest number from 1 that no other slot's name uses. With at most 3 slots, a small loop finds it.
- The whole body of `src/mnemonic.c` is inside `#if MNEMONIC_FEATURE`, so the two tables (336 bytes of data) and `mnemonic_generate_name()` are not in the aplite binary. `localtime()` is no longer called from `timer_assign_name()`.

The name field stays (20 bytes on aplite). The Timer List, the main window, and the lap prefix (not on aplite) read it as before.

"Timer N" with the lowest free number, not the slot number plus one: slots move down when a timer is deleted, so a number from the slot index can give two timers the same name.

*Alternatives:*
- Name by start time ("14:30"). Rejected: it needs `localtime()` and a format, and it costs more than a number.
- No name at all on aplite. Rejected: the list would have rows with no first line, and the draw code would need a second layout.
- Smaller tables (fewer words). Rejected: it saves less and changes the names on every platform.

### D2. Test log output is a flag (`TEST_LOGS`)

Add `TEST_LOGS` to `src/utility.h`:

```c
#if defined(PBL_PLATFORM_APLITE) && !defined(TEST_BUILD)
  #define TEST_LOGS 0
#else
  #define TEST_LOGS 1
#endif
```

With `TEST_LOGS` 0:

- `TEST_LOG(level, fmt, ...)` expands to an expression that the compiler checks but does not run (`(void)sizeof(printf(fmt, ...))` or an equal form). The arguments still count as used, so `-Werror=unused-but-set-variable` does not fail (this error occurred in the measurement build), and the format strings are not in the binary.
- `test_log_state(event)` is a macro that expands to nothing, so the event name strings are not in the binary either. `prv_get_mode_name()` in `utility.c` goes with it.

The three plain `APP_LOG` debug lines in `src/main.c` and the "Old version" line in `src/timer.c` change to `TEST_LOG`, so they also leave the aplite release build. The `APP_LOG` error line in `assert()` stays.

The flag is by platform, not global: the other platforms keep their logs in the release build, as today. This keeps the change to aplite only.

*Alternative:* remove the logs on every platform in release builds. Rejected for this change: it changes the other platforms and their test flow, and they do not need the space.

### D3. The test build option

`wscript` reads an environment variable, `QT_TEST_BUILD`. When it is `1`, the build adds `-DTEST_BUILD` to the C flags of every platform. `test/functional/conftest.py` sets it in `EmulatorHelper.build()`.

The build output is the same `build/*.pbw`. A release build is a plain `pebble build`. The build prints one line that says which kind it is, so a test build is not shipped by mistake.

*Alternative:* a second `wscript` or a `--test` command line option. Rejected: `pebble build` does not pass unknown options to waf in a stable way, and an environment variable needs no change to how the tool is called.

### D4. The aplite test build

The aplite test build is the release build plus the test log output (1408 bytes). With all four trims, its heap is about 784 bytes (measured with B, D, and S applied and the logs kept). The release build is the product; the test build exists only to run the tests.

784 bytes is below the heap of every build that is known to run. So the first verify step is to launch the aplite test build and check for `App fault` and failed allocations. If it does not run:

1. Use `test_log_state()` for the log lines of `list-alarm-takeover` that have their own format string, and shorten the `test_log_state()` format on aplite.
2. If it still does not run, report the numbers. Aplite is then verified by the unit tests (the logic is the same on every platform) and by a manual run of the release build on the aplite emulator with screenshots. Do not trim alarm-delivery code to make a test build fit.

### D5. Three slots on aplite, and saved data from 5 slots

`MAX_TIMERS` is 3 on aplite. Each slot is 56 bytes of bss.

Today `timer_persist_read()` resets all timers when the saved count is more than `MAX_TIMERS`. After this change an aplite user with 4 or 5 saved timers would lose all of them at the first launch. Change the rule: when the saved count is more than `MAX_TIMERS`, load the first `MAX_TIMERS` slots, set the count to `MAX_TIMERS`, and delete the persist keys of the others. The check for a negative count stays.

"The first 3" keeps the slot numbers of the loaded timers, so the saved pending-alarm mask and a wakeup cookie stay valid for them. A bit or a cookie for a dropped slot has no effect: the mask is only read for existing slots, and the wakeup launch already checks the cookie against the slot count.

The format of a saved timer does not change, so `PERSIST_VERSION` stays the same.

*Alternative:* keep running countdowns first when timers must be dropped. Rejected: it moves slot numbers (the saved mask and the cookie become wrong) and costs code on the platform that has none to spare. See Risks.

### D6. Order of work, and the limit of the trim

Apply the trims in the D6 order of `list-alarm-takeover`: C and B (RAM with no link to alarms), then D. Measure after each one and record the numbers in `tasks.md`.

Then apply S (D8). If the release build does not reach 1600 bytes of heap with all four (the measurements used a simpler "Timer N" than D1), take the next steps in this order and measure again: 32-bit time math where a value cannot overflow; shorter strings. Stop and report before any step that touches alarm-delivery code.

### D7. Tests

- Unit tests (host build, not aplite): `timer_assign_name()` with `MNEMONIC_FEATURE` 0 is tested in a second test binary that is compiled with `-DPBL_PLATFORM_APLITE`: "Timer 1" for the first slot, the lowest free number after a delete, no duplicate after delete and create. The same binary tests `timer_persist_read()` with 5 saved slots: 3 are loaded, in order, and the keys of slots 3 and 4 are deleted.
- The existing unit tests do not change (they build as a non-aplite platform).
- Build check: the aplite release build links, and `strings` on its binary finds no `TEST_STATE`. The basalt binary still has it.
- Functional, aplite test build: the full suite, including `test_list_alarm_takeover.py` and its aplite-only test. Tests that expect a mnemonic name (`test_mnemonic_names.py`) skip on aplite. Tests that need more than 3 slots skip or adjust on aplite.
- Functional, basalt: the full suite again, to show that the other platforms did not change.
- Aplite sizes: `Total footprint in RAM` and `arm-none-eabi-size` for the release build and the test build, and the heap with a marked list row (the bell icon loaded). This closes tasks 3.3 and 3.4 of `list-alarm-takeover`.

### D8. No phone settings message code on aplite (`SETTINGS_SYNC_FEATURE`)

Add `SETTINGS_SYNC_FEATURE` to `src/settings.h`: 1 everywhere, 0 on aplite. With 0, `src/settings.c` leaves out `prv_inbox_received()`, the request and retry functions, the retry timer, and the four `app_message_*` calls in `settings_init()`. `settings_init()` still sets the defaults, loads saved settings if any exist, and saves them. The `settings_get_*()` functions do not change, so no caller changes.

This removes code that cannot work on aplite (see Context), and it is the trim that lifts the release heap above the floor. It also frees the heap that the failed `app_message_open()` call used for a moment at launch.

The saved settings blob stays: its code is small, and an aplite watch that somehow has saved settings keeps them.

The functional tests set a setting with `send_app_message_int()` only for the lap feature, which is not on aplite, so no aplite test depends on settings sync. Check this in the tasks.

*Alternatives:*
- Open the inbox with a small size on aplite so that sync works. Rejected for this change: the inbox must hold all the keys the phone sends, the size that fits is not known, and any inbox takes heap from an app that has none to spare. It can be a later change if aplite settings are wanted.
- Leave the code in. Rejected: 848 bytes for code that always fails, on the platform where the heap is below the safe floor.

## Risks / Trade-offs

- [An aplite user with 4 or 5 saved timers loses the last 1 or 2 at the update. A dropped running countdown does not ring.] → Only on the first launch after the update, and only for more than 3 timers on aplite. The 3 kept timers keep their alarms. The alternative (reset all, as today) loses more. See Open Questions.
- [The aplite test build may not run (heap about 784)] → D4 has two fallbacks and a stop rule.
- [The release heap is less than the sum of the measured savings (about 2190), because "Timer N" needs a unique-number search] → The requirement is 1600. The verify step measures it, and runs the release build on the emulator with a marked list row and checks for `App fault`.
- [A user expects the phone settings page to work on aplite] → It does not work today either. The docs say so after this change. A small-inbox sync can be a later change (D8).
- [No logs in the aplite release build makes a field problem on aplite harder to find] → A test build has them. `assert()` still logs.
- [A test build is shipped by mistake] → The build prints its kind. On every platform except aplite the two builds are the same binary.
- [Names on aplite are less easy to tell apart ("Timer 1", "Timer 2")] → Accepted. The time on the second line of each row tells them apart, and there are at most 3.
- [The other platforms change by accident] → The basalt suite runs again, and the basalt size is compared before and after.

## Migration Plan

No data migration step. Saved timers load as before; on aplite, more than 3 saved timers are cut to the first 3 (D5). Existing mnemonic names of saved timers on aplite stay as they are; only new timers get "Timer N".

Rollback: revert this change. Aplite then does not link again while `list-alarm-takeover` is applied.

## Open Questions

None.

Resolved (user, 2026-10-01):

- More than 3 saved timers on aplite: "keep the first 3" is accepted. See D5.
- The phone settings message code is left out of the aplite release build too. See D8.
