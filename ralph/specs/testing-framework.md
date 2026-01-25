# Specification: Testing Framework

## Overview
This specification outlines the setup of a unit testing framework for the pebble-timer-quick application. The goal is to enable automated testing of the C source code to ensure its correctness and to facilitate future development.

## Requirements

### 1. Testing Framework
- **Framework:** The project will use `cmocka`, a lightweight unit testing framework for C.
- **Test Location:** All test code will be located in a new `test` directory at the root of the project.
- **Build System:** The `wscript` build system will be modified to include a new `test` command (`pebble test`) that builds and runs the unit tests.
- **Emulator:** Unit tests will be run on the host machine. Integration tests, to be added later, will use the Pebble SDK's emulators (e.g., `diorite`, `basalt`).

### 2. Initial Test Suite
- A new test file, `test/test_timer.c`, will be created.
- This file will contain the initial set of unit tests for the timer logic found in `src/timer.c`.

## Testing Requirements

The initial test suite will include the following four tests for the `timer` module:

1.  **`test_timer_reset`**:
    - **Purpose:** Verify that `timer_reset()` correctly resets the timer's state.
    - **Steps:**
        1.  Initialize `timer_data` to a non-zero state.
        2.  Call `timer_reset()`.
        3.  Assert that `timer_get_length_ms()` returns 0.
        4.  Assert that `timer_data.can_vibrate` is `false`.

2.  **`test_timer_increment`**:
    - **Purpose:** Verify that `timer_increment()` correctly increases the timer's length.
    - **Steps:**
        1.  Call `timer_reset()`.
        2.  Call `timer_increment(5000)`.
        3.  Assert that `timer_get_length_ms()` returns `5000`.

3.  **`test_timer_pause`**:
    - **Purpose:** Verify that `timer_toggle_play_pause()` correctly pauses a running timer.
    - **Note:** `timer_reset()` sets `start_ms = epoch()`, which leaves the timer in a RUNNING state (since `timer_is_paused()` checks `start_ms <= 0`).
    - **Steps:**
        1.  Call `timer_reset()` - timer is now RUNNING.
        2.  Call `timer_increment(10000)`.
        3.  Simulate a delay of 2 seconds (timer is already running).
        4.  Call `timer_toggle_play_pause()` to PAUSE the timer.
        5.  Assert that `timer_get_value_ms()` is approximately `8000`.

4.  **`test_timer_start`**:
    - **Purpose:** Verify that the timer value decreases after starting.
    - **Note:** Since `timer_reset()` leaves timer RUNNING, no toggle is needed to start.
    - **Steps:**
        1. Call `timer_reset()` - timer starts RUNNING.
        2. Call `timer_increment(10000)`.
        3. Simulate a delay of 2 seconds (timer is already running).
        4. Assert that `timer_get_value_ms()` is less than `10000`.

## Dependencies
- `cmocka`: C unit testing framework.
- Pebble SDK: For emulator support in future integration tests.

## Progress
- 2026-01-24: Spec created.
- 2026-01-25: Created `test/test_timer.c` with initial tests.
- 2026-01-25: Created `test/pebble.h` and implemented mocks.
- 2026-01-25: Updated `wscript` to add `test` command and build logic.
- 2026-01-25: Verified compilation (skipped due to missing `cmocka` in environment).
- 2026-01-25: Fixed test implementations to correctly match timer.c behavior. All 4 tests now pass.
- 2026-01-25: Added `test/Makefile` to build and run tests without Pebble SDK.
- 2026-01-25: Spec COMPLETED. All tests passing.

## Notes
- The `epoch()` function is mocked using cmocka's `mock()` for deterministic tests.
- `cmocka` is required to run tests. A local copy is installed in `vendor/cmocka_install/`.
- **Important:** `timer_reset()` sets `start_ms = epoch()`, which leaves the timer in a RUNNING state (not paused). This is a key detail for understanding test flows.
- To run tests without Pebble SDK: `cd test && make test`
