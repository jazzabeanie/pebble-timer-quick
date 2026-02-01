#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>

#include "pebble.h"
#include "utility.h"
#include "timer.h"

// Mock epoch function
uint64_t epoch(void) {
    return (uint64_t)mock();
}

// Mock persistence functions (stubs)
status_t persist_write_int(const uint32_t key, const int32_t value) {
    return 0;
}

int persist_write_data(const uint32_t key, const void *data, const size_t size) {
    return (int)size;
}

bool persist_exists(const uint32_t key) {
    return false;
}

status_t persist_delete(const uint32_t key) {
    return 0;
}

int persist_read_data(const uint32_t key, void *buffer, const size_t buffer_size) {
    return 0;
}

// Mock vibration functions (verifiable)
void vibes_long_pulse(void) {
    function_called();
}

void vibes_enqueue_custom_pattern(VibePattern pattern) {
    function_called();
}

void vibes_cancel(void) {
    function_called();
}

// Helper to reset timer state before each test
static int setup(void **state) {
    // Manually zero out timer_data for a clean slate
    memset(&timer_data, 0, sizeof(Timer));
    return 0;
}

static int teardown(void **state) {
    return 0;
}

// 1. test_timer_reset
// Purpose: Verify that timer_reset() correctly resets the timer's state.
static void test_timer_reset(void **state) {
    // Initialize timer_data to non-zero
    timer_data.length_ms = 1000;
    timer_data.can_vibrate = true;

    // timer_reset() calls epoch() once
    will_return(epoch, 10000);

    timer_reset();

    assert_int_equal(timer_get_length_ms(), 0);
    assert_false(timer_data.can_vibrate);
}

// 2. test_timer_increment
// Purpose: Verify that timer_increment() correctly increases the timer's length.
static void test_timer_increment(void **state) {
    // Setup: timer starts at 0, paused (start_ms = 0)
    timer_data.start_ms = 0;
    timer_data.length_ms = 0;

    // timer_increment calls timer_get_value_ms which calls epoch() 0 times when paused
    // When paused (start_ms <= 0), timer_get_value_ms returns length_ms - (-start_ms) = length_ms
    // No epoch() calls needed for paused state
    timer_increment(5000);

    assert_int_equal(timer_get_length_ms(), 5000);
}

// 3. test_timer_pause
// Purpose: Verify that timer_toggle_play_pause() correctly pauses a running timer.
// Note: timer_reset() leaves the timer in a RUNNING state (start_ms = epoch()).
// So: Reset -> Increment -> (already running) -> Delay -> Toggle(Pause) -> Check
static void test_timer_pause(void **state) {
    // Step 1: Call timer_reset()
    // This sets start_ms = epoch(), length_ms = 0, and leaves timer RUNNING
    will_return(epoch, 10000);
    timer_reset();
    // State: start_ms=10000, length_ms=0, RUNNING

    // Step 2: Call timer_increment(10000)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(10000);
    // State: start_ms=10000, length_ms=10000, RUNNING

    // Timer is already running. Let it run for 2 seconds.
    // Simulate time passing to T=12000

    // Step 3: Call timer_toggle_play_pause() to PAUSE the timer
    // Since start_ms > 0 (running), toggle will subtract epoch (pause it)
    // start_ms = 10000 - 12000 = -2000 (negative means paused with 2s elapsed)
    will_return(epoch, 12000);
    timer_toggle_play_pause();
    // State: start_ms=-2000 (paused), length_ms=10000

    // Step 4: Check timer value
    // When paused (start_ms <= 0), no epoch() call needed
    // elapsed = -start_ms = 2000
    // value = length_ms - elapsed = 10000 - 2000 = 8000
    int64_t value = timer_get_value_ms();

    // Assert value is approximately 8000 (10000 - 2000)
    assert_true(value >= 7500 && value <= 8500);
}

