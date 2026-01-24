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
    - **Steps:**
        1.  Call `timer_reset()`.
        2.  Call `timer_increment(10000)`.
        3.  Call `timer_toggle_play_pause()` to start the timer.
        4.  Simulate a delay of 2 seconds.
        5.  Call `timer_toggle_play_pause()` to pause the timer.
        6.  Assert that `timer_get_value_ms()` is approximately `8000`.

4.  **`test_timer_start`**:
    - **Purpose:** Verify that the timer value decreases after starting.
    - **Steps:**
        1. Call `timer_reset()`.
        2. Call `timer_increment(10000)`.
        3. Call `timer_toggle_play_pause()` to start the timer.
        4. Simulate a delay of 2 seconds.
        5. Assert that `timer_get_value_ms()` is less than `10000`.

## Dependencies
- `cmocka`: C unit testing framework.
- Pebble SDK: For emulator support in future integration tests.

## Progress
- 2026-01-24: Spec created.

## Notes
- The `epoch()` function will need to be mocked for the tests to be deterministic.
