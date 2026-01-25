# Specification: Extended Timer Tests

## Overview
This specification defines additional unit tests for `src/timer.c` to improve test coverage. These tests complement the existing 4 tests in `test/test_timer.c` by covering the remaining timer API functions (excluding persistence).

## Requirements

### 1. Testing Framework
- **Framework:** Tests will use the existing `cmocka` setup in `test/test_timer.c`.
- **Mocking:** Continue using the existing `epoch()` mock for deterministic time control.
- **Additional Mocks:** Add mocks for `vibes_enqueue_custom_pattern()`, `vibes_long_pulse()`, and `vibes_cancel()` to test vibration logic.

### 2. New Test Cases
The following tests will be added to `test/test_timer.c`.

## Testing Requirements

### 1. `test_timer_get_time_parts`
- **Purpose:** Verify that `timer_get_time_parts()` correctly converts milliseconds to hours, minutes, and seconds.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(3661000)` (1 hour, 1 minute, 1 second).
    3. Call `timer_get_time_parts(&hr, &min, &sec)`.
    4. Assert `hr == 1`, `min == 1`, `sec == 1`.

### 2. `test_timer_is_chrono_false`
- **Purpose:** Verify that `timer_is_chrono()` returns false when timer has positive remaining time.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(60000)` (1 minute).
    3. Assert `timer_is_chrono()` returns `false`.

### 3. `test_timer_is_chrono_true`
- **Purpose:** Verify that `timer_is_chrono()` returns true when timer has elapsed past zero.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(5000)` (5 seconds).
    3. Simulate delay of 10 seconds (timer runs past zero).
    4. Assert `timer_is_chrono()` returns `true`.

### 4. `test_timer_is_vibrating`
- **Purpose:** Verify that `timer_is_vibrating()` returns true only when all conditions are met: chrono mode, running, and can_vibrate is true.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(5000)`.
    3. Simulate delay of 10 seconds (enter chrono mode).
    4. Set `timer_data.can_vibrate = true`.
    5. Assert `timer_is_vibrating()` returns `true`.
    6. Call `timer_toggle_play_pause()` to pause.
    7. Assert `timer_is_vibrating()` returns `false` (paused).

### 5. `test_timer_increment_chrono`
- **Purpose:** Verify that `timer_increment_chrono()` adjusts the stopwatch by modifying start_ms.
- **Steps:**
    1. Call `timer_reset()` (timer starts running).
    2. Record initial `timer_data.start_ms`.
    3. Call `timer_increment_chrono(5000)`.
    4. Assert `timer_data.start_ms` decreased by 5000.

### 6. `test_timer_rewind`
- **Purpose:** Verify that `timer_rewind()` pauses the timer and resets start_ms to 0.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(60000)`.
    3. Simulate delay of 5 seconds.
    4. Call `timer_rewind()`.
    5. Assert `timer_data.start_ms == 0` (paused).
    6. Assert `timer_data.can_vibrate == true` (since length > 0).

### 7. `test_timer_restart_countdown`
- **Purpose:** Verify that `timer_restart()` restores a countdown timer to its base length.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(60000)` (1 minute).
    3. Set `timer_data.base_length_ms = 60000`.
    4. Simulate delay of 30 seconds.
    5. Call `timer_restart()`.
    6. Assert `timer_data.length_ms == 60000` (restored to base).
    7. Assert timer is running (start_ms > 0).

### 8. `test_timer_restart_chrono`
- **Purpose:** Verify that `timer_restart()` resets a chrono timer to 0.
- **Steps:**
    1. Call `timer_reset()`.
    2. Set `timer_data.base_length_ms = 0` (chrono mode).
    3. Simulate delay of 10 seconds (chrono running).
    4. Call `timer_restart()`.
    5. Assert `timer_data.length_ms == 0`.

### 9. `test_timer_check_elapsed_vibrates`
- **Purpose:** Verify that `timer_check_elapsed()` triggers vibration when timer is in chrono mode, running, can_vibrate is true, and value is under 30 seconds.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(5000)`.
    3. Simulate delay of 7 seconds (value ~2 seconds into chrono).
    4. Set `timer_data.can_vibrate = true`.
    5. Call `timer_check_elapsed()`.
    6. Assert `vibes_enqueue_custom_pattern()` was called.

### 10. `test_timer_check_elapsed_auto_snooze`
- **Purpose:** Verify that `timer_check_elapsed()` disables vibration and increments auto_snooze_count after 30 seconds.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(5000)`.
    3. Simulate delay of 40 seconds (value > VIBRATION_LENGTH_MS of 30s).
    4. Set `timer_data.can_vibrate = true`.
    5. Set `timer_data.auto_snooze_count = 0`.
    6. Call `timer_check_elapsed()`.
    7. Assert `timer_data.can_vibrate == false`.
    8. Assert `timer_data.auto_snooze_count == 1`.

### 11. `test_timer_check_elapsed_repeat`
- **Purpose:** Verify that `timer_check_elapsed()` handles repeating timers correctly.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(5000)`.
    3. Set `timer_data.base_length_ms = 5000`.
    4. Set `timer_data.is_repeating = true`.
    5. Set `timer_data.repeat_count = 3`.
    6. Simulate delay of 7 seconds (enter chrono).
    7. Set `timer_data.can_vibrate = true`.
    8. Call `timer_check_elapsed()`.
    9. Assert `timer_data.repeat_count == 2` (decremented).
    10. Assert `vibes_long_pulse()` was called.

### 12. `test_timer_sub_minute_valid`
- **Purpose:** Verify that timers with values between 1-59 seconds work correctly.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(30000)` (30 seconds).
    3. Assert `timer_get_length_ms() == 30000`.
    4. Assert `timer_get_value_ms()` is approximately 30000.

### 13. `test_timer_sub_second_resets`
- **Purpose:** Verify that timers with values less than 1 second auto-reset.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(500)` (500ms).
    3. Assert `timer_get_length_ms() == 0` (auto-reset triggered).

### 14. `test_timer_crosses_sub_second_resets`
- **Purpose:** Verify that a running timer auto-resets when it crosses below 1 second.
- **Steps:**
    1. Call `timer_reset()`.
    2. Call `timer_increment(2000)` (2 seconds).
    3. Simulate delay of 1.5 seconds (value now ~500ms).
    4. Call `timer_increment(0)` to trigger the check.
    5. Assert `timer_get_length_ms() == 0` (auto-reset triggered).

## Dependencies
- `cmocka`: C unit testing framework (existing).
- Mocks for `vibes_enqueue_custom_pattern()`, `vibes_long_pulse()`, `vibes_cancel()`.

## Progress
- 2026-01-25: Spec created.

## Notes
- The `VIBRATION_LENGTH_MS` constant is 30000ms (30 seconds).
- The `SNOOZE_INCREMENT_MS` constant is defined in `utility.h`.
- Tests 9-11 require mocking the vibration functions to verify they are called.
- The existing `epoch()` mock should be extended to support setting arbitrary return values for simulating time passage.
