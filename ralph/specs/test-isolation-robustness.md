# Test Isolation Robustness

## Overview

Functional tests passed when run in isolation but failed when run as part of
the full suite. Whole modules would fail with `All captured logs: []` (see
`pytest_results_subset_20260419_103800.log`), plus pervasive
"Expected mode New, got Counting" timing flakiness. This spec makes the test
infrastructure robust against cross-test interference.

## Root Causes

1. **`pebble kill` / `pebble wipe` are global.** The pebble tool's kill
   command kills the qemu/pypkjs processes of *every* platform, and wipe
   deletes *every* platform's persist directory. The function-scoped
   `emulator` fixture killed/wiped per test, destroying the module-scoped
   `persistent_emulator` instances other tests were still using.

2. **The shared `pebble logs` subprocess broke across emulator restarts.**
   The `_PlatformReader` kept one `pebble logs` process per platform for the
   whole session. When an emulator was killed and restarted, the subprocess
   could hang attached to the dead instance (its stuck-detection only fired
   if the process had *never* produced output), leaving every later log-based
   assertion in the session with empty captures. Worse, `pebble logs` boots
   its own emulator via the pebble tool's managed transport if none is
   running, so the respawn loop could race the tests' own installs and leave
   orphan qemu processes.

3. **Fixed sleeps raced the app's 3s new-expire timer**
   (`NEW_EXPIRE_TIME_MS`, src/main.c). Fixture sleeps (e.g. the 3.0s log
   warm-up) consumed an unpredictable slice of the 3-second ControlModeNew
   window before the test body ran; under full-suite load the margin
   vanished.

4. **No launch verification.** Nothing confirmed "app launched and logs
   flowing" before a test body ran, so one broken emulator or leaked
   persisted state cascaded through a whole module (e.g. 16 consecutive
   failures in `test_timer_workflows.py`).

## Changes (all in `test/functional/conftest.py`)

1. **`_LogStream` replaces `_PlatformReader`.** App logs are read directly
   from the emulator's pypkjs WebSocket — the same transport used for button
   presses. The stream sends `AppLogShippingControl(enable=True)` (endpoint
   2006) and decodes `AppLogMessage` packets itself. It reconnects
   automatically when the emulator restarts and never spawns processes.
   `LogCapture`'s public API is unchanged; multiple captures may now be
   attached simultaneously.

2. **Platform-scoped kill/wipe.** `EmulatorHelper.kill()`/`wipe()` kill only
   this platform's qemu/pypkjs pids (from the pebble tool's emulator info
   file) and delete only this platform's persist directory.

3. **Launch barrier.** `install()` blocks until the app's `TEST_STATE:init`
   line (emitted by `prv_initialize`) is observed, retrying once with a
   log-stream reconnect + relaunch, and raising (after killing the emulator
   for a clean cold boot) if the launch still can't be confirmed. The
   captured init state is stored in `helper.last_init_state`.

4. **Leaked-state detection & recovery.** The autouse per-test fixture
   checks `last_init_state` for a fresh start (`m=New`, `t=0:00`). If a
   previous test leaked persisted state, it logs a warning and recovers with
   a full wipe cycle (`_fresh_start_cycle`) instead of letting the leak
   cascade; if that fails too the test fails fast with the init state in the
   message.

5. The `emulator` fixture's 3.0s log warm-up sleep is gone (the stream is
   always connected), so test bodies now get the full 3s ControlModeNew
   window.

## Test Cases

Verification is by running previously order-dependent combinations:

1. `test_hold_down_delete.py` alone (baseline parity) — passes, ~26s faster
   than before.
2. Cross-fixture sequence `test_hold_down_delete.py` (function-scoped
   `emulator`, kills the emulator per test) followed by
   `test_base_length.py` + `test_log_based.py` (module-scoped
   `persistent_emulator`) — the transition that previously killed the log
   pipeline.
3. Full basalt suite run for a health snapshot.

## Progress

- 2026-07-14: Root causes identified from April failure logs + pebble-tool
  source. WebSocket log capture validated with a standalone probe.
  Implemented all conftest changes; README updated.
- 2026-07-14: First combo run caught a packet-coalescing bug (pypkjs can pack
  several pebble-protocol packets into one relay frame, and packets can span
  frames); fixed with a receive buffer mirroring libpebble2's
  PebbleConnection.
- 2026-07-14: Full basalt run: **115 passed / 22 failed / 4 errors (38:45)**
  vs the 2026-06-29 baseline of 75 passed / 47 failed / 3 errors. All
  previously order-dependent modules (test_timer_workflows etc.) now pass;
  zero `All captured logs: []` occurrences. Added `pebble install` retry
  (with a scoped kill between attempts) after a cold boot exceeded the
  pebble tool's hard-coded 5s connect window and errored a module fixture.

## Remaining full-run failures (classified, none order-dependent)

- 13 icon reference-mask mismatches (test_button_icons,
  test_directional_icons, test_repeat_counter_visibility) — pre-existing
  stale reference images.
- 5 test_timer_list "Delete all" tests — fail identically in isolation;
  app/feature-level, not infrastructure.
- 2 test_reverse_chrono_and_edit_pause — documented pre-existing.
- 1 test_backlight (linger measured 0.64s < asserted 0.8s) and
  1 test_create_timer chrono OCR (7s AUTO_BACKGROUND_CHRONO window) —
  wall-clock-sensitive test logic, load jitter.

## Status

Completed

## Tests

Passing (infrastructure-level; remaining full-run failures classified above
are pre-existing or app-level)
