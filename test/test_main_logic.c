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

// Backlight mock
void light_enable(bool enable) {}

// Test logging mock
void test_log_state(const char *event) {}

// --- Settings stubs ---
#include "../src/settings.h"
static bool s_mock_swap_back_and_select_long = false;
void settings_init(SettingsChangeCallback on_change) {}
void settings_save(void) {}
bool settings_get_show_increment_icons(void)    { return true; }
bool settings_get_show_direction_icon(void)     { return true; }
bool settings_get_show_quit_icon(void)          { return true; }
bool settings_get_show_to_bg_icon(void)         { return true; }
bool settings_get_show_edit_icon(void)          { return true; }
bool settings_get_show_play_pause_icon(void)    { return true; }
bool settings_get_show_details_icon(void)       { return true; }
bool settings_get_show_repeat_enable_icon(void) { return true; }
bool settings_get_show_alarm_reset_icon(void)   { return true; }
bool settings_get_show_silence_icon(void)       { return true; }
bool settings_get_show_snooze_icon(void)        { return true; }
bool settings_get_swap_back_and_select_long(void) { return s_mock_swap_back_and_select_long; }
bool settings_get_multiple_timers_enabled(void) { return false; }
bool settings_get_voice_naming_enabled(void) { return false; }

// --- Timer List stub ---
void timer_list_window_push(void) {}

// --- Launch reason / wakeup event stubs ---
AppLaunchReason launch_reason(void) { return APP_LAUNCH_SYSTEM; }
bool wakeup_get_launch_event(WakeupId *wakeup_id, int32_t *cookie) { return false; }

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

// Test that first launch (no persisted data) starts in New mode, not chrono
static void test_first_launch_starts_in_new_mode(void **state) {
    // Simulate fresh install: timer_reset() sets length_ms=0, start_ms=0, is_paused=true
    // This is what timer_persist_read() does when no data exists (persist_exists returns false)
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    timer_data.reset_on_init = false;

    // Clear main_data to simulate fresh state
    memset(&main_data, 0, sizeof(main_data));

    // Run initialization
    prv_initialize();

    // Should start in ControlModeNew, NOT ControlModeCounting (chrono)
    assert_int_equal(main_data.control_mode, ControlModeNew);
}

// When swap setting is on, Back in New mode should toggle to EditSec (not add time)
static void test_swap_back_toggles_to_editsec_from_new(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeNew;
    s_mock_swap_back_and_select_long = true;

    prv_back_click_handler(NULL, NULL);

    assert_int_equal(main_data.control_mode, ControlModeEditSec);
    assert_int_equal(timer_data.length_ms, 0); // no time added

    s_mock_swap_back_and_select_long = false;
}

// When swap setting is on, Select long in New mode should add 60 min (not switch to EditSec)
static void test_swap_select_long_adds_time_in_new(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeNew;
    s_mock_swap_back_and_select_long = true;

    prv_select_long_click_handler(NULL, NULL);

    assert_int_equal(main_data.control_mode, ControlModeNew); // stays in New
    assert_int_equal(timer_data.length_ms, 3600000); // 60 min added

    s_mock_swap_back_and_select_long = false;
}

// Hold Up at the final alarm of a repeating timer: the original timer must
// restart in full — base length AND base repeat count — not the accumulated total.
static void test_up_long_restarts_repeating_timer_after_final_alarm(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeCounting;

    // 1-min timer set to repeat 10 times, now at its final alarm:
    // running, vibrating, 2s past the elapse point
    s_mock_epoch = 1000000;
    timer_data.length_ms = 60000;
    timer_data.base_length_ms = 60000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 1; // final alarm
    timer_data.base_repeat_count = 10;
    timer_data.can_vibrate = true;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch - 62000;

    prv_up_long_click_handler(NULL, NULL);

    // The original 1-min timer restarts, repeats included
    assert_int_equal(timer_data.length_ms, 60000);
    assert_true(timer_data.is_repeating);
    assert_int_equal(timer_data.repeat_count, 10);
    assert_false(timer_is_chrono());
    // 2s overshoot past the alarm is deducted from the fresh cycle
    assert_int_equal(timer_get_value_ms(), 58000);
}

// Hold Up at the alarm of a non-repeating timer: restart at the base length,
// not base added on top of the old length (2x).
static void test_up_long_restarts_nonrepeating_timer_at_base_length(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeCounting;

    // 1-min non-repeating timer, alarm ringing for 2s
    s_mock_epoch = 2000000;
    timer_data.length_ms = 60000;
    timer_data.base_length_ms = 60000;
    timer_data.can_vibrate = true;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch - 62000;

    prv_up_long_click_handler(NULL, NULL);

    assert_int_equal(timer_data.length_ms, 60000);
    assert_false(timer_data.is_repeating);
    assert_int_equal(timer_get_value_ms(), 58000);
}

// After a repeat has fired, turning repeats off (hold Up while counting) must
// leave the timer at its original length, not the accumulated total.
static void test_toggle_repeat_off_after_repeat_keeps_original_length(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeCounting;

    // 1-min timer repeating 2 times, running from t0
    s_mock_epoch = 3000000;
    timer_data.length_ms = 60000;
    timer_data.base_length_ms = 60000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 2;
    timer_data.base_repeat_count = 2;
    timer_data.can_vibrate = true;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch;

    // First cycle elapses (1s past the alarm) and auto-repeats
    s_mock_epoch += 61000;
    timer_check_elapsed();
    assert_int_equal(timer_data.repeat_count, 1);

    // User turns repeats off with a long Up press while counting
    prv_up_long_click_handler(NULL, NULL);

    assert_false(timer_data.is_repeating);
    assert_int_equal(timer_data.repeat_count, 0);
    // Original 1-min length, not 2 minutes
    assert_int_equal(timer_data.length_ms, 60000);
    // Second cycle keeps counting down (1s overshoot deducted)
    assert_int_equal(timer_get_value_ms(), 59000);
}

// Pressing Down during an intermediate repeat alarm restarts the cycle at the
// base length instead of accumulating onto length_ms.
static void test_down_click_intermediate_repeat_keeps_base_length(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeCounting;

    // 1-min timer with repeats remaining, alarm ringing for 1s
    s_mock_epoch = 4000000;
    timer_data.length_ms = 60000;
    timer_data.base_length_ms = 60000;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 3;
    timer_data.base_repeat_count = 3;
    timer_data.can_vibrate = true;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch - 61000;

    prv_down_click_handler(NULL, NULL);

    assert_int_equal(timer_data.repeat_count, 2);
    assert_int_equal(timer_data.length_ms, 60000);
    assert_int_equal(timer_get_value_ms(), 59000);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_seconds_timer_bug),
        cmocka_unit_test(test_first_launch_starts_in_new_mode),
        cmocka_unit_test(test_swap_back_toggles_to_editsec_from_new),
        cmocka_unit_test(test_swap_select_long_adds_time_in_new),
        cmocka_unit_test(test_up_long_restarts_repeating_timer_after_final_alarm),
        cmocka_unit_test(test_up_long_restarts_nonrepeating_timer_at_base_length),
        cmocka_unit_test(test_toggle_repeat_off_after_repeat_keeps_original_length),
        cmocka_unit_test(test_down_click_intermediate_repeat_keeps_base_length),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