// 4. test_timer_start
// Purpose: Verify that the timer value decreases after starting.
// Note: timer_reset() leaves timer RUNNING, so we don't need to call toggle to start.
static void test_timer_start(void **state) {
    // Step 1: Call timer_reset()
    will_return(epoch, 10000);
    timer_reset();
    // State: start_ms=10000, length_ms=0, RUNNING

    // Step 2: Call timer_increment(10000)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(10000);
    // State: start_ms=10000, length_ms=10000, RUNNING

    // Step 3: Simulate delay 2s by advancing epoch to 12000
    // The timer is already running from reset

    // Step 4: Check timer value
    // When running (start_ms > 0), epoch() is called once
    // elapsed = epoch() - start_ms = 12000 - 10000 = 2000
    // value = length_ms - elapsed = 10000 - 2000 = 8000
    will_return(epoch, 12000);
    int64_t value = timer_get_value_ms();

    // Assert value has decreased from 10000
    assert_true(value < 10000);
}

// 5. test_timer_get_time_parts
// Purpose: Verify that timer_get_time_parts() correctly converts milliseconds to hours, minutes, seconds.
static void test_timer_get_time_parts(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 1 hour, 1 minute, 1 second = 3661000 ms
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(3661000);

    // timer_get_time_parts calls timer_get_value_ms which calls epoch() 1 time
    // Since timer is running with start_ms=10000, epoch=10000:
    // elapsed = epoch() - start_ms = 10000 - 10000 = 0
    // value = length_ms - elapsed = 3661000 - 0 = 3661000
    will_return(epoch, 10000);

    uint16_t hr, min, sec;
    timer_get_time_parts(&hr, &min, &sec);

    assert_int_equal(hr, 1);
    assert_int_equal(min, 1);
    assert_int_equal(sec, 1);
}

// 6. test_timer_is_chrono_false
// Purpose: Verify that timer_is_chrono() returns false when timer has positive remaining time.
static void test_timer_is_chrono_false(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 60000 ms (1 minute)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(60000);

    // timer_is_chrono calls epoch() 1 time for running timer
    // elapsed = epoch() - start_ms = 10000 - 10000 = 0
    // raw_value = length_ms - elapsed = 60000 - 0 = 60000 > 0, so not chrono
    will_return(epoch, 10000);

    assert_false(timer_is_chrono());
}

// 7. test_timer_is_chrono_true
// Purpose: Verify that timer_is_chrono() returns true when timer has elapsed past zero.
static void test_timer_is_chrono_true(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();
    // State: start_ms=10000, length_ms=0, RUNNING

    // Increment to 5000 ms (5 seconds)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(5000);
    // State: start_ms=10000, length_ms=5000, RUNNING

    // Simulate delay of 10 seconds (timer runs past zero)
    // At T=20000, timer has been running for 10s but only had 5s
    // timer_is_chrono calls epoch() 1 time
    // elapsed = epoch() - start_ms = 20000 - 10000 = 10000
    // raw_value = length_ms - elapsed = 5000 - 10000 = -5000 <= 0, so IS chrono
    will_return(epoch, 20000);

    assert_true(timer_is_chrono());
}

// 8. test_timer_is_vibrating
// Purpose: Verify that timer_is_vibrating() returns true only when all conditions are met.
static void test_timer_is_vibrating(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(5000);

    // Simulate delay of 10 seconds (enter chrono mode)
    // Set can_vibrate = true
    timer_data.can_vibrate = true;

    // timer_is_vibrating calls timer_is_chrono (1 epoch call) and timer_is_paused (0 calls)
    // timer_is_chrono: elapsed = 20000 - 10000 = 10000, raw = 5000 - 10000 = -5000 <= 0
    will_return(epoch, 20000);

    assert_true(timer_is_vibrating());

    // Now pause the timer
    // timer_toggle_play_pause: start_ms = 10000 - 20000 = -10000 (paused)
    will_return(epoch, 20000);
    timer_toggle_play_pause();

    // timer_is_vibrating should return false (paused)
    // timer_is_chrono is called for paused timer: no epoch() call needed
    // elapsed = -(-10000) = 10000, raw = 5000 - 10000 = -5000 <= 0, so chrono=true
    // But timer_is_paused returns true first (short-circuit), so timer_is_vibrating returns false

    assert_false(timer_is_vibrating());
}

