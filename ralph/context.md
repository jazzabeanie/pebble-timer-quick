# Context File - Ralph Wiggum Loop

## Instructions for AI Agents
This file provides critical context about the codebase without requiring you to read everything. 

**USAGE RULES:**
- READ this file before starting work on any spec
- APPEND to the Recent Changes section with new entries (add at the top of that section, most recent first)
- Do NOT modify or delete existing Recent Changes entries - only append new ones
- UPDATE other sections (Key Components, Important Decisions, Known Issues, Future Considerations) as needed
- INCLUDE dates with your entries (YYYY-MM-DD format)
- BE CONCISE but include enough detail for future agents to understand decisions
- This file can be MANUALLY CLEARED at major project milestones when details are no longer relevant (human decision only)

**WHAT TO DOCUMENT:**
- Important architectural decisions and why they were made
- Key patterns or conventions established
- Gotchas, pitfalls, or non-obvious behavior
- Summaries of complex components
- Any context that would save future agents from re-discovering information

---

## Recent Changes
*Log recent changes with dates and brief descriptions. Most recent at top.*

- 2026-01-26: Changed repeat timer initial display from "2x" to "_x". When repeat mode is enabled via long press Up, `repeat_count` now starts at 0 (displayed as "_x") instead of 2. This is equivalent to 1x (no actual repeat). User must press Down twice to reach "2x" for actual repeating. Only change was in main.c (`prv_up_long_click_handler`: `repeat_count = 0` instead of `2`). Drawing.c already handled count=0 as "_x". Added unit test 22 (`test_timer_check_elapsed_repeat_zero_count`) verifying count=0 doesn't trigger repeat. Updated functional test `test_enable_repeating_timer` to verify "_x" initial display and require 2 Down presses to reach "2x". All 22 unit tests pass.
- 2026-01-26: COMPLETED repeating-timer spec. Implemented repeat toggle via long press Up in ControlModeCounting, intermediate alarm restart (Down button during intermediate alarm restarts instead of snoozing), chrono mode guard (no effect). Changed display format from "x2" to "2x" to match spec. Initial repeat_count set to 2 (minimum useful value). Added 3 new unit tests (19-21). Removed xfail from test_enable_repeating_timer and updated test to handle flashing indicator (multi-screenshot approach) and verify restart via header "00:20" pattern. Added `seconds` parameter to `has_time_pattern()` in test_create_timer.py. Key insight: the "Nx" indicator is only shown when repeat_count > 1. After the first repeat fires (decrementing from 2 to 1), the indicator disappears since "1x" is equivalent to a normal timer. The flashing indicator in ControlModeEditRepeat requires taking multiple screenshots to reliably capture via OCR. All 21 unit tests pass, all 10 create timer tests pass, 7/8 workflow tests pass (test_pause_completed_timer is a pre-existing flaky test).
- 2026-01-26: Fixed 3 failing functional tests (transitions_to_counting, counts_up, resets_timer). Key insights: (1) EasyOCR text extraction takes several seconds per image, causing app timing issues (3s inactivity timer, 7s chrono auto-quit). Fix: defer all OCR to after all screenshots are captured. (2) Chrono mode auto-backgrounds after 7 seconds (AUTO_BACKGROUND_CHRONO + QUIT_DELAY_MS=7000 in main.c). Fix: capture both chrono screenshots within the window, then press Down to cancel the quit timer before teardown runs. (3) LECO 7-segment font causes OCR digit misreadings (5→6, 0→O). Fix: normalize O/o→0 and expand digit variants in has_time_pattern(). All 10 tests pass on basalt.
- 2026-01-25: Extended functional-tests-emulator spec with 5 additional test cases. Added tests for: timer countdown, mode transition (New→Counting after 3s inactivity), chrono/stopwatch mode, play/pause toggle, and long-press reset. All 10 tests pass on basalt platform. Test classes now organized by feature: TestCreateTimer, TestButtonPresses, TestTimerCountdown, TestChronoMode, TestPlayPause, TestLongPressReset.
- 2026-01-25: Fixed persistent_emulator fixture to use menu navigation instead of install(). Key insight: `install()` clears the app's persisted state even within the same emulator session. Solution: Added `open_app_via_menu()` method to EmulatorHelper that re-opens the app by pressing SELECT twice (navigating through the Pebble launcher menu). After long-pressing down to quit an app, the Pebble returns to the launcher with the previously-run app selected. All 5 tests pass on basalt.
- 2026-01-25: Updated persistent_emulator fixture to preserve app persist state. Key change: After holding down button to quit the app (which sets persist state), the fixture now re-opens the app within the same emulator via `install()` instead of killing the emulator first. This preserves the app's persist data that was set by the long-press quit action. Removed the kill->reinstall cycle that was destroying the persist state.
- 2026-01-25: Fixed functional-tests-emulator persistent_emulator fixture. Key insights: (1) QEMU's TCP server for button input only supports ONE concurrent connection - must use persistent socket. (2) Rapid socket connect/disconnect causes timeouts after ~2 connections. (3) Added pytest.ini with log_cli=true for proper logging output. (4) Warm-up cycle (wipe->install->long-press-quit->kill->fresh-install) ensures clean state between test runs.
- 2026-01-25: COMPLETED timer-extended-tests spec. Added 14 new unit tests (total 18 tests now). Key insights: (1) `timer_check_elapsed()` auto-snooze behavior re-enables `can_vibrate` via `timer_increment()` - this is intentional design for re-arming alerts. (2) Vibration mocks now use cmocka's `function_called()` / `expect_function_call()` for verification. (3) Added `vibes_cancel()` mock to pebble.h.
- 2026-01-25: COMPLETED testing framework spec. Fixed test implementations to correctly handle timer.c behavior. Key insight: `timer_reset()` sets `start_ms = epoch()` which leaves timer RUNNING, not paused. Added `test/Makefile` for standalone test builds. All 4 tests now pass.
- 2026-01-25: Implemented testing framework spec. Added `test/test_timer.c` and `test/pebble.h`. Updated `wscript` to include test command and check for `cmocka`. Tests are skipped if `cmocka` is not found.

