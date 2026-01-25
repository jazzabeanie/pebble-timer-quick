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

// Mock vibration functions (stubs)
void vibes_long_pulse(void) {
}

void vibes_enqueue_custom_pattern(VibePattern pattern) {
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

    // timer_increment calls timer_get_value_ms which calls epoch() 3 times
    // when start_ms = 0 (paused), timer_get_value_ms returns length_ms
    // The formula: value = length - epoch + (((start + epoch - 1) % epoch) + 1)
    // With start=0: value = length - epoch + ((epoch - 1) % epoch + 1) = length - epoch + epoch = length
    will_return(epoch, 50000);
    will_return(epoch, 50000);
    will_return(epoch, 50000);

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
    // timer_increment calls timer_get_value_ms which calls epoch() 3 times
    will_return(epoch, 10000);
    will_return(epoch, 10000);
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
    // When paused (start_ms < 0), the formula:
    // value = length - epoch + (((start + epoch - 1) % epoch) + 1)
    // With start=-2000, epoch=12000:
    // (start + epoch - 1) = -2000 + 12000 - 1 = 9999
    // 9999 % 12000 = 9999
    // value = 10000 - 12000 + 9999 + 1 = 8000
    will_return(epoch, 12000);
    will_return(epoch, 12000);
    will_return(epoch, 12000);
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
    will_return(epoch, 10000);
    will_return(epoch, 10000);
    will_return(epoch, 10000);
    timer_increment(10000);
    // State: start_ms=10000, length_ms=10000, RUNNING

    // Step 3: Simulate delay 2s by advancing epoch to 12000
    // The timer is already running from reset

    // Step 4: Check timer value
    // When running (start_ms > 0), the formula:
    // value = length - epoch + (((start + epoch - 1) % epoch) + 1)
    // With start=10000, epoch=12000:
    // (start + epoch - 1) = 10000 + 12000 - 1 = 21999
    // 21999 % 12000 = 9999
    // value = 10000 - 12000 + 9999 + 1 = 8000
    will_return(epoch, 12000);
    will_return(epoch, 12000);
    will_return(epoch, 12000);
    int64_t value = timer_get_value_ms();

    // Assert value has decreased from 10000
    assert_true(value < 10000);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test_setup_teardown(test_timer_reset, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_increment, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_pause, setup, teardown),
        cmocka_unit_test_setup_teardown(test_timer_start, setup, teardown),
    };

    return cmocka_run_group_tests(tests, NULL, NULL);
}