// 9. test_timer_increment_chrono
// Purpose: Verify that timer_increment_chrono() adjusts the stopwatch by modifying start_ms.
static void test_timer_increment_chrono(void **state) {
    // Setup: reset timer at T=10000 (timer starts running)
    will_return(epoch, 10000);
    timer_reset();
    // State: start_ms=10000

    // Record initial start_ms
    int64_t initial_start_ms = timer_data.start_ms;
    assert_int_equal(initial_start_ms, 10000);

    // Call timer_increment_chrono(5000)
    // This should decrease start_ms by 5000
    timer_increment_chrono(5000);

    assert_int_equal(timer_data.start_ms, initial_start_ms - 5000);
    assert_int_equal(timer_data.start_ms, 5000);
}

// 10. test_timer_rewind
// Purpose: Verify that timer_rewind() pauses the timer and resets start_ms to 0.
static void test_timer_rewind(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 60000 ms (1 minute)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(60000);
    // State: start_ms=10000, length_ms=60000, can_vibrate=true

    // Simulate delay of 5 seconds (time at T=15000)
    // But rewind doesn't need epoch calls

    // Call timer_rewind()
    timer_rewind();

    // Assert start_ms == 0 (paused)
    assert_int_equal(timer_data.start_ms, 0);
    // Assert can_vibrate == true (since length > 0)
    assert_true(timer_data.can_vibrate);
}

// 11. test_timer_restart_countdown
// Purpose: Verify that timer_restart() restores a countdown timer to its base length.
static void test_timer_restart_countdown(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 60000 ms (1 minute)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(60000);

    // Set base_length_ms = 60000
    timer_data.base_length_ms = 60000;

    // Simulate delay of 30 seconds (T=40000)
    // Timer is running, so let's just verify restart behavior

    // Call timer_restart()
    // timer_restart calls timer_is_paused (no epoch) and epoch() once if not paused
    will_return(epoch, 40000);
    timer_restart();

    // Assert length_ms == 60000 (restored to base)
    assert_int_equal(timer_data.length_ms, 60000);
    // Assert timer is running (start_ms > 0)
    assert_true(timer_data.start_ms > 0);
    assert_int_equal(timer_data.start_ms, 40000);
}

// 12. test_timer_restart_chrono
// Purpose: Verify that timer_restart() resets a chrono timer to 0.
static void test_timer_restart_chrono(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Set base_length_ms = 0 (chrono mode)
    timer_data.base_length_ms = 0;

    // Simulate delay of 10 seconds (chrono running)
    // Timer is running from reset

    // Call timer_restart()
    // timer_restart calls timer_is_paused then epoch()
    will_return(epoch, 20000);
    timer_restart();

    // Assert length_ms == 0
    assert_int_equal(timer_data.length_ms, 0);
}

// 13. test_timer_check_elapsed_vibrates
// Purpose: Verify that timer_check_elapsed() triggers vibration when conditions are met.
static void test_timer_check_elapsed_vibrates(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(5000);

    // Simulate delay of 7 seconds (value ~2 seconds into chrono)
    // Set can_vibrate = true
    timer_data.can_vibrate = true;

    // timer_check_elapsed calls:
    // 1. timer_is_chrono (1 epoch call)
    // 2. timer_is_paused (0 epoch calls)
    // 3. If chrono && running && can_vibrate, check repeat and value
    // 4. timer_get_value_ms (1 epoch call)
    // At T=17000: elapsed = 17000 - 10000 = 7000, value = |5000 - 7000| = 2000 ms (under 30s)
    will_return(epoch, 17000);
    will_return(epoch, 17000);

    // Expect vibes_enqueue_custom_pattern to be called
    expect_function_call(vibes_enqueue_custom_pattern);

    timer_check_elapsed();
}