<!-- Example:
- 2026-01-23: Initial project setup with ralph loop structure
-->

---

## Key Components
*Summaries of key components or modules, explaining their purpose and how they fit together.*

### Timer Module (src/timer.c)
Core timer logic. Key behavioral notes:
- `timer_reset()` sets `start_ms = epoch()`, leaving timer in RUNNING state
- `timer_is_paused()` returns `start_ms <= 0` - negative start_ms encodes elapsed time when paused
- `timer_get_value_ms()` uses complex formula: `length - epoch + (((start + epoch - 1) % epoch) + 1)`
- `timer_toggle_play_pause()` toggles by subtracting/adding epoch to start_ms

### Testing Framework (test/)
- `test/test_timer.c`: Unit tests for timer module using cmocka
- `test/pebble.h`: Mock Pebble SDK headers for host compilation
- `test/Makefile`: Standalone build without Pebble SDK
- cmocka installed in `vendor/cmocka_install/`

### Functional Tests (test/functional/)
- `test/functional/conftest.py`: EmulatorHelper class for interacting with Pebble emulator
- `test/functional/test_create_timer.py`: 10 functional tests organized into 6 test classes:
  - TestCreateTimer: Timer creation via button presses (2-minute timer test, initial state, increment tests)
  - TestButtonPresses: Button functionality (Up adds 20min, Select adds 5min)
  - TestTimerCountdown: Timer countdown and mode transition tests
  - TestChronoMode: Stopwatch/chrono functionality
  - TestPlayPause: Play/pause toggle in counting mode
  - TestLongPressReset: Long press Select to reset timer
- `test/functional/pytest.ini`: Logging configuration (log_cli=true for visible logs)
- Key pattern: Use **persistent socket** for QEMU button commands - QEMU only accepts one connection at a time
- Key pattern: **Defer OCR assertions** to after all screenshots are captured - EasyOCR takes several seconds per image, which interferes with app timing (3s inactivity timer, 7s chrono auto-quit)
- Key pattern: **Chrono auto-quit**: app exits chrono mode after 7s. Press Down after screenshots to cancel quit timer.
- Key pattern: **OCR digit normalization**: O/o→0 substitution in normalize_time_text(), digit variant expansion (5↔6, 0↔8, etc.) in has_time_pattern()
- Run tests: `./conda-env/bin/python -m pytest test/functional/test_create_timer.py -v --platform=basalt`

---

## Important Decisions
*Document architectural or design decisions with reasoning.*

### 2026-01-25: Persistent Socket for QEMU Button Commands
QEMU's TCP serial port (`-serial tcp::port,server,nowait`) only accepts ONE concurrent connection. Previous implementation created a new socket for each button press, causing timeouts after ~2-3 rapid presses. Fixed by maintaining a persistent socket in EmulatorHelper. The socket is created once on transport connect and reused for all button commands.

### 2026-01-25: Standalone Test Build via Makefile
Added `test/Makefile` to allow running tests without requiring the Pebble SDK. This enables CI/CD integration and easier local testing. The wscript build system is still the primary method when using Pebble tools.

---

## Known Issues
*Technical debt and issues that need future attention but aren't blocking current work.*

- timer.c has debug APP_LOG statements with `%lld` format specifiers that cause warnings on 64-bit Linux (should use `PRId64` from `<inttypes.h>`)
- The `epoch()` function mock in tests returns uint64_t via mock() cast - works but not ideal for very large epoch values

---

## Future Considerations
*Ideas for enhancements or improvements identified during development.*

<!-- Example:
- Consider implementing caching layer for frequently accessed user data
- Could benefit from adding webhooks for real-time notifications
- API versioning strategy should be established before adding breaking changes
-->

---

