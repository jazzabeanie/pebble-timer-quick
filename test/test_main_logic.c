#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>

#include "pebble.h"
#include "utility.h"

// --- Mocks for Pebble SDK ---
// Time
static uint64_t s_mock_epoch = 1000000;
uint64_t epoch(void) {
  return s_mock_epoch;
}

// Window
Window* window_create(void) { return (Window*)1; }
void window_destroy(Window* window) {}
void window_set_click_config_provider(Window *window, ClickConfigProvider click_config_provider) {}
Layer* window_get_root_layer(Window *window) { return (Layer*)1; }
GRect layer_get_bounds(Layer *layer) { return (GRect){{0,0},{144,168}}; }
void window_stack_push(Window *window, bool animated) {}
void window_stack_pop(bool animated) {}
void window_single_click_subscribe(ButtonId button_id, ClickHandler handler) {}
void window_raw_click_subscribe(ButtonId button_id, void* down_handler, void* up_handler, void* context) {}
void window_long_click_subscribe(ButtonId button_id, uint16_t delay_ms, ClickHandler handler, void* context) {}

// Layer
Layer* layer_create(GRect frame) { return (Layer*)1; }
void layer_destroy(Layer* layer) {}
void layer_set_update_proc(Layer *layer, void* proc) {}
void layer_add_child(Layer *parent, Layer *child) {}
void layer_mark_dirty(Layer *layer) {}

// Timer/Wakeup
AppTimer* app_timer_register(uint32_t timeout_ms, AppTimerCallback callback, void* callback_data) { return (AppTimer*)1; }
void app_timer_cancel(AppTimer* timer) {}
void app_timer_reschedule(AppTimer* timer, uint32_t new_timeout_ms) {}
void tick_timer_service_subscribe(TimeUnits tick_units, void* handler) {}
void tick_timer_service_unsubscribe(void) {}
void wakeup_cancel_all(void) {}
void wakeup_schedule(time_t timestamp, uint32_t cookie, bool notify_if_missed) {}

// Vibration
void vibes_long_pulse(void) {}
void vibes_enqueue_custom_pattern(VibePattern pattern) {}
void vibes_cancel(void) {}
void vibes_short_pulse(void) {}

// Persistence (Stubs)
int32_t persist_read_int(const uint32_t key) { return 0; }
status_t persist_write_int(const uint32_t key, const int32_t value) { return 0; }
int persist_write_data(const uint32_t key, const void *data, const size_t size) { return size; }
bool persist_exists(const uint32_t key) { return false; }
status_t persist_delete(const uint32_t key) { return 0; }
int persist_read_data(const uint32_t key, void *buffer, const size_t buffer_size) { return 0; }

// --- Mocks for drawing.h ---
void drawing_start_bounce_animation(bool upward) {}
void drawing_start_reset_animation(void) {}
void drawing_render(Layer *layer, GContext *ctx) {}
void drawing_update(void) {}
void drawing_initialize(Layer *layer) {}
void drawing_terminate(void) {}

// Utility Mocks
void assert(void *ptr, const char *file, int line) {
    if (!ptr) {
        printf("Assertion failed in %s:%d\n", file, line);
    }
}

// App event loop mock
void app_event_loop(void) {}

// --- Include main.c logic ---
// We redefine main to avoid conflict, and to allow us to test static functions
#define main app_main
#include "../src/main.c"
#undef main

// --- Test Case ---
static void test_seconds_timer_bug(void **state) {
    // 1. Initialize logic
    // Reset timer data (timer_data is defined in timer.c, but main.c includes timer.h.
    // We link against timer.c so we share the global variable.)

    // We need to access timer_data directly. main.c includes timer.h which declares it extern.
    // timer.c defines it.
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset(); // Helper from timer.c

    // Set initial control mode to ControlModeNew (default entry)
    main_data.control_mode = ControlModeNew;
    main_data.is_editing_existing_timer = false;

    // 2. Simulate holding Select to enter Edit Seconds mode
    prv_select_long_click_handler(NULL, NULL);

    // Check state: should be in ControlModeEditSec
    assert_int_equal(main_data.control_mode, ControlModeEditSec);

    // 3. Simulate pressing UP to add 20 seconds
    prv_up_click_handler(NULL, NULL);

    // Expectation: Length should increase by 20s.
    // If bug exists: length_ms is 0 (chrono mode editing elapsed time).
    // If fixed: length_ms is 20000 (countdown mode setting duration).
    assert_int_equal(timer_data.length_ms, 20000);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_seconds_timer_bug),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