// 14. test_timer_check_elapsed_auto_snooze
// Purpose: Verify that timer_check_elapsed() increments auto_snooze_count after 30 seconds.
// Note: can_vibrate is set to false, but then timer_increment re-enables it because length > 0.
// This is the actual behavior of the code - the snooze adds time and re-arms vibration.
static void test_timer_check_elapsed_auto_snooze(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(5000);

    // Simulate delay of 40 seconds (value > VIBRATION_LENGTH_MS of 30s)
    // At T=50000: elapsed = 50000 - 10000 = 40000, chrono value = |5000 - 40000| = 35000 ms
    timer_data.can_vibrate = true;
    timer_data.auto_snooze_count = 0;

    // timer_check_elapsed calls:
    // 1. timer_is_chrono (1 epoch call)
    // 2. timer_is_paused (0 calls)
    // 3. timer_get_value_ms (1 epoch call) -> returns > 30000
    // Then it sets can_vibrate = false and increments auto_snooze_count
    // timer_increment calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 50000);
    will_return(epoch, 50000);
    // timer_increment for snooze
    will_return(epoch, 50000);

    timer_check_elapsed();

    // Assert auto_snooze_count == 1 (incremented)
    assert_int_equal(timer_data.auto_snooze_count, 1);
    // Note: can_vibrate is true after timer_increment re-enables it (length > 0)
    // This is by design - the snooze adds time and re-arms the timer
    assert_true(timer_data.can_vibrate);
}

// 15. test_timer_check_elapsed_repeat
// Purpose: Verify that timer_check_elapsed() handles repeating timers correctly.
static void test_timer_check_elapsed_repeat(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(5000);

    // Set up repeating timer
    timer_data.base_length_ms = 5000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 3;
    timer_data.can_vibrate = true;

    // Simulate delay of 7 seconds (enter chrono)
    // timer_check_elapsed calls:
    // 1. timer_is_chrono (1 epoch call)
    // 2. timer_is_paused (0 calls)
    // 3. checks repeat and decrements count
    // 4. calls timer_increment which calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 17000);
    // timer_increment inside check_elapsed
    will_return(epoch, 17000);

    // Expect vibes_long_pulse to be called (for repeat)
    expect_function_call(vibes_long_pulse);

    timer_check_elapsed();

    // Assert repeat_count == 2 (decremented)
    assert_int_equal(timer_data.repeat_count, 2);
}

// 16. test_timer_sub_minute_valid
// Purpose: Verify that timers with values between 1-59 seconds work correctly.
static void test_timer_sub_minute_valid(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 30000 ms (30 seconds)
    // timer_increment calls timer_get_value_ms which calls epoch() 1 time for running timer
    will_return(epoch, 10000);
    timer_increment(30000);

    // Assert length == 30000
    assert_int_equal(timer_get_length_ms(), 30000);

    // Assert value is approximately 30000
    // timer_get_value_ms at same epoch returns 30000 (1 epoch call)
    will_return(epoch, 10000);
    int64_t value = timer_get_value_ms();
    assert_true(value >= 29000 && value <= 31000);
}

// 17. test_timer_sub_second_resets
// Purpose: Verify that timers with values less than 1 second auto-reset.
static void test_timer_sub_second_resets(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 500 ms
    // timer_increment calls timer_get_value_ms (1 epoch call)
    // After incrementing, value is 500ms which is < 1000, so timer_reset is called
    // timer_reset calls epoch once
    will_return(epoch, 10000);
    will_return(epoch, 10000);
    timer_increment(500);

    // Assert length == 0 (auto-reset triggered)
    assert_int_equal(timer_get_length_ms(), 0);
}

// 18. test_timer_crosses_sub_second_resets
// Purpose: Verify that a running timer auto-resets when it crosses below 1 second.
static void test_timer_crosses_sub_second_resets(void **state) {
    // Setup: reset timer
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 2000 ms (2 seconds)
    // timer_increment calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 10000);
    timer_increment(2000);

    // Simulate delay of 1.5 seconds (value now ~500ms)
    // At T=11500: elapsed = 11500 - 10000 = 1500, value = 2000 - 1500 = 500ms

    // Call timer_increment(0) to trigger the check
    // timer_increment calls timer_get_value_ms (1 epoch call)
    // value will be < 1000, so timer_reset is called (1 epoch call)
    will_return(epoch, 11500);
    will_return(epoch, 11500);  // timer_reset call
    timer_increment(0);

    // Assert length == 0 (auto-reset triggered)
    assert_int_equal(timer_get_length_ms(), 0);
}

