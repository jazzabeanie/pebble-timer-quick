# Specification: Stopwatch Subtraction Fix

## Overview
This specification defines the fix for a bug where subtracting time from a stopwatch (chrono) timer results in an invalid state instead of converting it into a countdown timer. 

## Problem Description
When the timer is in chrono mode (counting up from 0:00), it has `length_ms = 0` and `start_ms <= epoch()`. 
If a user subtracts time (e.g., 1 minute) from the chrono timer, `timer_increment_chrono(-60000)` is called, which sets `start_ms = start_ms + 60000`. 
If this new `start_ms` is in the future (`start_ms > epoch()`), the current logic in `timer_is_chrono()` and `timer_get_value_ms()` fails because it uses a modulo operation `% epoch()` that does not account for future start times. This results in the timer displaying a massive value (near the epoch itself) instead of a 1-minute countdown.

## Requirements

### 1. Test-Driven Development
A new unit test must be added to `test/test_timer.c` to reproduce the bug before implementing the fix.

### 2. Robust Time Calculations
The logic in `src/timer.c` must be updated to correctly handle:
-   **Running Timers**: `start_ms > 0`
-   **Paused Timers**: `start_ms <= 0` (where `start_ms` is the negative of the elapsed time at the moment of pause)
-   **Future Start Times**: `start_ms > epoch()` (representing a countdown timer that hasn't started yet or has been adjusted into the future)

### 3. API Contract Changes
No changes to the public API in `timer.h` are required. The internal implementation of the following functions will be updated:
-   `timer_get_value_ms()`
-   `timer_is_chrono()`

## Implementation Plan

### Step 1: Reproduction Test
Add `test_timer_chrono_subtraction_to_countdown` to `test/test_timer.c`:
1.  Mock `epoch()` to return `100000`.
2.  Set `timer_data.length_ms = 0`.
3.  Set `timer_data.start_ms = 95000` (5 seconds elapsed, showing 0:05 chrono).
4.  Call `timer_increment_chrono(-60000)` (subtract 1 minute).
5.  Assert `timer_data.start_ms == 155000` (60 seconds in the future).
6.  Assert `timer_is_chrono()` returns `false` (it's now a countdown).
7.  Assert `timer_get_value_ms()` returns `55000` (0:55 remaining).

### Step 2: Refactor Logic
Update `src/timer.c` with simplified logic:
-   Calculate `elapsed` time first:
    ```c
    int64_t elapsed = (timer_data.start_ms > 0) ? (epoch() - timer_data.start_ms) : (-timer_data.start_ms);
    ```
-   Calculate `raw_value = timer_data.length_ms - elapsed`.
-   `timer_is_chrono()` returns `raw_value <= 0`.
-   `timer_get_value_ms()` returns `raw_value` (if `raw_value >= 0`) or `-raw_value` (if `raw_value < 0`).

### Step 3: Update Existing Tests
Existing tests in `test/test_timer.c` that rely on the old modulo math may need to be updated to match the new, simpler (and more correct) behavior.

## Dependencies
- `testing-framework.md` (spec #1)
- `timer-extended-tests.md` (spec #2)

## Progress
- **Status**: Not Started
- **Tests**: NA