// 19. test_timer_check_elapsed_repeat_final
// Purpose: Verify that timer_check_elapsed() does NOT restart on the final repeat (repeat_count == 1).
// When repeat_count == 1, the timer has completed its last repeat and should vibrate normally.
static void test_timer_check_elapsed_repeat_final(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 10000);
    timer_increment(5000);

    // Set up repeating timer with final repeat
    timer_data.base_length_ms = 5000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 1; // Final repeat - should NOT restart
    timer_data.can_vibrate = true;

    // Simulate delay of 7 seconds (enter chrono)
    // timer_check_elapsed calls:
    // 1. timer_is_chrono (1 epoch call)
    // 2. timer_is_paused (0 calls)
    // 3. repeat_count is 1, NOT > 1, so skip repeat restart
    // 4. timer_get_value_ms (1 epoch call) -> returns ~2000ms (under 30s)
    // 5. Vibrates with custom pattern
    will_return(epoch, 17000);
    will_return(epoch, 17000);

    // Expect vibes_enqueue_custom_pattern (normal vibration, NOT long_pulse)
    expect_function_call(vibes_enqueue_custom_pattern);

    timer_check_elapsed();

    // Assert repeat_count unchanged (not decremented)
    assert_int_equal(timer_data.repeat_count, 1);
}

// 20. test_timer_reset_clears_repeat
// Purpose: Verify that timer_reset() clears repeat state.
static void test_timer_reset_clears_repeat(void **state) {
    // Setup: set repeat state
    timer_data.is_repeating = true;
    timer_data.repeat_count = 3;
    timer_data.length_ms = 60000;
    timer_data.base_length_ms = 60000;

    // timer_reset() calls epoch() once
    will_return(epoch, 10000);

    timer_reset();

    // Assert repeat state is cleared
    assert_false(timer_data.is_repeating);
    assert_int_equal(timer_data.repeat_count, 0);
}

// 21. test_timer_check_elapsed_repeat_decrements_to_final
// Purpose: Verify that timer_check_elapsed() decrements from 2 to 1, restarting the timer.
// After this, the next elapsed check with count=1 should NOT restart.
static void test_timer_check_elapsed_repeat_decrements_to_final(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 10000);
    timer_increment(5000);

    // Set up repeating timer with count=2 (one more repeat remaining)
    timer_data.base_length_ms = 5000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 2;
    timer_data.can_vibrate = true;

    // Simulate delay of 7 seconds (enter chrono)
    // timer_check_elapsed calls:
    // 1. timer_is_chrono (1 epoch call)
    // 2. timer_is_paused (0 calls)
    // 3. repeat_count=2 > 1, so decrement and restart
    // 4. timer_increment(base_length_ms) calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 17000);
    // timer_increment inside check_elapsed
    will_return(epoch, 17000);

    // Expect vibes_long_pulse (for repeat restart)
    expect_function_call(vibes_long_pulse);

    timer_check_elapsed();

    // Assert repeat_count == 1 (decremented from 2)
    assert_int_equal(timer_data.repeat_count, 1);
    // Assert timer is still repeating
    assert_true(timer_data.is_repeating);
}

// 22. test_timer_check_elapsed_repeat_zero_count
// Purpose: Verify that timer_check_elapsed() does NOT restart when repeat_count is 0.
// When repeat mode is first enabled, repeat_count starts at 0 (displayed as "_x").
// This is equivalent to 1x (no actual repeat), so the timer should vibrate normally.
static void test_timer_check_elapsed_repeat_zero_count(void **state) {
    // Setup: reset timer at T=10000
    will_return(epoch, 10000);
    timer_reset();

    // Increment to 5000 ms
    // timer_increment calls timer_get_value_ms (1 epoch call)
    will_return(epoch, 10000);
    timer_increment(5000);

    // Set up repeating timer with count=0 (initial state after enabling repeat)
    timer_data.base_length_ms = 5000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 0; // Initial state - should NOT restart
    timer_data.can_vibrate = true;

    // Simulate delay of 7 seconds (enter chrono)
    // timer_check_elapsed calls:
    // 1. timer_is_chrono (1 epoch call)
    // 2. timer_is_paused (0 calls)
    // 3. repeat_count is 0, NOT > 1, so skip repeat restart
    // 4. timer_get_value_ms (1 epoch call) -> returns ~2000ms (under 30s)
    // 5. Vibrates with custom pattern (normal vibration)
    will_return(epoch, 17000);
    will_return(epoch, 17000);

    // Expect vibes_enqueue_custom_pattern (normal vibration, NOT long_pulse)
    expect_function_call(vibes_enqueue_custom_pattern);

    timer_check_elapsed();

    // Assert repeat_count unchanged
    assert_int_equal(timer_data.repeat_count, 0);
}

// 23. test_timer_chrono_subtraction_to_countdown
// Purpose: Verify that subtracting time from a chrono (stopwatch) timer converts it to a countdown.
// Bug reproduction: When timer_increment_chrono(-60000) is called on a chrono with 5 seconds elapsed,
// start_ms is pushed into the future (start_ms > epoch). The old modulo-based math doesn't handle this.
static void test_timer_chrono_subtraction_to_countdown(void **state) {
    // Setup: chrono timer with 5 seconds elapsed
    // epoch() = 100000, start_ms = 95000 (started 5 seconds ago), length_ms = 0
    timer_data.length_ms = 0;
    timer_data.start_ms = 95000;

    // Verify initial state is chrono (timer_is_chrono checks raw_value <= 0)
    // elapsed = epoch() - start_ms = 100000 - 95000 = 5000
    // raw_value = length_ms - elapsed = 0 - 5000 = -5000 <= 0, so IS chrono
    // timer_is_chrono calls epoch() once for running timer
    will_return(epoch, 100000);
    assert_true(timer_is_chrono());

    // Subtract 1 minute (60 seconds) from the chrono
    // This should convert it to a countdown timer with ~55 seconds remaining
    timer_increment_chrono(-60000);

    // Verify: start_ms should now be in the future
    // start_ms = 95000 - (-60000) = 95000 + 60000 = 155000
    assert_int_equal(timer_data.start_ms, 155000);

    // Check: timer_is_chrono should return FALSE (it's now a countdown)
    // elapsed = epoch() - start_ms = 100000 - 155000 = -55000 (negative = not yet elapsed)
    // raw_value = length_ms - elapsed = 0 - (-55000) = 55000 > 0, so NOT chrono
    // timer_is_chrono calls epoch() once
    will_return(epoch, 100000);
    assert_false(timer_is_chrono());

    // Check: timer_get_value_ms should return ~55000 (55 seconds remaining)
    // elapsed = epoch() - start_ms = 100000 - 155000 = -55000
    // raw_value = length_ms - elapsed = 0 - (-55000) = 55000
    // timer_get_value_ms calls epoch() once
    will_return(epoch, 100000);
    int64_t value = timer_get_value_ms();
    // Expected: 55000 ms (55 seconds countdown)
    assert_int_equal(value, 55000);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test_setup_teardown(test_timer_reset, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_increment, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_pause, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_start, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_get_time_parts, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_is_chrono_false, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_is_chrono_true, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_is_vibrating, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_increment_chrono, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_rewind, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_restart_countdown, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_restart_chrono, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_check_elapsed_vibrates, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_check_elapsed_auto_snooze, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_check_elapsed_repeat, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_sub_minute_valid, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_sub_second_resets, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_crosses_sub_second_resets, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_check_elapsed_repeat_final, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_reset_clears_repeat, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_check_elapsed_repeat_decrements_to_final, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_check_elapsed_repeat_zero_count, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_chrono_subtraction_to_countdown, setup, teardown),
    };

    return cmocka_run_group_tests(tests, NULL, NULL);
}
