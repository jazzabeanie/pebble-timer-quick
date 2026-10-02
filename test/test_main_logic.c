#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>

#include "pebble.h"
#include "utility.h"
#include "timer.h"

// --- Log capture ---
// Every APP_LOG / TEST_LOG line and every test_log_state() event is recorded,
// so a test can count events such as "alarm_start" or "alarm_held,slot=1".
#define LOG_LINE_COUNT 600
#define LOG_LINE_LEN 128
static char s_log_lines[LOG_LINE_COUNT][LOG_LINE_LEN];
static int s_log_line_count = 0;

static void prv_log_clear(void) {
  s_log_line_count = 0;
}

static void prv_capture_log(const char *fmt, ...) {
  if (s_log_line_count >= LOG_LINE_COUNT) {
    return;
  }
  va_list args;
  va_start(args, fmt);
  vsnprintf(s_log_lines[s_log_line_count++], LOG_LINE_LEN, fmt, args);
  va_end(args);
}

// Number of recorded lines that contain `needle`
static int prv_log_count(const char *needle) {
  int count = 0;
  for (int i = 0; i < s_log_line_count; i++) {
    if (strstr(s_log_lines[i], needle)) {
      count++;
    }
  }
  return count;
}

#undef APP_LOG
#define APP_LOG(level, fmt, args...) prv_capture_log(fmt, ## args)

// --- Mocks for Pebble SDK ---
// Time
static uint64_t s_mock_epoch = 1000000;
uint64_t epoch(void) {
  return s_mock_epoch;
}

// Window
Window* window_create(void) { return (Window*)1; }
void window_destroy(Window* window) {}
Layer* window_get_root_layer(Window *window) { return (Layer*)1; }
GRect layer_get_bounds(Layer *layer) { return (GRect){{0,0},{144,168}}; }
void window_stack_push(Window *window, bool animated) {}
static int s_window_pop_count = 0;
void window_stack_pop(bool animated) { s_window_pop_count++; }
// Click subscriptions are recorded so the simulator (prv_sim_press) can drive
// the app's real handlers in the order the SDK fires them.
#define SIM_BUTTON_COUNT 4
static ClickHandler s_sub_single[SIM_BUTTON_COUNT];
static ClickHandler s_sub_raw_down[SIM_BUTTON_COUNT];
static ClickHandler s_sub_raw_up[SIM_BUTTON_COUNT];
static ClickHandler s_sub_long[SIM_BUTTON_COUNT];
static uint16_t s_sub_long_delay[SIM_BUTTON_COUNT];
void window_single_click_subscribe(ButtonId button_id, ClickHandler handler) {
  s_sub_single[button_id] = handler;
}
void window_raw_click_subscribe(ButtonId button_id, void* down_handler, void* up_handler, void* context) {
  s_sub_raw_down[button_id] = (ClickHandler)down_handler;
  s_sub_raw_up[button_id] = (ClickHandler)up_handler;
}
void window_long_click_subscribe(ButtonId button_id, uint16_t delay_ms, ClickHandler handler, void* context) {
  s_sub_long[button_id] = handler;
  s_sub_long_delay[button_id] = delay_ms;
}
// Multi-click subscriptions. A button with one is "armed" for a double press.
static ClickHandler s_sub_multi[SIM_BUTTON_COUNT];
static uint16_t s_sub_multi_timeout[SIM_BUTTON_COUNT];
void window_multi_click_subscribe(ButtonId button_id, uint8_t min_clicks, uint8_t max_clicks,
                                  uint16_t timeout, bool last_click_only, ClickHandler handler) {
  s_sub_multi[button_id] = handler;
  s_sub_multi_timeout[button_id] = timeout;
}
// As the SDK does for a visible window: drop the old subscriptions and call
// the provider at once
void window_set_click_config_provider(Window *window, ClickConfigProvider click_config_provider) {
  memset(s_sub_multi, 0, sizeof(s_sub_multi));
  click_config_provider(window);
}

// Layer
Layer* layer_create(GRect frame) { return (Layer*)1; }
void layer_destroy(Layer* layer) {}
void layer_set_update_proc(Layer *layer, void* proc) {}
void layer_add_child(Layer *parent, Layer *child) {}
void layer_mark_dirty(Layer *layer) {}

// Timer/Wakeup
// A small fake AppTimer scheduler. Registered callbacks fire in due-time order
// when a test advances the mock clock with prv_run_until(). Tests that never
// advance the clock see the old behavior (callbacks never fire).
#define FAKE_TIMER_COUNT 32
typedef struct {
  bool active;
  uint64_t due_ms;
  AppTimerCallback callback;
  void *data;
} FakeTimer;
static FakeTimer s_fake_timers[FAKE_TIMER_COUNT];
static FakeTimer s_fake_timer_sink;  // returned when full; never fires

static void prv_fake_timers_clear(void) {
  memset(s_fake_timers, 0, sizeof(s_fake_timers));
}

AppTimer* app_timer_register(uint32_t timeout_ms, AppTimerCallback callback, void* callback_data) {
  for (int i = 0; i < FAKE_TIMER_COUNT; i++) {
    if (!s_fake_timers[i].active) {
      s_fake_timers[i] = (FakeTimer){true, s_mock_epoch + timeout_ms, callback, callback_data};
      return (AppTimer*)&s_fake_timers[i];
    }
  }
  s_fake_timer_sink.active = false;
  return (AppTimer*)&s_fake_timer_sink;
}
void app_timer_cancel(AppTimer* timer) {
  if (timer) ((FakeTimer*)timer)->active = false;
}
void app_timer_reschedule(AppTimer* timer, uint32_t new_timeout_ms) {
  if (timer) ((FakeTimer*)timer)->due_ms = s_mock_epoch + new_timeout_ms;
}

// Advance the mock clock to target_ms, firing every due fake timer in order.
static void prv_run_until(uint64_t target_ms) {
  for (int guard = 0; guard < 100000; guard++) {
    FakeTimer *next = NULL;
    for (int i = 0; i < FAKE_TIMER_COUNT; i++) {
      FakeTimer *t = &s_fake_timers[i];
      if (t->active && t->due_ms <= target_ms && (!next || t->due_ms < next->due_ms)) {
        next = t;
      }
    }
    if (!next) break;
    next->active = false;
    if (next->due_ms > s_mock_epoch) s_mock_epoch = next->due_ms;
    next->callback(next->data);
  }
  if (target_ms > s_mock_epoch) s_mock_epoch = target_ms;
}
void tick_timer_service_subscribe(TimeUnits tick_units, void* handler) {}
void tick_timer_service_unsubscribe(void) {}

// Wakeup mock. Records every wakeup_schedule() call with its result, and
// applies the SDK rules: no time in the past (E_INVALID_ARGUMENT) and no
// wakeup within 1 minute of another scheduled one, ours or another app's
// (E_RANGE). wakeup_cancel_all() cancels only this app's wakeups.
#define FAKE_WAKEUP_COUNT 16
typedef struct {
  time_t time;
  int32_t cookie;
  WakeupId result;
} FakeWakeup;
static FakeWakeup s_wakeups[FAKE_WAKEUP_COUNT];
static int s_wakeup_count = 0;
static time_t s_other_app_wakeups[4];
static int s_other_app_wakeup_count = 0;
static int s_wakeup_cancel_all_count = 0;

static void prv_wakeups_reset(void) {
  s_wakeup_count = 0;
  s_other_app_wakeup_count = 0;
  s_wakeup_cancel_all_count = 0;
}

// Another app's wakeup: ours fail with E_RANGE within 1 minute of it
static void prv_add_other_app_wakeup(time_t when) {
  s_other_app_wakeups[s_other_app_wakeup_count++] = when;
}

void wakeup_cancel_all(void) {
  s_wakeup_cancel_all_count++;
  s_wakeup_count = 0;
}

static bool prv_within_one_minute(time_t a, time_t b) {
  return (a > b ? a - b : b - a) < 60;
}

WakeupId wakeup_schedule(time_t timestamp, int32_t cookie, bool notify_if_missed) {
  WakeupId result = s_wakeup_count + 1;
  if (timestamp <= (time_t)(s_mock_epoch / 1000)) {
    result = E_INVALID_ARGUMENT;
  }
  for (int i = 0; i < s_other_app_wakeup_count && result >= 0; i++) {
    if (prv_within_one_minute(timestamp, s_other_app_wakeups[i])) result = E_RANGE;
  }
  for (int i = 0; i < s_wakeup_count && result >= 0; i++) {
    if (s_wakeups[i].result >= 0 && prv_within_one_minute(timestamp, s_wakeups[i].time)) {
      result = E_RANGE;
    }
  }
  if (s_wakeup_count < FAKE_WAKEUP_COUNT) {
    s_wakeups[s_wakeup_count++] = (FakeWakeup){timestamp, cookie, result};
  }
  return result;
}

// Vibration
// The voice-rename feedback is "one short pulse = renamed, three pulses =
// nothing changed". The three-pulse pattern goes through the custom-pattern
// call, so the two are told apart by which counter moves.
static int s_short_pulse_count = 0;
static int s_custom_pattern_count = 0;
static uint32_t s_last_pattern_segments[8];
static int s_last_pattern_num_segments = 0;

static void prv_reset_vibe_counters(void) {
    s_short_pulse_count = 0;
    s_custom_pattern_count = 0;
    s_last_pattern_num_segments = 0;
    memset(s_last_pattern_segments, 0, sizeof(s_last_pattern_segments));
}

void vibes_long_pulse(void) {}
void vibes_enqueue_custom_pattern(VibePattern pattern) {
    s_custom_pattern_count++;
    s_last_pattern_num_segments = pattern.num_segments;
    for (int i = 0; i < pattern.num_segments && i < (int)ARRAY_LENGTH(s_last_pattern_segments); i++) {
        s_last_pattern_segments[i] = pattern.durations[i];
    }
}
void vibes_cancel(void) {}
void vibes_short_pulse(void) { s_short_pulse_count++; }

// --- Dictation stubs ---
// A non-NULL opaque handle is enough: main.c only passes it back to the stubs.
static DictationSession *const s_mock_dictation_session = (DictationSession *)0xD1C7;
static bool s_mock_phone_connected = true;
static bool s_last_enable_confirmation = true;
static bool s_last_enable_error_dialogs = false;
static int s_dictation_start_count = 0;

DictationSession *dictation_session_create(uint32_t buffer_size,
                                           DictationSessionStatusCallback callback, void *context) {
    return s_mock_dictation_session;
}
void dictation_session_destroy(DictationSession *session) {}
DictationSessionStatus dictation_session_start(DictationSession *session) {
    s_dictation_start_count++;
    return DictationSessionStatusSuccess;
}
DictationSessionStatus dictation_session_stop(DictationSession *session) {
    return DictationSessionStatusSuccess;
}
void dictation_session_enable_confirmation(DictationSession *session, bool is_enabled) {
    s_last_enable_confirmation = is_enabled;
}
void dictation_session_enable_error_dialogs(DictationSession *session, bool is_enabled) {
    s_last_enable_error_dialogs = is_enabled;
}

bool connection_service_peek_pebble_app_connection(void) { return s_mock_phone_connected; }

// Persistence: a small key-value store. It is off by default (nothing is
// stored and every read finds nothing, like a fresh install), so tests that do
// not relaunch the app are not affected. prv_persist_reset(true) turns it on.
#define FAKE_PERSIST_COUNT 48
#define FAKE_PERSIST_SIZE 128
typedef struct {
  bool used;
  uint32_t key;
  size_t size;
  uint8_t data[FAKE_PERSIST_SIZE];
} FakePersist;
static FakePersist s_persist[FAKE_PERSIST_COUNT];
static bool s_persist_enabled = false;

static void prv_persist_reset(bool enabled) {
  memset(s_persist, 0, sizeof(s_persist));
  s_persist_enabled = enabled;
}

static FakePersist *prv_persist_find(uint32_t key, bool create) {
  FakePersist *free_entry = NULL;
  if (!s_persist_enabled) {
    return NULL;
  }
  for (int i = 0; i < FAKE_PERSIST_COUNT; i++) {
    if (s_persist[i].used && s_persist[i].key == key) return &s_persist[i];
    if (!s_persist[i].used && !free_entry) free_entry = &s_persist[i];
  }
  if (create && free_entry) {
    free_entry->used = true;
    free_entry->key = key;
    return free_entry;
  }
  return NULL;
}

int persist_write_data(const uint32_t key, const void *data, const size_t size) {
  FakePersist *entry = prv_persist_find(key, true);
  if (entry && size <= FAKE_PERSIST_SIZE) {
    memcpy(entry->data, data, size);
    entry->size = size;
  }
  return size;
}
int persist_read_data(const uint32_t key, void *buffer, const size_t buffer_size) {
  FakePersist *entry = prv_persist_find(key, false);
  if (!entry) return 0;
  size_t size = entry->size < buffer_size ? entry->size : buffer_size;
  memcpy(buffer, entry->data, size);
  return size;
}
int32_t persist_read_int(const uint32_t key) {
  int32_t value = 0;
  persist_read_data(key, &value, sizeof(value));
  return value;
}
status_t persist_write_int(const uint32_t key, const int32_t value) {
  persist_write_data(key, &value, sizeof(value));
  return 0;
}
bool persist_exists(const uint32_t key) { return prv_persist_find(key, false) != NULL; }
status_t persist_delete(const uint32_t key) {
  FakePersist *entry = prv_persist_find(key, false);
  if (entry) entry->used = false;
  return 0;
}

// --- Mocks for drawing.h ---
void drawing_start_bounce_animation(bool upward) {}
void drawing_start_reset_animation(void) {}
void drawing_render(Layer *layer, GContext *ctx) {}
void drawing_update(void) {}
void drawing_initialize(Layer *layer) {}
void drawing_terminate(void) {}
static int8_t s_mock_slot_override = -1;
void drawing_set_slot_override(int8_t slot) { s_mock_slot_override = slot; }
int8_t drawing_get_slot_override(void) { return s_mock_slot_override; }
// Display freeze: the time the display is frozen at, or -1 when not frozen
static int64_t s_mock_freeze_ms = -1;
void drawing_set_freeze_ms(int64_t at_ms) { s_mock_freeze_ms = at_ms; }
void drawing_clear_freeze(void) { s_mock_freeze_ms = -1; }

// Utility Mocks
void assert(void *ptr, const char *file, int line) {
    if (!ptr) {
        printf("Assertion failed in %s:%d\n", file, line);
    }
}

// App event loop mock
void app_event_loop(void) {}

// Backlight mock. Models what the user sees: every button press lights the
// screen for SYSTEM_LIGHT_MS (the system's own timeout); light_enable(true)
// forces it on; light_enable(false) returns to automatic control and turns the
// light off at once (the observed symptom on the watch).
#define SYSTEM_LIGHT_MS 3000
static bool s_light_forced = false;
static uint64_t s_light_auto_until = 0;
void light_enable(bool enable) {
  s_light_forced = enable;
  if (!enable) s_light_auto_until = 0;
}
void light_enable_interaction(void) {
  if (!s_light_forced) s_light_auto_until = s_mock_epoch + SYSTEM_LIGHT_MS;
}
static bool prv_light_is_on(void) {
  return s_light_forced || s_mock_epoch < s_light_auto_until;
}

// Test logging mock: record the event name
void test_log_state(const char *event) {
  prv_capture_log("TEST_STATE:%s", event);
}

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
static bool s_mock_multiple_timers = false;
bool settings_get_multiple_timers_enabled(void) { return s_mock_multiple_timers; }
bool settings_get_voice_naming_enabled(void) { return false; }
static bool s_mock_lap_stopwatch_enabled = false;
bool settings_get_lap_stopwatch_enabled(void) { return s_mock_lap_stopwatch_enabled; }
static uint32_t s_mock_screen_on_seconds = 10;
static uint32_t s_mock_down_extra_seconds = 60;
uint32_t settings_get_screen_on_seconds(void) { return s_mock_screen_on_seconds; }
uint32_t settings_get_down_extra_seconds(void) { return s_mock_down_extra_seconds; }

// --- Timer List stub ---
// The stub only counts the pushes and tracks "on top". A test leaves the list
// by clearing s_mock_list_on_top and calling main_show_alarm() or
// main_watch_arm(), as the real list does.
#include "../src/timer_list.h"
static int s_timer_list_push_count = 0;
static bool s_mock_list_on_top = false;
void timer_list_window_push(void) {
  s_timer_list_push_count++;
  s_mock_list_on_top = true;
}
bool timer_list_is_on_top(void) { return s_mock_list_on_top; }

// --- Launch reason / wakeup event stubs ---
static AppLaunchReason s_mock_launch_reason = APP_LAUNCH_SYSTEM;
AppLaunchReason launch_reason(void) { return s_mock_launch_reason; }
static int32_t s_mock_launch_cookie = 0;
bool wakeup_get_launch_event(WakeupId *wakeup_id, int32_t *cookie) {
  *cookie = s_mock_launch_cookie;
  return true;
}

// --- Include main.c logic ---
// We redefine main to avoid conflict, and to allow us to test static functions
#define main app_main
#include "../src/main.c"
#undef main

// Put the app's static state back to what a new process starts with. Every
// launch helper calls this, so a stale AppTimer pointer from an earlier test
// can never cancel a timer of the current one. The persist store is turned
// off; a test that relaunches the app turns it on (prv_sim_begin).
static void prv_reset_app_statics(void) {
    memset(&main_data, 0, sizeof(main_data));
    backlight_timer = NULL;
    backlight_on = false;
    s_light_forced = false;
    s_light_auto_until = 0;
    s_up_held = false;
    s_up_chord_consumed = false;
    s_watch_timer = NULL;
    s_held_logged_mask = 0;
    s_blocked_buttons = 0;
    s_window_pop_count = 0;
    s_mock_list_on_top = false;
    s_timer_list_push_count = 0;
    s_mock_slot_override = -1;
    s_mock_freeze_ms = -1;
    memset(s_sub_multi, 0, sizeof(s_sub_multi));
}

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

// Every interaction handler must leave the backlight consistent with the
// current control mode. The Down handler's New/EditSec branches historically
// skipped prv_update_backlight(), so if the backlight was off it stayed off
// even though we are in an (illuminated) edit mode. Force that state and
// verify the handler corrects it.
static void test_down_click_in_new_mode_updates_backlight(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeNew;

    backlight_on = false;
    backlight_timer = NULL;

    prv_down_click_handler(NULL, NULL);

    assert_true(backlight_on);
}

static void test_down_click_in_edit_sec_mode_updates_backlight(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeEditSec;

    backlight_on = false;
    backlight_timer = NULL;

    prv_down_click_handler(NULL, NULL);

    assert_true(backlight_on);
}

// #2: prv_apply_edit_increment centralizes the edit-mode increment sequence
// used by every timer-adjusting button. It must change the timer length and
// mark the length as modified so the new duration is committed when the edit
// expires (see timer_length_modified_in_edit_mode in prv_new_expire_callback).
static void test_apply_edit_increment_adds_time_and_sets_flag(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    main_data.control_mode = ControlModeEditSec;
    main_data.timer_length_modified_in_edit_mode = false;

    prv_apply_edit_increment(SELECT_BUTTON_INCREMENT_SEC_MS);

    assert_int_equal(timer_data.length_ms, SELECT_BUTTON_INCREMENT_SEC_MS);
    assert_true(main_data.timer_length_modified_in_edit_mode);
}

// Restarting a running stopwatch (long-press Select while counting up) with the
// Lap Stopwatch feature on assigns a fresh mnemonic name — but only when the
// user has NOT given the stopwatch a custom name. A stopwatch renamed via voice
// must keep that name across a restart.
static void test_restart_stopwatch_preserves_custom_name(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    s_mock_lap_stopwatch_enabled = true;

    // Running stopwatch (chrono): counting up 5s, not paused, in Counting mode
    s_mock_epoch = 1000000;
    timer_data.length_ms = 0;
    timer_data.base_length_ms = 0;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch - 5000;
    main_data.control_mode = ControlModeCounting;

    // User renames the stopwatch
    timer_set_name(timer_get_active_slot(), "My Run");
    assert_string_equal(timer_data.name, "My Run");

    // Hold Select to restart the stopwatch
    prv_select_long_click_handler(NULL, NULL);

    // The custom name survives the restart
    assert_string_equal(timer_data.name, "My Run");

    s_mock_lap_stopwatch_enabled = false;
}

// A stopwatch that was never renamed still gets a fresh mnemonic name assigned
// when it is restarted (the has-custom-name guard must not suppress this).
static void test_restart_unnamed_stopwatch_reassigns_name(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    s_mock_lap_stopwatch_enabled = true;

    s_mock_epoch = 1000000;
    timer_data.length_ms = 0;
    timer_data.base_length_ms = 0;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch - 5000;
    main_data.control_mode = ControlModeCounting;

    // Stand-in for a generated name that is NOT user-provided
    snprintf(timer_data.name, sizeof(timer_data.name), "%s", "placeholder");

    prv_select_long_click_handler(NULL, NULL);

    // A mnemonic name was reassigned, replacing the placeholder
    assert_string_not_equal(timer_data.name, "placeholder");

    s_mock_lap_stopwatch_enabled = false;
}

// With the Lap Stopwatch setting on, Select on a running *countdown* must still
// toggle play/pause — laps are a stopwatch-only behavior. Regression guard for
// the bug where a running countdown recorded a lap instead of pausing.
static void test_lap_setting_countdown_select_pauses_not_lap(void **state) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    s_mock_lap_stopwatch_enabled = true;

    // Running countdown (NOT chrono): 5-minute timer, 5s elapsed, in Counting mode
    s_mock_epoch = 1000000;
    timer_data.length_ms = 5 * 60 * 1000;
    timer_data.base_length_ms = timer_data.length_ms;
    timer_data.is_paused = false;
    timer_data.start_ms = s_mock_epoch - 5000;
    main_data.control_mode = ControlModeCounting;
    assert_false(timer_is_chrono());

    // Press Select
    prv_select_click_handler(NULL, NULL);

    // Countdown should be paused, not lapped (would still be running if lapped)
    assert_true(timer_is_paused());

    s_mock_lap_stopwatch_enabled = false;
}

// --- Voice rename feedback ---
// A successful transcription commits immediately with one short pulse; a
// failure the user did not dismiss themselves gives three pulses and leaves
// the name alone; backing out of the dictation UI is silent.

// Put a known name on the active slot and clear the vibration counters.
static void prv_setup_dictation_test(const char *initial_name) {
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    memset(&main_data, 0, sizeof(main_data));
    snprintf(timer_data.name, sizeof(timer_data.name), "%s", initial_name);
    prv_reset_vibe_counters();
}

static void test_dictation_success_vibrates_and_sets_name(void **state) {
    prv_setup_dictation_test("old name");

    char transcription[] = "pasta";
    prv_dictation_callback(NULL, DictationSessionStatusSuccess, transcription, NULL);

    assert_string_equal(timer_data.name, "pasta");
    assert_int_equal(s_short_pulse_count, 1);
    assert_int_equal(s_custom_pattern_count, 0);
}

// Failures that end without the user dismissing the UI: three short pulses.
static void prv_assert_failure_buzzes(DictationSessionStatus status) {
    prv_setup_dictation_test("old name");

    prv_dictation_callback(NULL, status, NULL, NULL);

    assert_string_equal(timer_data.name, "old name");
    assert_int_equal(s_short_pulse_count, 0);
    assert_int_equal(s_custom_pattern_count, 1);
    // Five alternating on/off segments produce three distinct buzzes
    assert_int_equal(s_last_pattern_num_segments, 5);
    for (int i = 0; i < 5; i++) {
        assert_int_equal(s_last_pattern_segments[i], 100);
    }
}

static void test_dictation_system_aborted_buzzes(void **state) {
    prv_assert_failure_buzzes(DictationSessionStatusFailureSystemAborted);
}

static void test_dictation_no_speech_buzzes(void **state) {
    prv_assert_failure_buzzes(DictationSessionStatusFailureNoSpeechDetected);
}

static void test_dictation_connectivity_error_buzzes(void **state) {
    prv_assert_failure_buzzes(DictationSessionStatusFailureConnectivityError);
}

static void test_dictation_disabled_buzzes(void **state) {
    prv_assert_failure_buzzes(DictationSessionStatusFailureDisabled);
}

static void test_dictation_internal_error_buzzes(void **state) {
    prv_assert_failure_buzzes(DictationSessionStatusFailureInternalError);
}

static void test_dictation_recognizer_error_buzzes(void **state) {
    prv_assert_failure_buzzes(DictationSessionStatusFailureRecognizerError);
}

// The user exited the dictation UI themselves: they already know nothing was
// renamed, so stay silent.
static void prv_assert_failure_silent(DictationSessionStatus status) {
    prv_setup_dictation_test("old name");

    prv_dictation_callback(NULL, status, NULL, NULL);

    assert_string_equal(timer_data.name, "old name");
    assert_int_equal(s_short_pulse_count, 0);
    assert_int_equal(s_custom_pattern_count, 0);
}

static void test_dictation_transcription_rejected_is_silent(void **state) {
    prv_assert_failure_silent(DictationSessionStatusFailureTranscriptionRejected);
}

static void test_dictation_rejected_with_error_is_silent(void **state) {
    prv_assert_failure_silent(DictationSessionStatusFailureTranscriptionRejectedWithError);
}

// The SDK confirmation screen is disabled so the result callback fires as soon
// as the transcription is ready - that is where the success pulse happens.
static void test_dictation_confirmation_disabled(void **state) {
    prv_setup_dictation_test("old name");
    s_mock_phone_connected = true;
    s_last_enable_confirmation = true;
    s_dictation_session = NULL;

    prv_start_voice_rename();

    assert_false(s_last_enable_confirmation);
    assert_true(s_last_enable_error_dialogs);
    assert_int_equal(s_dictation_start_count, 1);

    s_dictation_session = NULL;
    s_dictation_start_count = 0;
}

// --- Configurable display-refresh windows --------------------------------

// main_is_interaction_active uses the "screen on" seconds setting for its
// window, not a hardcoded 10s.
static void test_interaction_active_honors_screen_on_setting(void **state) {
    memset(&main_data, 0, sizeof(main_data));
    s_mock_epoch = 1000000;
    main_data.last_interaction_time = s_mock_epoch;

    // Default 10s window: 5s ago is active, 15s ago is not.
    s_mock_screen_on_seconds = 10;
    s_mock_epoch = 1000000 + 5000;
    assert_true(main_is_interaction_active());
    s_mock_epoch = 1000000 + 15000;
    assert_false(main_is_interaction_active());

    // Raising the setting to 20s keeps the same 15s-old interaction active.
    s_mock_screen_on_seconds = 20;
    assert_true(main_is_interaction_active());

    s_mock_screen_on_seconds = 10;
}

// main_is_last_interaction_down is a fixed window after the Down press, sized by
// the "down extra" seconds setting; 0 disables it.
static void test_down_extension_honors_down_extra_setting(void **state) {
    memset(&main_data, 0, sizeof(main_data));
    s_mock_epoch = 2000000;
    main_data.last_down_time = s_mock_epoch;

    // Default 60s window: still extended at 30s, expired at 70s.
    s_mock_down_extra_seconds = 60;
    s_mock_epoch = 2000000 + 30000;
    assert_true(main_is_last_interaction_down());
    s_mock_epoch = 2000000 + 70000;
    assert_false(main_is_last_interaction_down());

    // A short 5s window expires by 30s.
    s_mock_down_extra_seconds = 5;
    s_mock_epoch = 2000000 + 30000;
    assert_false(main_is_last_interaction_down());

    // 0 disables the extension entirely, even immediately after the press.
    s_mock_down_extra_seconds = 0;
    s_mock_epoch = 2000000;
    assert_false(main_is_last_interaction_down());

    s_mock_down_extra_seconds = 60;
}

// A Down press while running records the extension timestamp; while paused it
// does not (nothing to refresh).
static void test_down_press_records_extension_window(void **state) {
    memset(&main_data, 0, sizeof(main_data));
    s_mock_down_extra_seconds = 60;
    s_mock_epoch = 3000000;
    main_data.control_mode = ControlModeCounting;

    // Running: a Down press opens the extension window.
    timer_data.start_ms = s_mock_epoch - 30000;
    timer_data.length_ms = 5 * MSEC_IN_MIN;
    timer_data.is_paused = false;
    main_data.last_down_time = 0;
    prv_down_click_handler(NULL, NULL);
    assert_int_equal((int)main_data.last_down_time, (int)s_mock_epoch);
    assert_true(main_is_last_interaction_down());

    // Paused: a Down press must not open the window (would refresh with no change).
    timer_data.is_paused = true;
    main_data.last_down_time = 0;
    prv_down_click_handler(NULL, NULL);
    assert_int_equal((int)main_data.last_down_time, 0);
}

// --- Wakeup input guard ---------------------------------------------------
// On an alarm (wakeup) launch, a press whose press-down is within
// WAKEUP_INPUT_GUARD_MS of launch is ignored until it is released, and so is a
// press held from before launch. The handlers are called directly in the order
// the SDK would fire them: raw-down on press, single on release, long after
// BUTTON_HOLD_RESET_MS.

#define WAKEUP_TEST_LAUNCH_MS 5000000

// Launch the app with the given reason at WAKEUP_TEST_LAUNCH_MS, then put the
// active timer into a ringing alarm: a 1-min countdown that elapsed 1s ago.
static void prv_launch_with_alarm(AppLaunchReason reason) {
    prv_persist_reset(false);
    s_mock_multiple_timers = false;
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    prv_reset_app_statics();
    s_mock_launch_reason = reason;
    s_mock_epoch = WAKEUP_TEST_LAUNCH_MS;
    prv_initialize();

    timer_data.length_ms = 60000;
    timer_data.base_length_ms = 60000;
    timer_data.can_vibrate = true;
    timer_data.is_paused = false;
    timer_data.start_ms = WAKEUP_TEST_LAUNCH_MS - 61000;
    timer_data.reset_on_init = false;
    main_data.control_mode = ControlModeCounting;
    s_window_pop_count = 0;
    assert_true(timer_is_vibrating());
}

// Relaunch as a user launch so the guard does not leak into later tests.
static void prv_end_launch_test(void) {
    s_mock_launch_reason = APP_LAUNCH_SYSTEM;
    s_mock_epoch = WAKEUP_TEST_LAUNCH_MS;
    s_watch_timer = NULL;
    prv_initialize();
    s_up_held = false;
    s_up_chord_consumed = false;
}

static void prv_at(uint64_t ms_after_launch) {
    s_mock_epoch = WAKEUP_TEST_LAUNCH_MS + ms_after_launch;
}

// The alarm is untouched: still ringing, same length, same mode, app still open.
static void prv_assert_alarm_untouched(void) {
    assert_true(timer_is_vibrating());
    assert_int_equal(timer_data.length_ms, 60000);
    assert_int_equal(main_data.control_mode, ControlModeCounting);
    assert_int_equal(s_window_pop_count, 0);
}

static void test_wakeup_guard_select_press_in_window_ignored(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(100);
    prv_select_raw_click_handler(NULL, NULL);
    prv_at(200);
    prv_select_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();
    prv_end_launch_test();
}

static void test_wakeup_guard_up_press_in_window_ignored(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(100);
    prv_up_raw_down_handler(NULL, NULL);
    prv_at(200);
    prv_up_raw_up_handler(NULL, NULL);
    prv_up_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();
    prv_end_launch_test();
}

static void test_wakeup_guard_down_press_in_window_ignored(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(100);
    prv_down_raw_down_handler(NULL, NULL);
    prv_at(200);
    prv_down_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();
    prv_end_launch_test();
}

// Back has no raw subscription; its single click fires on press-down.
static void test_wakeup_guard_back_press_in_window_ignored(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(100);
    prv_back_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();
    prv_end_launch_test();
}

// A press that starts in the window stays ignored when its long click fires
// after the window closes.
static void test_wakeup_guard_long_press_started_in_window_ignored(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(200);
    prv_select_raw_click_handler(NULL, NULL);
    prv_at(200 + BUTTON_HOLD_RESET_MS);
    prv_select_long_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();

    prv_at(200);
    prv_up_raw_down_handler(NULL, NULL);
    prv_at(200 + BUTTON_HOLD_RESET_MS);
    prv_up_long_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();

    prv_at(200);
    prv_down_raw_down_handler(NULL, NULL);
    prv_at(200 + BUTTON_HOLD_RESET_MS);
    prv_down_long_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();
    prv_end_launch_test();
}

// A press held from before launch has no raw-down in this app; its release
// after the window must still be ignored.
static void test_wakeup_guard_press_held_before_launch_ignored(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(WAKEUP_INPUT_GUARD_MS + 200);
    prv_select_click_handler(NULL, NULL);
    prv_up_click_handler(NULL, NULL);
    prv_down_click_handler(NULL, NULL);
    prv_at(WAKEUP_INPUT_GUARD_MS + 700);
    prv_select_long_click_handler(NULL, NULL);
    prv_up_long_click_handler(NULL, NULL);
    prv_down_long_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();
    prv_end_launch_test();
}

static void test_wakeup_guard_down_press_after_window_snoozes(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(WAKEUP_INPUT_GUARD_MS + 100);
    prv_down_raw_down_handler(NULL, NULL);
    prv_at(WAKEUP_INPUT_GUARD_MS + 200);
    prv_down_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    assert_int_equal(timer_data.length_ms, 60000 + SNOOZE_INCREMENT_MS);
    prv_end_launch_test();
}

static void test_wakeup_guard_back_press_after_window_silences(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(WAKEUP_INPUT_GUARD_MS + 100);
    prv_back_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    assert_int_equal(s_window_pop_count, 0);
    prv_end_launch_test();
}

static void test_wakeup_guard_new_press_after_ignored_press_acts(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(100);
    prv_select_raw_click_handler(NULL, NULL);
    prv_at(200);
    prv_select_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();

    prv_at(WAKEUP_INPUT_GUARD_MS + 100);
    prv_select_raw_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    prv_at(WAKEUP_INPUT_GUARD_MS + 200);
    prv_select_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    prv_end_launch_test();
}

// The window is 400ms: a press that starts at 350ms is ignored, and a new
// press at 450ms acts.
static void test_wakeup_guard_press_late_in_window_ignored(void **state) {
    assert_int_equal(WAKEUP_INPUT_GUARD_MS, 400);
    prv_launch_with_alarm(APP_LAUNCH_WAKEUP);
    prv_at(350);
    prv_down_raw_down_handler(NULL, NULL);
    prv_at(400);
    prv_down_click_handler(NULL, NULL);
    prv_assert_alarm_untouched();

    prv_at(450);
    prv_down_raw_down_handler(NULL, NULL);
    prv_at(500);
    prv_down_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    prv_end_launch_test();
}

static void test_wakeup_guard_not_applied_on_user_launch(void **state) {
    prv_launch_with_alarm(APP_LAUNCH_SYSTEM);
    prv_at(100);
    prv_select_raw_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    prv_end_launch_test();

    prv_launch_with_alarm(APP_LAUNCH_SYSTEM);
    prv_at(100);
    prv_back_click_handler(NULL, NULL);
    assert_false(timer_is_vibrating());
    prv_end_launch_test();
}

// --- Event-loop simulation ------------------------------------------------
// These tests run real user flows: the app's click config drives the buttons,
// the fake scheduler fires the app's own AppTimers (edit expire, refresh,
// backlight linger), and the mock clock moves forward in small steps.

// Launch the app with no saved timers at at_ms.
static void prv_sim_launch(AppLaunchReason reason, uint64_t at_ms) {
    prv_fake_timers_clear();
    prv_persist_reset(false);
    s_mock_multiple_timers = false;
    memset(&timer_data, 0, sizeof(Timer));
    timer_reset();
    prv_reset_app_statics();
    s_mock_launch_reason = reason;
    s_mock_epoch = at_ms;
    prv_initialize();
    prv_click_config_provider(NULL);
}

static void prv_sim_wait(uint64_t ms) {
    prv_run_until(s_mock_epoch + ms);
}

// Press a button and hold it for hold_ms, firing handlers in SDK order: raw
// down on press; single on press when the button has no long click (Back),
// else on release; long after its delay (then no single on release).
static void prv_sim_press(ButtonId b, uint32_t hold_ms) {
    s_light_auto_until = s_mock_epoch + SYSTEM_LIGHT_MS;  // the system lights the screen
    bool has_long = s_sub_long[b] != NULL;
    if (s_sub_raw_down[b]) s_sub_raw_down[b](NULL, NULL);
    if (!has_long && s_sub_single[b]) s_sub_single[b](NULL, NULL);
    uint64_t release_ms = s_mock_epoch + hold_ms;
    bool long_fired = false;
    if (has_long && hold_ms >= s_sub_long_delay[b]) {
        prv_run_until(s_mock_epoch + s_sub_long_delay[b]);
        s_sub_long[b](NULL, NULL);
        long_fired = true;
    }
    prv_run_until(release_ms);
    if (s_sub_raw_up[b]) s_sub_raw_up[b](NULL, NULL);
    if (has_long && !long_fired && s_sub_single[b]) s_sub_single[b](NULL, NULL);
}

// The same flow as the functional helper setup_short_timer(): wait for the
// running stopwatch, pause it, hold Select to reset into EditSec, add seconds
// with Down, and wait for the edit to expire. Ends in Counting, paused.
static void prv_sim_set_short_timer(int seconds) {
    prv_sim_wait(3100);                      // New expires to a running stopwatch
    prv_sim_press(BUTTON_ID_SELECT, 100);    // pause it
    prv_sim_wait(300);
    prv_sim_press(BUTTON_ID_SELECT, 1000);   // hold: reset to 0:00, EditSec
    prv_sim_wait(300);
    for (int i = 0; i < seconds; i++) {
        prv_sim_press(BUTTON_ID_DOWN, 100);  // +1 s
        prv_sim_wait(200);
    }
    prv_sim_wait(3500);                      // edit expires (sub-minute stays paused)
}

// Step until the alarm starts; return that time (0 if it never starts).
static uint64_t prv_sim_wait_for_alarm(uint64_t timeout_ms) {
    uint64_t end = s_mock_epoch + timeout_ms;
    while (s_mock_epoch < end) {
        if (timer_is_vibrating()) return s_mock_epoch;
        prv_sim_wait(5);
    }
    return timer_is_vibrating() ? s_mock_epoch : 0;
}

// A 10 s timer, once started, shows exactly 10 s minus the time since start,
// never goes up, and rings 10 s after the start.
static void test_sim_ten_second_timer_counts_down_smoothly(void **state) {
    prv_sim_launch(APP_LAUNCH_SYSTEM, 7000000);
    prv_sim_set_short_timer(10);
    assert_int_equal(main_data.control_mode, ControlModeCounting);
    assert_true(timer_is_paused());
    assert_int_equal(timer_get_value_ms(), 10000);

    prv_sim_press(BUTTON_ID_SELECT, 100);    // start (single fires on release)
    uint64_t start = s_mock_epoch;
    assert_false(timer_is_paused());

    int64_t prev = timer_get_value_ms();
    while (!timer_is_vibrating() && s_mock_epoch < start + 11000) {
        prv_sim_wait(10);
        if (timer_is_chrono()) break;
        int64_t value = timer_get_value_ms();
        assert_true(value <= prev);
        assert_int_equal(value, 10000 - (int64_t)(s_mock_epoch - start));
        prev = value;
    }
    uint64_t alarm = prv_sim_wait_for_alarm(1000);
    assert_true(alarm >= start + 10000);
    assert_true(alarm <= start + 10000 + 20);
}

// Sweep the timing of the fast "set it right after launch" flow: from New,
// hold Select into EditSec, press Down 10 times, and start it if it paused.
// Whatever the timing: no alarm may start while the user is still entering
// the time, the result must not be longer than the 10 s entered, a running
// countdown must never count up, and the shown seconds must never jump by
// more than 1 between 10 ms samples.
static void test_sim_countdown_never_counts_up_sweep(void **state) {
    for (int phase = 0; phase < 1000; phase += 125) {
        for (int delay = 200; delay <= 2600; delay += 400) {
            prv_sim_launch(APP_LAUNCH_SYSTEM, 8000000 + phase);
            prv_sim_wait(delay);
            prv_sim_press(BUTTON_ID_SELECT, 1000);   // hold: New -> EditSec
            prv_sim_wait(150);
            bool alarm_while_editing = false;
            for (int i = 0; i < 10; i++) {
                prv_sim_press(BUTTON_ID_DOWN, 80);
                for (int w = 0; w < 15; w++) {
                    prv_sim_wait(10);
                    if (timer_is_vibrating()) alarm_while_editing = true;
                }
            }
            prv_sim_wait(3500);                      // edit expires
            if (timer_is_paused()) {
                prv_sim_press(BUTTON_ID_SELECT, 100);
            }
            int64_t first = timer_get_value_ms();
            bool countdown = !timer_is_chrono();
            printf("  phase=%3d delay=%4d -> %s %lld ms%s\n", phase, delay,
                   countdown ? "countdown" : "stopwatch", (long long)first,
                   alarm_while_editing ? " (ALARM while editing)" : "");
            assert_false(alarm_while_editing);
            assert_true(countdown);
            assert_true(first <= 10000);

            int64_t prev = first;
            uint16_t hr, min, prev_sec;
            timer_get_time_parts(&hr, &min, &prev_sec);
            uint64_t end = s_mock_epoch + 12000;
            while (s_mock_epoch < end && countdown && !timer_is_chrono()) {
                prv_sim_wait(10);
                if (timer_is_chrono()) break;
                int64_t value = timer_get_value_ms();
                assert_true(value <= prev);
                uint16_t sec;
                timer_get_time_parts(&hr, &min, &sec);
                assert_true(prev_sec - sec <= 1);
                prev = value;
                prev_sec = sec;
            }
        }
    }
}

// Starting a sub-minute timer with Select right after its edit expires must
// not turn the light off: the press lights the screen, and the app must not
// cut that short.
static void test_sim_light_stays_on_after_select_starts_timer(void **state) {
    prv_sim_launch(APP_LAUNCH_SYSTEM, 9000000);
    prv_sim_set_short_timer(10);
    uint64_t press = s_mock_epoch;
    prv_sim_press(BUTTON_ID_SELECT, 100);    // start the countdown
    prv_run_until(press + 1500);
    assert_true(prv_light_is_on());
}

// Silencing an alarm with Select must not turn the light off at once.
static void test_sim_light_stays_on_after_select_silences_alarm(void **state) {
    prv_sim_launch(APP_LAUNCH_SYSTEM, 9500000);
    prv_sim_set_short_timer(5);
    prv_sim_press(BUTTON_ID_SELECT, 100);    // start
    assert_true(prv_sim_wait_for_alarm(6000) != 0);
    prv_sim_wait(2000);
    assert_true(prv_light_is_on());          // the alarm keeps the light on
    uint64_t press = s_mock_epoch;
    prv_sim_press(BUTTON_ID_SELECT, 100);    // silence
    assert_false(timer_is_vibrating());
    prv_run_until(press + 1500);
    assert_true(prv_light_is_on());
}

// On a wakeup launch the app can open before the countdown ends (the wakeup
// time is rounded down to whole seconds), so the alarm starts after launch.
// A press 100 ms after the alarm appears must be ignored, however early the
// app opened.
static void test_sim_guard_covers_alarm_start_after_early_wakeup(void **state) {
    const int leads[] = {0, 200, 400, 600, 800, 950};
    int failures = 0;
    for (size_t i = 0; i < ARRAY_LENGTH(leads); i++) {
        uint64_t launch = 10000000 + i * 100000;
        prv_sim_launch(APP_LAUNCH_WAKEUP, launch);
        // The saved 10 s countdown has leads[i] ms left at launch
        timer_data.length_ms = 10000;
        timer_data.base_length_ms = 10000;
        timer_data.can_vibrate = true;
        timer_data.is_paused = false;
        timer_data.start_ms = launch - (10000 - leads[i]);
        main_data.control_mode = ControlModeCounting;
        app_timer_cancel(main_data.app_timer);
        prv_app_timer_callback(NULL);

        uint64_t alarm = prv_sim_wait_for_alarm(2000);
        assert_true(alarm != 0);
        prv_run_until(alarm + 100);
        prv_sim_press(BUTTON_ID_DOWN, 100);
        bool ignored = timer_is_vibrating();
        printf("  wakeup %3d ms before the end: alarm at +%llu ms, press at alarm+100 %s\n",
               leads[i], (unsigned long long)(alarm - launch),
               ignored ? "ignored" : "ACTED");
        if (!ignored) failures++;
    }
    assert_int_equal(failures, 0);
}

// Case A: holding Select into EditSec while the New-mode timer still runs as a
// stopwatch, then adding less time than the stopwatch shows, leaves a
// stopwatch. No alarm may start on it, so the next Down adds 1 s (it must not
// be taken as a snooze).
static void test_sim_no_alarm_on_stopwatch_after_edit_increment(void **state) {
    prv_sim_launch(APP_LAUNCH_SYSTEM, 12000000);
    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_SELECT, 1000);   // hold: New -> EditSec (still running)
    assert_int_equal(main_data.control_mode, ControlModeEditSec);
    prv_sim_wait(150);
    prv_sim_press(BUTTON_ID_DOWN, 80);       // +1 s: still a stopwatch (~1.2 s)
    assert_true(timer_is_chrono());
    prv_sim_wait(500);
    assert_false(timer_is_vibrating());
    prv_sim_press(BUTTON_ID_DOWN, 80);       // +1 s, not a snooze
    assert_int_equal(main_data.control_mode, ControlModeEditSec);
    assert_true(timer_data.length_ms < SNOOZE_INCREMENT_MS);
}

////////////////////////////////////////////////////////////////////////////////////////////////////
// Alarm takeover and held alarms (openspec: list-alarm-takeover)
//
// These tests save timers in several slots, launch the app from that saved
// state, and let the fake scheduler run the app's own timers. An exit runs
// prv_terminate(), and a relaunch reads the saved state back, as on the watch.

#define MIN_MS 60000

// Start a test at at_ms (use a multiple of 1000) with an empty, enabled
// persist store and no timers.
static void prv_sim_begin(uint64_t at_ms) {
    prv_persist_reset(true);
    prv_wakeups_reset();
    prv_log_clear();
    prv_reset_vibe_counters();
    s_mock_epoch = at_ms;
    s_mock_multiple_timers = false;
    s_mock_launch_reason = APP_LAUNCH_SYSTEM;
    memset(timer_slots, 0, sizeof(timer_slots));
    timer_count = 0;
    timer_set_active_slot(0);
}

// Turn the persist store off again so later tests see a fresh install
static int prv_sim_teardown(void **state) {
    prv_persist_reset(false);
    s_mock_multiple_timers = false;
    s_mock_list_on_top = false;
    s_mock_launch_reason = APP_LAUNCH_SYSTEM;
    return 0;
}

// A running countdown in a slot with remaining_ms left now (negative: it ended
// that long ago)
static void prv_slot_countdown(uint8_t slot, int64_t length_ms, int64_t remaining_ms) {
    timer_slots[slot] = (Timer){
        .length_ms = length_ms,
        .base_length_ms = length_ms,
        .start_ms = (int64_t)s_mock_epoch - (length_ms - remaining_ms),
        .can_vibrate = true,
        .is_paused = false,
    };
    snprintf(timer_slots[slot].name, sizeof(timer_slots[slot].name), "timer %d", slot);
    if (slot >= timer_count) timer_count = slot + 1;
}

// A running stopwatch in a slot
static void prv_slot_chrono(uint8_t slot, int64_t elapsed_ms) {
    timer_slots[slot] = (Timer){
        .start_ms = (int64_t)s_mock_epoch - elapsed_ms,
        .is_paused = false,
    };
    snprintf(timer_slots[slot].name, sizeof(timer_slots[slot].name), "timer %d", slot);
    if (slot >= timer_count) timer_count = slot + 1;
}

// Save the slots and the pending-alarm mask, as an earlier exit would
static void prv_sim_save(uint32_t pending_mask) {
    timer_persist_store();
    persist_write_int(PERSIST_PENDING_MASK_KEY, (int32_t)pending_mask);
}

// Launch the app from the saved state at the current mock time
static void prv_sim_launch_saved(AppLaunchReason reason, int32_t cookie) {
    prv_fake_timers_clear();
    prv_reset_app_statics();
    s_mock_launch_reason = reason;
    s_mock_launch_cookie = cookie;
    prv_initialize();
    prv_click_config_provider(NULL);
}

// Close the app (the system exit: no button handler runs)
static void prv_sim_exit(void) {
    prv_terminate();
}

// Launch the app with the recorded wakeup `index`, at that wakeup's time
static void prv_sim_fire_wakeup(int index) {
    assert_true(index < s_wakeup_count);
    FakeWakeup wakeup = s_wakeups[index];
    assert_true(wakeup.result >= 0);
    s_mock_epoch = (uint64_t)wakeup.time * 1000;
    prv_sim_launch_saved(APP_LAUNCH_WAKEUP, wakeup.cookie);
}

static uint32_t prv_saved_pending_mask(void) {
    return (uint32_t)persist_read_int(PERSIST_PENDING_MASK_KEY);
}

// The guard window started at at_ms and every button is blocked
static void prv_assert_guard_started_at(uint64_t at_ms) {
    assert_int_equal(s_blocked_buttons, 0xFF);
    assert_int_equal(s_wakeup_launch_ms, (uint32_t)at_ms);
}

// The main window shows `slot` in Counting mode with its alarm vibrating
static void prv_assert_alarm_showing(uint8_t slot) {
    assert_int_equal(timer_get_active_slot(), slot);
    assert_int_equal(main_data.control_mode, ControlModeCounting);
    assert_true(timer_is_vibrating());
}

// Check that three wakeups were recorded for `cookie`: a primary at `primary`
// and backups 2 min and 4 min later
static void prv_assert_wakeups(time_t primary, int32_t cookie) {
    assert_int_equal(s_wakeup_count, 3);
    for (int i = 0; i < 3; i++) {
        assert_int_equal(s_wakeups[i].time, primary + i * BACKUP_WAKEUP_DELAY_S);
        assert_int_equal(s_wakeups[i].cookie, cookie);
    }
}

// 1.3: main_show_alarm() on a slot that is already elapsed and vibrating
static void test_show_alarm_on_vibrating_slot(void **state) {
    uint64_t t0 = 20000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, MIN_MS, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    assert_true(prv_sim_wait_for_alarm(3000) != 0);
    prv_sim_wait(1500);
    assert_true(timer_data.elapsed);
    assert_true(timer_is_vibrating());
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);

    // Leftover state from an edit: main_show_alarm() must clear all of it
    main_data.control_mode = ControlModeNew;
    main_data.is_reverse_direction = true;
    prv_reset_new_expire_timer();
    main_data.quit_timer = app_timer_register(QUIT_DELAY_MS, prv_quit_callback, NULL);

    uint64_t shown = s_mock_epoch;
    main_show_alarm();

    prv_assert_alarm_showing(0);
    assert_false(main_data.is_reverse_direction);
    assert_null(main_data.new_expire_timer);
    assert_null(main_data.quit_timer);
    prv_assert_guard_started_at(shown);
    // The alarm was already running: it is not started a second time
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
}

// Launch with the Timer List on top, a 5 min countdown in slot 0, and a 30 s
// countdown in slot 1 that ends 5 s after launch. At 6 s, leave the list as a
// takeover of slot 1 does. Returns the time main_show_alarm() was called.
static uint64_t prv_sim_takeover_from_list(uint64_t t0) {
    prv_sim_begin(t0);
    s_mock_multiple_timers = true;
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, 5000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    assert_int_equal(s_timer_list_push_count, 1);

    prv_sim_wait(6000);
    // The main window has never checked slot 1
    assert_false(timer_slots[1].elapsed);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 0);
    assert_int_equal(s_custom_pattern_count, 0);

    s_mock_list_on_top = false;
    timer_set_active_slot(1);
    main_show_alarm();
    return s_mock_epoch;
}

// 1.3a: main_show_alarm() on a non-zero slot that the main window never checked
static void test_show_alarm_on_unchecked_slot(void **state) {
    prv_sim_takeover_from_list(21000000);

    prv_assert_alarm_showing(1);
    assert_int_equal(s_custom_pattern_count, 1);
    assert_true(backlight_on);
    assert_true(prv_light_is_on());
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
    // The refresh is scheduled again for the new slot
    assert_non_null(main_data.app_timer);
    assert_true(((FakeTimer *)main_data.app_timer)->active);
    assert_true(((FakeTimer *)main_data.app_timer)->due_ms <= s_mock_epoch + 1005);
}

// 1.4: after main_show_alarm(), presses in the guard window and a release with
// no press-down are ignored; a Down press after the window snoozes
static void test_show_alarm_guards_presses(void **state) {
    uint64_t shown = prv_sim_takeover_from_list(22000000);
    prv_assert_guard_started_at(shown);

    // Press-down at +100 ms
    prv_run_until(shown + 100);
    prv_sim_press(BUTTON_ID_DOWN, 50);
    prv_assert_alarm_showing(1);
    assert_int_equal(timer_data.length_ms, 30000);

    // Back at +200 ms
    prv_run_until(shown + 200);
    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_alarm_showing(1);
    assert_int_equal(s_window_pop_count, 0);

    // A release with no press-down (the button was held when the alarm showed)
    prv_run_until(shown + 500);
    s_sub_single[BUTTON_ID_SELECT](NULL, NULL);
    s_sub_single[BUTTON_ID_UP](NULL, NULL);
    s_sub_long[BUTTON_ID_SELECT](NULL, NULL);
    prv_assert_alarm_showing(1);
    assert_false(timer_is_paused());

    // Down at +600 ms snoozes
    prv_run_until(shown + 600);
    prv_sim_press(BUTTON_ID_DOWN, 100);
    assert_false(timer_is_vibrating());
    assert_int_equal(timer_data.length_ms, 30000 + SNOOZE_INCREMENT_MS);
    assert_int_equal(timer_get_active_slot(), 1);
}

// 1.4a: not busy: slot 1 takes over at its end time; slot 0 keeps running and
// is watched, so it takes over at its own end
static void test_sim_takeover_when_not_busy(void **state) {
    uint64_t t0 = 23000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 60000);
    prv_slot_countdown(1, 30000, 30000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    prv_run_until(t0 + 30000 - 10);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_false(timer_is_vibrating());
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);

    prv_run_until(t0 + 30000 + 20);
    prv_assert_alarm_showing(1);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=1"), 1);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
    assert_true(s_custom_pattern_count >= 1);
    assert_int_equal(s_blocked_buttons, 0xFF);
    assert_true(s_wakeup_launch_ms >= (uint32_t)(t0 + 30000));
    assert_true(backlight_on);

    // The timer that was on screen keeps running
    assert_false(timer_slots[0].is_paused);
    assert_int_equal(timer_slots[0].length_ms, 5 * MIN_MS);
    assert_true(timer_watch_mask() & 1);

    // Silence slot 1 after the guard window; slot 0 then takes over at its end
    prv_run_until(t0 + 31000);
    prv_sim_press(BUTTON_ID_BACK, 50);
    assert_false(timer_is_vibrating());
    assert_int_equal(timer_get_active_slot(), 1);
    assert_int_equal(s_window_pop_count, 0);

    prv_run_until(t0 + 60000 - 10);
    assert_int_equal(timer_get_active_slot(), 1);
    prv_run_until(t0 + 60000 + 20);
    prv_assert_alarm_showing(0);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=0"), 1);
}

// Slot 0 (60 s timer) alarms 5 s after launch, and slot 1 (30 s timer) ends
// 15 s after launch, behind that alarm. Runs to just after slot 1 ends and
// checks that it is held.
static void prv_sim_hold_behind_alarm(uint64_t t0) {
    prv_sim_begin(t0);
    prv_slot_countdown(0, MIN_MS, 5000);
    prv_slot_countdown(1, 30000, 15000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    prv_run_until(t0 + 5000 + 20);
    prv_assert_alarm_showing(0);
    assert_int_equal(prv_log_count("alarm_held"), 0);

    prv_run_until(t0 + 15000 + 20);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
    prv_assert_alarm_showing(0);
    assert_int_equal(timer_slots[1].length_ms, 30000);
    assert_false(timer_slots[1].elapsed);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    // There is no re-check timer while an alarm is held
    assert_null(s_watch_timer);
}

// The held slot 1 took over: it is on screen, vibrating, unchanged, and shows
// the real time since it ended (it ended 15 s after t0)
static void prv_assert_held_took_over(uint64_t t0) {
    prv_assert_alarm_showing(1);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=1"), 1);
    assert_int_equal(timer_slots[1].length_ms, 30000);
    assert_int_equal(timer_get_value_ms(), (int64_t)(s_mock_epoch - (t0 + 15000)));
}

// 1.4b: held behind an alarm: logged once, nothing changes
static void test_sim_hold_logged_once(void **state) {
    uint64_t t0 = 24000000;
    prv_sim_hold_behind_alarm(t0);

    // More checks while busy do not log the hold again
    prv_watch_arm();
    prv_watch_arm();
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
    assert_int_equal(prv_log_count("alarm_held"), 1);
    assert_null(s_watch_timer);
    prv_assert_alarm_showing(0);
}

// 1.4b: Select silences slot 0, and slot 1 takes over at once
static void test_sim_held_takes_over_on_select(void **state) {
    uint64_t t0 = 25000000;
    prv_sim_hold_behind_alarm(t0);
    prv_sim_press(BUTTON_ID_SELECT, 100);
    prv_assert_held_took_over(t0);
    assert_true(timer_slots[0].is_paused);
}

// 1.4b: Back silences slot 0, and slot 1 takes over at once
static void test_sim_held_takes_over_on_back(void **state) {
    uint64_t t0 = 26000000;
    prv_sim_hold_behind_alarm(t0);
    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_held_took_over(t0);
    assert_int_equal(s_window_pop_count, 0);
    assert_false(timer_slots[0].can_vibrate);
}

// 1.4b: Down snoozes slot 0, and slot 1 takes over at once
static void test_sim_held_takes_over_on_down(void **state) {
    uint64_t t0 = 27000000;
    prv_sim_hold_behind_alarm(t0);
    prv_sim_press(BUTTON_ID_DOWN, 100);
    prv_assert_held_took_over(t0);
    assert_int_equal(timer_slots[0].length_ms, MIN_MS + SNOOZE_INCREMENT_MS);
    // The snoozed timer is watched again
    assert_true(timer_watch_mask() & 1);
}

// 1.4b: the 30 s vibration of slot 0 ends on its own, and slot 1 takes over
static void test_sim_held_takes_over_when_vibration_ends(void **state) {
    uint64_t t0 = 28000000;
    prv_sim_hold_behind_alarm(t0);
    prv_run_until(t0 + 5000 + 29000);
    prv_assert_alarm_showing(0);
    prv_run_until(t0 + 5000 + 30000 + 1100);
    prv_assert_held_took_over(t0);
    assert_int_equal(timer_slots[0].auto_snooze_count, 1);
}

// 1.4b2: Up on the alarm silences it and opens the edit screen; the held alarm
// waits until that edit expires
static void test_sim_up_on_alarm_keeps_held_alarm_waiting(void **state) {
    uint64_t t0 = 29000000;
    prv_sim_hold_behind_alarm(t0);

    prv_sim_press(BUTTON_ID_UP, 100);
    assert_int_equal(main_data.control_mode, ControlModeNew);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_false(timer_is_vibrating());
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);

    // A press in the edit screen does not let it take over either
    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_DOWN, 100);
    assert_int_equal(main_data.control_mode, ControlModeNew);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);

    // The edit expires 3 s after the last press
    prv_sim_wait(2900);
    assert_int_equal(timer_get_active_slot(), 0);
    prv_sim_wait(200);
    prv_assert_held_took_over(t0);
}

// How to put slot 0 into an edit mode from Counting
typedef enum { EditViaNew, EditViaEditSec, EditViaEditRepeat } EditVia;

// 1.4c: slot 1 ends while slot 0 is in an edit mode: held; when the edit
// expires to Counting, slot 1 takes over
static void prv_sim_hold_behind_edit(EditVia via, uint64_t t0) {
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, 4000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    ControlMode edit_mode = ControlModeNew;
    prv_sim_wait(500);
    switch (via) {
        case EditViaNew:
            prv_sim_wait(1500);
            prv_sim_press(BUTTON_ID_UP, 100);          // Counting -> New
            break;
        case EditViaEditSec:
            prv_sim_press(BUTTON_ID_UP, 100);          // Counting -> New
            prv_sim_wait(200);
            prv_sim_press(BUTTON_ID_SELECT, 1000);     // hold: New -> EditSec
            edit_mode = ControlModeEditSec;
            break;
        case EditViaEditRepeat:
            prv_sim_press(BUTTON_ID_UP, 1000);         // hold: Counting -> EditRepeat
            edit_mode = ControlModeEditRepeat;
            break;
    }
    assert_int_equal(main_data.control_mode, edit_mode);
    assert_true(s_mock_epoch < t0 + 4000);

    // Slot 1 ends while the edit screen shows
    prv_run_until(t0 + 4000 + 20);
    assert_int_equal(main_data.control_mode, edit_mode);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    assert_false(timer_slots[1].elapsed);
    assert_null(s_watch_timer);

    // The edit expires to Counting, and slot 1 takes over
    prv_sim_wait(3000);
    prv_assert_alarm_showing(1);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=1"), 1);
    assert_int_equal(timer_slots[1].length_ms, 30000);
}

static void test_sim_held_behind_new_mode(void **state) {
    prv_sim_hold_behind_edit(EditViaNew, 30000000);
}

static void test_sim_held_behind_edit_sec(void **state) {
    prv_sim_hold_behind_edit(EditViaEditSec, 31000000);
}

static void test_sim_held_behind_edit_repeat(void **state) {
    prv_sim_hold_behind_edit(EditViaEditRepeat, 32000000);
}

// 1.4d: two held alarms open in the order they ended
static void test_sim_two_held_open_in_order(void **state) {
    uint64_t t0 = 33000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, MIN_MS, 5000);
    prv_slot_countdown(1, 30000, 10000);
    prv_slot_countdown(2, 30000, 8000);    // ends first
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    prv_run_until(t0 + 12000);
    prv_assert_alarm_showing(0);
    assert_int_equal(prv_log_count("alarm_held,slot=2"), 1);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);

    // Silence slot 0: the first to end (slot 2) opens. Slot 1 does not take
    // over inside that takeover; it is held behind the new alarm.
    prv_sim_press(BUTTON_ID_SELECT, 100);
    prv_assert_alarm_showing(2);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=2"), 1);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=1"), 0);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
    assert_false(timer_slots[1].elapsed);

    // Silence slot 2 after the guard window: slot 1 opens
    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_alarm_showing(1);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=1"), 1);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
}

// 1.4e: an alarm held for 45 s vibrates when it is shown and shows about 0:45
static void test_sim_held_45s_vibrates_for_full_time(void **state) {
    uint64_t t0 = 34000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    // Stay in the edit screen for 45 s after slot 1 ends: a press every 2 s
    prv_sim_wait(500);
    prv_sim_press(BUTTON_ID_UP, 100);
    while (s_mock_epoch < t0 + 2000 + 42000) {
        prv_sim_wait(1900);
        prv_sim_press(BUTTON_ID_DOWN, 100);
        assert_int_equal(main_data.control_mode, ControlModeNew);
    }
    assert_int_equal(timer_get_active_slot(), 0);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
    assert_int_equal(s_custom_pattern_count, 0);

    // The edit expires: the held alarm is shown
    prv_sim_wait(3100);
    uint64_t shown = s_mock_epoch;
    prv_assert_alarm_showing(1);
    assert_true(s_custom_pattern_count >= 1);
    assert_int_equal(timer_slots[1].auto_snooze_count, 0);
    assert_int_equal(timer_slots[1].length_ms, 30000);
    uint16_t hr, min, sec;
    timer_get_time_parts(&hr, &min, &sec);
    assert_int_equal(min, 0);
    assert_true(sec >= 45 && sec <= 49);

    // It vibrates each second for its full time, counted from when it was
    // shown (the edit expired up to 100 ms before `shown`)
    int vibes = s_custom_pattern_count;
    prv_run_until(shown + 28500);
    assert_true(timer_is_vibrating());
    assert_int_equal(timer_slots[1].auto_snooze_count, 0);
    assert_true(s_custom_pattern_count - vibes >= 27);
    prv_run_until(shown + 31500);
    assert_int_equal(timer_slots[1].auto_snooze_count, 1);
}

// 1.4f: a countdown that was overdue at launch (not a saved held alarm) never
// takes over
static void test_sim_overdue_at_launch_never_takes_over(void **state) {
    uint64_t t0 = 35000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, -10000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    prv_sim_wait(60000);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    assert_int_equal(prv_log_count("alarm_held"), 0);
    assert_false(timer_slots[1].elapsed);
    assert_int_equal(s_custom_pattern_count, 0);
}

// 1.4f: with the Timer List on top, the main watch does nothing, and slot 0's
// alarm does not start behind the list. It starts when the list hands over.
static void test_sim_no_alarm_behind_the_list(void **state) {
    uint64_t t0 = 36000000;
    prv_sim_begin(t0);
    s_mock_multiple_timers = true;
    prv_slot_countdown(0, 30000, 5000);
    prv_slot_countdown(1, 5 * MIN_MS, 5 * MIN_MS);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    assert_int_equal(s_timer_list_push_count, 1);
    assert_null(s_watch_timer);

    // Slot 0 ends behind the list
    prv_sim_wait(8000);
    assert_int_equal(s_custom_pattern_count, 0);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 0);
    assert_false(timer_slots[0].elapsed);
    assert_false(backlight_on);
    assert_null(s_watch_timer);
    assert_int_equal(s_blocked_buttons, 0);

    // The list hands over: the alarm starts
    s_mock_list_on_top = false;
    timer_set_active_slot(0);
    main_show_alarm();
    prv_assert_alarm_showing(0);
    assert_int_equal(s_custom_pattern_count, 1);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
}

// 2.5c: a list exit that does not take over (Select on a timer) re-runs the
// alarm check and arms the watch
static void test_sim_list_exit_reruns_the_check(void **state) {
    uint64_t t0 = 37000000;
    prv_sim_begin(t0);
    s_mock_multiple_timers = true;
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, 10000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(2000);
    assert_null(s_watch_timer);

    s_mock_list_on_top = false;
    main_watch_arm();
    assert_non_null(s_watch_timer);
    assert_int_equal(((FakeTimer *)s_watch_timer)->due_ms, t0 + 10000);

    prv_run_until(t0 + 10000 + 20);
    prv_assert_alarm_showing(1);
}

// --- D12: one wakeup for the next alarm event, plus two backups ---

// Slot 0 is a 5 min timer with slot0_remaining_ms left, shown in New mode
// (busy). The other slots are 30 s timers that end 1.5 s (slot 2, if used)
// and 2 s (slot 1) after launch, so they are held. The app exits 2.5 s after
// launch. Returns the exit time in whole seconds.
static time_t prv_sim_exit_with_held(uint64_t t0, int64_t slot0_remaining_ms, bool two_held) {
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, slot0_remaining_ms);
    prv_slot_countdown(1, 30000, 2000);
    if (two_held) {
        prv_slot_countdown(2, 30000, 1500);
    }
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(500);
    prv_sim_press(BUTTON_ID_UP, 100);
    assert_int_equal(main_data.control_mode, ControlModeNew);

    prv_run_until(t0 + 2500);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    prv_sim_exit();
    return (time_t)((t0 + 2500) / 1000);
}

// 1.5f: one held alarm
static void test_exit_one_held(void **state) {
    time_t now_s = prv_sim_exit_with_held(40000000, 5 * MIN_MS, false);
    prv_assert_wakeups(now_s + HELD_WAKEUP_DELAY_S, 1);
    assert_int_equal(s_wakeups[0].time, now_s + 10);
    assert_int_equal(s_wakeups[1].time, now_s + 130);
    assert_int_equal(s_wakeups[2].time, now_s + 250);
    assert_int_equal(prv_saved_pending_mask(), 0x3);
}

// 1.5f: two held alarms: the cookie is the first to end
static void test_exit_two_held(void **state) {
    time_t now_s = prv_sim_exit_with_held(41000000, 5 * MIN_MS, true);
    prv_assert_wakeups(now_s + HELD_WAKEUP_DELAY_S, 2);
    assert_int_equal(prv_saved_pending_mask(), 0x7);
}

// 1.5f: a held alarm and the active countdown ending 30 s after the exit: the
// primary is the held alarm, and the countdown still rings at its end
static void test_exit_held_and_active_ending_later(void **state) {
    uint64_t t0 = 42000000;
    time_t now_s = prv_sim_exit_with_held(t0, 32500, false);
    prv_assert_wakeups(now_s + HELD_WAKEUP_DELAY_S, 1);
    assert_int_equal(prv_saved_pending_mask(), 0x3);

    prv_sim_fire_wakeup(0);
    prv_assert_alarm_showing(1);
    assert_true(timer_watch_mask() & 1);
    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_BACK, 50);
    assert_false(timer_is_vibrating());

    // Slot 0 rings at its end
    prv_run_until(t0 + 32500 - 10);
    assert_int_equal(timer_get_active_slot(), 1);
    prv_run_until(t0 + 32500 + 20);
    prv_assert_alarm_showing(0);
}

// 1.5f: a held alarm and the active countdown ending 5 s after the exit
// (before the held time): the primary is the countdown; the held bit is saved
// and both alarms ring in turn
static void test_exit_held_and_active_ending_sooner(void **state) {
    uint64_t t0 = 43000000;
    time_t now_s = prv_sim_exit_with_held(t0, 7500, false);
    prv_assert_wakeups(now_s + 5, 0);
    assert_int_equal(prv_saved_pending_mask(), 0x3);

    prv_sim_fire_wakeup(0);
    prv_run_until(t0 + 7500 + 20);
    assert_true(timer_is_vibrating());
    uint8_t first = timer_get_active_slot();

    // Silence the first alarm after the guard window: the other one takes over
    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_BACK, 50);
    assert_true(timer_is_vibrating());
    assert_int_equal(timer_get_active_slot(), 1 - first);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 2);
}

// One 30 s countdown with 20.5 s left; the app exits 0.5 s after launch.
// Returns the countdown's end in whole seconds.
static time_t prv_sim_exit_with_active_only(uint64_t t0) {
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 20500);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(500);
    return (time_t)(t0 / 1000 + 20);
}

// 1.5f: the active countdown only
static void test_exit_active_only(void **state) {
    time_t end_s = prv_sim_exit_with_active_only(44000000);
    prv_sim_exit();
    prv_assert_wakeups(end_s, 0);
    assert_true(s_wakeups[0].result >= 0);
    assert_true(s_wakeups[1].result >= 0);
    assert_true(s_wakeups[2].result >= 0);
    assert_int_equal(prv_saved_pending_mask(), 0x1);
}

// 1.5f: the active countdown ends in 10 min and a non-active one in 3 min: the
// primary is the non-active one, and both are saved
static void test_exit_non_active_ends_first(void **state) {
    uint64_t t0 = 45000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 10 * MIN_MS, 10 * MIN_MS);
    prv_slot_countdown(1, 3 * MIN_MS, 3 * MIN_MS);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(1000);
    prv_sim_exit();

    prv_assert_wakeups((time_t)(t0 / 1000 + 180), 1);
    assert_int_equal(prv_saved_pending_mask(), 0x3);

    // That wakeup opens slot 1, and slot 0 is watched
    prv_sim_fire_wakeup(0);
    prv_sim_wait(100);
    prv_assert_alarm_showing(1);
    assert_true(timer_watch_mask() & 1);
    assert_non_null(s_watch_timer);
    assert_int_equal(((FakeTimer *)s_watch_timer)->due_ms, t0 + 10 * MIN_MS);
}

// 1.5f: two non-active countdowns 20 s apart: the primary is the first; after
// that launch the second is watched and takes over when the user is free
static void test_exit_two_non_active(void **state) {
    uint64_t t0 = 46000000;
    prv_sim_begin(t0);
    prv_slot_chrono(0, 5000);
    prv_slot_countdown(1, MIN_MS, 60000);
    prv_slot_countdown(2, 2 * MIN_MS, 80000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(1000);
    prv_sim_exit();

    prv_assert_wakeups((time_t)(t0 / 1000 + 60), 1);
    assert_int_equal(prv_saved_pending_mask(), 0x6);

    prv_sim_fire_wakeup(0);
    prv_sim_wait(100);
    prv_assert_alarm_showing(1);

    // Slot 2 ends while slot 1 still vibrates: it is held
    prv_run_until(t0 + 80000 + 20);
    prv_assert_alarm_showing(1);
    assert_int_equal(prv_log_count("alarm_held,slot=2"), 1);

    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_alarm_showing(2);
}

// 1.5f: another app's wakeup within 1 minute of the primary: the primary gets
// E_RANGE, and both backups are scheduled
static void test_exit_primary_blocked_by_other_app(void **state) {
    time_t end_s = prv_sim_exit_with_active_only(47000000);
    prv_add_other_app_wakeup(end_s + 30);
    prv_sim_exit();

    prv_assert_wakeups(end_s, 0);
    assert_int_equal(s_wakeups[0].result, E_RANGE);
    assert_true(s_wakeups[1].result >= 0);
    assert_true(s_wakeups[2].result >= 0);
    assert_int_equal(prv_saved_pending_mask(), 0x1);
}

// 1.5f: other apps' wakeups near the primary and the first backup: both get
// E_RANGE, and the second backup is scheduled
static void test_exit_primary_and_backup_blocked(void **state) {
    time_t end_s = prv_sim_exit_with_active_only(48000000);
    prv_add_other_app_wakeup(end_s + 30);
    prv_add_other_app_wakeup(end_s + 100);
    prv_sim_exit();

    prv_assert_wakeups(end_s, 0);
    assert_int_equal(s_wakeups[0].result, E_RANGE);
    assert_int_equal(s_wakeups[1].result, E_RANGE);
    assert_true(s_wakeups[2].result >= 0);
}

// 1.5f: no pending alarm: no wakeup, and the saved mask is 0
static void test_exit_no_pending_alarm(void **state) {
    uint64_t t0 = 49000000;
    prv_sim_begin(t0);
    prv_slot_chrono(0, 5000);
    prv_slot_countdown(1, MIN_MS, 30000);
    timer_slots[1].is_paused = true;
    timer_slots[1].start_ms = 30000;
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(1000);
    prv_sim_exit();

    assert_int_equal(s_wakeup_count, 0);
    assert_int_equal(prv_saved_pending_mask(), 0);
}

// 1.5g: the primary wakeup launch cancels the backups
static void test_primary_wakeup_cancels_backups(void **state) {
    uint64_t t0 = 50000000;
    prv_sim_exit_with_active_only(t0);
    prv_sim_exit();
    assert_int_equal(s_wakeup_count, 3);
    int cancels = s_wakeup_cancel_all_count;

    prv_sim_fire_wakeup(0);
    assert_int_equal(s_wakeup_cancel_all_count, cancels + 1);
    assert_int_equal(s_wakeup_count, 0);   // no backup is left to launch the app

    prv_run_until(t0 + 20500 + 20);
    prv_assert_alarm_showing(0);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
}

// A backup wakeup launches the app late: the alarm vibrates for its full time
// and shows the real time since the end
static void prv_sim_backup_launch(uint64_t t0, int backup, int expected_s) {
    time_t end_s = prv_sim_exit_with_active_only(t0);
    prv_add_other_app_wakeup(end_s + 30);
    if (backup == 2) {
        prv_add_other_app_wakeup(end_s + 100);
    }
    prv_sim_exit();

    prv_sim_fire_wakeup(backup);
    uint64_t launch = s_mock_epoch;
    prv_assert_alarm_showing(0);
    assert_true(s_custom_pattern_count >= 1);
    assert_int_equal(timer_data.auto_snooze_count, 0);
    // The real time since the end. The wakeup time is in whole seconds, so it
    // is up to 1 s less than the backup delay.
    int64_t overtime_s = timer_get_value_ms() / 1000;
    assert_true(overtime_s >= expected_s - 1 && overtime_s <= expected_s);

    // One vibration each second, for 30 s from the launch
    int vibes = s_custom_pattern_count;
    prv_run_until(launch + 29000);
    assert_true(timer_is_vibrating());
    assert_int_equal(timer_data.auto_snooze_count, 0);
    assert_true(s_custom_pattern_count - vibes >= 28);
    prv_run_until(launch + 31500);
    assert_int_equal(timer_data.auto_snooze_count, 1);
}

// 1.5g: a backup launch 2 min late shows about 2:00
static void test_backup_wakeup_two_minutes_late(void **state) {
    prv_sim_backup_launch(51000000, 1, 120);
}

// 1.5g: a second-backup launch 4 min late shows about 4:00
static void test_second_backup_wakeup_four_minutes_late(void **state) {
    prv_sim_backup_launch(52000000, 2, 240);
}

// 1.5g: a second countdown that ended while the app waited for a backup is
// held after that launch, and takes over after the first
static void test_backup_launch_holds_second_ended_countdown(void **state) {
    uint64_t t0 = 53000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 20500);
    prv_slot_countdown(1, 2 * MIN_MS, 60000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(500);
    time_t end_s = (time_t)(t0 / 1000 + 20);
    prv_add_other_app_wakeup(end_s + 30);
    prv_sim_exit();
    assert_int_equal(s_wakeups[0].result, E_RANGE);
    assert_int_equal(prv_saved_pending_mask(), 0x3);

    // The first backup launches the app 2 min after slot 0's end. Slot 1 ended
    // 80 s before this launch.
    prv_sim_fire_wakeup(1);
    prv_assert_alarm_showing(0);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);
    assert_false(timer_slots[1].elapsed);

    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_alarm_showing(1);
    assert_int_equal(timer_get_value_ms(), (int64_t)(s_mock_epoch - (t0 + 60000)));
}

// 1.5g: a wakeup launch for a held alarm that ended 45 s ago: it vibrates for
// its full time and shows about 0:45. The second saved held alarm takes over
// after the first is silenced.
static void test_wakeup_launch_for_held_alarm(void **state) {
    uint64_t t0 = 54000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 4 * MIN_MS);
    prv_slot_countdown(1, 30000, -45000);
    prv_slot_countdown(2, 30000, -30000);
    prv_sim_save(0x7);
    prv_sim_launch_saved(APP_LAUNCH_WAKEUP, 1);

    prv_assert_alarm_showing(1);
    assert_true(s_custom_pattern_count >= 1);
    uint16_t hr, min, sec;
    timer_get_time_parts(&hr, &min, &sec);
    assert_int_equal(min, 0);
    assert_int_equal(sec, 45);
    // The pending key is used up at launch
    assert_false(persist_exists(PERSIST_PENDING_MASK_KEY));

    prv_run_until(t0 + 28000);
    prv_assert_alarm_showing(1);
    assert_int_equal(timer_slots[1].auto_snooze_count, 0);

    prv_sim_press(BUTTON_ID_SELECT, 100);
    prv_assert_alarm_showing(2);
    assert_int_equal(timer_slots[2].auto_snooze_count, 0);
}

// --- D13: a user launch holds a saved held alarm ---

// 1.5g / 1.5j: "Multiple Timers" on: the list shows, and nothing takes over
static void test_user_launch_with_held_alarm_shows_list(void **state) {
    uint64_t t0 = 55000000;
    prv_sim_begin(t0);
    s_mock_multiple_timers = true;
    prv_slot_countdown(0, 5 * MIN_MS, 4 * MIN_MS);
    prv_slot_countdown(1, 30000, -120000);
    prv_sim_save(0x2);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    assert_int_equal(s_timer_list_push_count, 1);
    prv_sim_wait(5000);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 0);
    assert_int_equal(s_custom_pattern_count, 0);
    assert_int_equal(s_blocked_buttons, 0);   // no guard
    // The held alarm is in the watch mask, for the list to mark
    assert_int_equal(timer_ended_mask(timer_watch_mask()), 0x2);
}

// 1.5j: "Multiple Timers" off, a saved held alarm on slot 0 that ended 2 min
// ago: it is the active timer's own alarm and vibrates for its full time
static void test_user_launch_held_slot0_no_list(void **state) {
    uint64_t t0 = 56000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, -120000);
    prv_sim_save(0x1);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    assert_int_equal(s_timer_list_push_count, 0);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
    prv_assert_alarm_showing(0);
    assert_true(s_custom_pattern_count >= 1);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
    assert_int_equal(timer_data.auto_snooze_count, 0);
    uint16_t hr, min, sec;
    timer_get_time_parts(&hr, &min, &sec);
    assert_int_equal(min, 2);
    assert_int_equal(sec, 0);

    // A press 100 ms after the alarm start is ignored
    prv_run_until(t0 + 100);
    prv_sim_press(BUTTON_ID_DOWN, 50);
    prv_assert_alarm_showing(0);
    assert_int_equal(timer_data.length_ms, 30000);

    // Full vibration, counted from the launch
    prv_run_until(t0 + 28000);
    assert_true(timer_is_vibrating());
    assert_int_equal(timer_data.auto_snooze_count, 0);
    prv_run_until(t0 + 32000);
    assert_int_equal(timer_data.auto_snooze_count, 1);
}

// 1.5j: "Multiple Timers" off, a leftover held countdown in slot 1 while slot 0
// counts down: slot 1 takes over at once
static void test_user_launch_leftover_held_slot_takes_over(void **state) {
    uint64_t t0 = 57000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 4 * MIN_MS);
    prv_slot_countdown(1, 30000, -120000);
    prv_sim_save(0x2);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    assert_int_equal(s_timer_list_push_count, 0);
    prv_assert_alarm_showing(1);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=1"), 1);
    assert_true(s_custom_pattern_count >= 1);
    assert_int_equal(timer_slots[1].auto_snooze_count, 0);
}

// --- D14: hold Down shows a held alarm instead of exiting ---

// 1.5l: slot 0 alarms with slot 1 held; hold Down deletes slot 0, and the held
// timer takes over
static void test_hold_down_shows_held_alarm(void **state) {
    uint64_t t0 = 58000000;
    prv_sim_hold_behind_alarm(t0);

    prv_sim_press(BUTTON_ID_DOWN, 1000);
    assert_int_equal(s_window_pop_count, 0);
    assert_int_equal(timer_count, 1);
    // The held timer moved into slot 0 and is on screen
    prv_assert_alarm_showing(0);
    assert_int_equal(timer_data.length_ms, 30000);
    assert_int_equal(prv_log_count("main_alarm_takeover,slot=0"), 1);
    assert_true(s_custom_pattern_count >= 1);
    // Its alarm is still pending
    assert_true(timer_watch_mask() & 1);
}

// 1.5l: with no held alarm, hold Down deletes the timer and exits, as before
static void test_hold_down_exits_without_held_alarm(void **state) {
    uint64_t t0 = 59000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, MIN_MS, 5000);
    prv_slot_countdown(1, 5 * MIN_MS, 5 * MIN_MS);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_run_until(t0 + 6000);
    prv_assert_alarm_showing(0);

    prv_sim_press(BUTTON_ID_DOWN, 1000);
    assert_int_equal(s_window_pop_count, 1);
    assert_int_equal(timer_count, 1);
    assert_int_equal(prv_log_count("main_alarm_takeover"), 0);
}

// 1.4b: a button that leaves an edit mode: hold Down in the edit screen
// deletes the edited timer, and the held alarm takes over
static void test_hold_down_in_edit_mode_shows_held_alarm(void **state) {
    uint64_t t0 = 60000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(500);
    prv_sim_press(BUTTON_ID_UP, 100);
    prv_run_until(t0 + 2100);
    assert_int_equal(main_data.control_mode, ControlModeNew);
    assert_int_equal(prv_log_count("alarm_held,slot=1"), 1);

    prv_sim_press(BUTTON_ID_DOWN, 1000);
    assert_int_equal(s_window_pop_count, 0);
    assert_int_equal(timer_count, 1);
    prv_assert_alarm_showing(0);
    assert_int_equal(timer_data.length_ms, 30000);
}

// --- D5, D15: the auto-quit timer ---

// Launch with one countdown in slot 0, open the edit screen at 0.5 s, and let
// the edit expire (3.6 s after launch)
static void prv_sim_edit_and_expire(void) {
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_sim_wait(500);
    prv_sim_press(BUTTON_ID_UP, 100);
    assert_int_equal(main_data.control_mode, ControlModeNew);
    prv_sim_wait(3100);
    assert_int_equal(main_data.control_mode, ControlModeCounting);
}

// 1.5m: a takeover cancels the auto-quit timer
static void test_takeover_cancels_auto_quit(void **state) {
    uint64_t t0 = 61000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 25 * MIN_MS, 24 * MIN_MS);
    prv_slot_countdown(1, 30000, 13600);
    prv_sim_edit_and_expire();
    assert_non_null(main_data.quit_timer);

    // Slot 1 takes over 10 s after the edit expired
    prv_run_until(t0 + 13600 + 20);
    prv_assert_alarm_showing(1);
    assert_null(main_data.quit_timer);

    prv_run_until(t0 + 3600 + 61000);
    assert_int_equal(s_window_pop_count, 0);
}

// 1.5n: a 21 min countdown with 45 s left: no quit timer starts, and the app
// is still open and vibrating 60 s after the edit expired
static void test_no_auto_quit_with_little_time_left(void **state) {
    uint64_t t0 = 62000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 21 * MIN_MS, 48600);
    prv_sim_edit_and_expire();
    assert_null(main_data.quit_timer);

    prv_run_until(t0 + 48600 + 20);
    prv_assert_alarm_showing(0);
    prv_run_until(t0 + 3600 + 60500);
    assert_int_equal(s_window_pop_count, 0);
    assert_true(timer_is_vibrating());
}

// 1.5n: 25 min with 21 min left: the quit timer starts and quits, as before
static void test_auto_quit_with_over_20_min_left(void **state) {
    uint64_t t0 = 63000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 25 * MIN_MS, 21 * MIN_MS + 30000);
    prv_sim_edit_and_expire();
    assert_non_null(main_data.quit_timer);

    prv_run_until(t0 + 3600 + QUIT_DELAY_MS + 100);
    assert_int_equal(s_window_pop_count, 1);
}

// 1.5n: 25 min with 19 min left: no quit timer
static void test_no_auto_quit_with_19_min_left(void **state) {
    uint64_t t0 = 64000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 25 * MIN_MS, 19 * MIN_MS);
    prv_sim_edit_and_expire();
    assert_null(main_data.quit_timer);

    prv_run_until(t0 + 3600 + QUIT_DELAY_MS + 100);
    assert_int_equal(s_window_pop_count, 0);
}

// 1.5n: the quit timer fires while another slot's alarm waits: the app does
// not quit, and that alarm takes over
static void test_quit_callback_with_held_alarm_takes_over(void **state) {
    uint64_t t0 = 65000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 25 * MIN_MS, 24 * MIN_MS);
    prv_slot_countdown(1, 30000, -5000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    // Slot 1 was overdue at launch, so nothing watches it. Make it a pending
    // alarm without running the watch, as if it ended this instant.
    assert_int_equal(timer_get_active_slot(), 0);
    timer_watch_restore(0x3);

    prv_quit_callback(NULL);
    assert_int_equal(s_window_pop_count, 0);
    prv_assert_alarm_showing(1);
}

// 1.5n: the quit timer fires while the active alarm vibrates: no quit
static void test_quit_callback_during_alarm_does_not_quit(void **state) {
    uint64_t t0 = 66000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, MIN_MS, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_run_until(t0 + 3000);
    prv_assert_alarm_showing(0);

    prv_quit_callback(NULL);
    assert_int_equal(s_window_pop_count, 0);
    assert_true(timer_is_vibrating());
}

// --- D16: an alarm stays pending until it has rung and stopped ---

// Slot 0 is a 5 min countdown on screen; slot 1 (30 s) takes over 3 s after
// launch. Runs to 5 s after launch (2 s into the vibration).
static void prv_sim_takeover_vibrating(uint64_t t0) {
    prv_sim_begin(t0);
    prv_slot_countdown(0, 5 * MIN_MS, 5 * MIN_MS);
    prv_slot_countdown(1, 30000, 3000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_run_until(t0 + 3100);
    prv_assert_alarm_showing(1);
}

// 1.5o: a takeover, then an exit 2 s into the vibration with no press: the
// alarm is still pending, so the app wakes up 10 s later and shows it again
static void test_exit_during_takeover_alarm_rings_again(void **state) {
    uint64_t t0 = 67000000;
    prv_sim_takeover_vibrating(t0);
    prv_run_until(t0 + 5000);
    prv_sim_exit();

    prv_assert_wakeups((time_t)(t0 / 1000 + 5 + HELD_WAKEUP_DELAY_S), 1);
    assert_int_equal(prv_saved_pending_mask(), 0x3);

    prv_log_clear();
    prv_reset_vibe_counters();
    prv_sim_fire_wakeup(0);
    uint64_t launch = s_mock_epoch;
    prv_assert_alarm_showing(1);
    assert_true(s_custom_pattern_count >= 1);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 1);
    // Real overtime: it ended 3 s after t0
    assert_int_equal(timer_get_value_ms(), (int64_t)(launch - (t0 + 3000)));
    // Full vibration from this launch
    prv_run_until(launch + 28000);
    assert_true(timer_is_vibrating());
    assert_int_equal(timer_data.auto_snooze_count, 0);
}

// 1.5o: the app closes after a launch restored a pending alarm, before the
// alarm vibrated: the bit is saved again and a wakeup is scheduled at +10 s
static void test_exit_before_alarm_vibrates_keeps_it_pending(void **state) {
    uint64_t t0 = 68000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, -5000);
    prv_sim_save(0x1);
    prv_sim_launch_saved(APP_LAUNCH_WAKEUP, 0);
    // Put the alarm state back to "restored at launch, not checked yet", the
    // state before the first refresh of the main window
    timer_watch_restore(0x1);
    assert_int_equal(timer_alarm_rang_slot(), -1);
    prv_sim_exit();

    prv_assert_wakeups((time_t)(t0 / 1000 + HELD_WAKEUP_DELAY_S), 0);
    assert_int_equal(prv_saved_pending_mask(), 0x1);
}

// 1.5o: one countdown only; its own alarm vibrates and the app exits with no
// press: the app wakes up 10 s later
static void test_exit_during_own_alarm_rings_again(void **state) {
    uint64_t t0 = 69000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_run_until(t0 + 4000);
    prv_assert_alarm_showing(0);
    prv_sim_exit();

    prv_assert_wakeups((time_t)(t0 / 1000 + 4 + HELD_WAKEUP_DELAY_S), 0);
    assert_int_equal(prv_saved_pending_mask(), 0x1);
}

// 1.5o: a takeover, then a Back at +100 ms that the guard ignores, then an
// exit: the alarm is still pending
static void test_exit_after_guarded_press_rings_again(void **state) {
    uint64_t t0 = 70000000;
    prv_sim_takeover_vibrating(t0);
    // The takeover was at t0 + 3000; Back 100 ms later is inside the window
    assert_true(s_mock_epoch <= t0 + 3100);
    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_alarm_showing(1);
    assert_int_equal(s_window_pop_count, 0);
    prv_run_until(t0 + 4000);
    prv_sim_exit();

    prv_assert_wakeups((time_t)(t0 / 1000 + 4 + HELD_WAKEUP_DELAY_S), 1);
    assert_int_equal(prv_saved_pending_mask(), 0x3);
}

// 1.5o: Select silences the alarm, then the app exits: no wakeup for that
// slot, its bit is not saved, and a user launch restores a pending mask of 0
static void test_exit_after_silenced_alarm_is_not_pending(void **state) {
    uint64_t t0 = 71000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_run_until(t0 + 4000);
    prv_assert_alarm_showing(0);
    prv_sim_press(BUTTON_ID_SELECT, 100);
    assert_false(timer_is_vibrating());
    assert_int_equal(timer_watch_mask(), 0);
    prv_sim_exit();

    assert_int_equal(s_wakeup_count, 0);
    assert_int_equal(prv_saved_pending_mask(), 0);

    // A user launch 3 s later: no slot is held
    s_mock_epoch += 3000;
    prv_log_clear();
    prv_reset_vibe_counters();
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    assert_int_equal(timer_watch_mask(), 0);
    assert_false(timer_is_vibrating());
    assert_int_equal(s_custom_pattern_count, 0);
}

// 1.5o: the 30 s vibration ends on its own: the alarm is no longer pending;
// the timer auto-snoozes and is watched as a countdown with time left
static void test_alarm_that_stops_on_its_own_is_not_pending(void **state) {
    uint64_t t0 = 72000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    prv_run_until(t0 + 2000 + 30000 + 1100);

    assert_false(timer_is_vibrating());
    assert_int_equal(timer_data.auto_snooze_count, 1);
    assert_int_equal(timer_watch_mask(), 0x1);
    assert_int_equal(timer_ended_mask(timer_watch_mask()), 0);

    // An exit now schedules the snoozed end, not a held alarm at +10 s
    uint64_t exit_ms = s_mock_epoch;
    prv_sim_exit();
    assert_int_equal(s_wakeup_count, 3);
    assert_int_equal(s_wakeups[0].time,
                     (time_t)((exit_ms + timer_get_value_ms()) / 1000));
    assert_true(s_wakeups[0].time > (time_t)(exit_ms / 1000) + HELD_WAKEUP_DELAY_S);
}

// 1.5o: Select silences slot 0 with slot 1 held: slot 0's bit is cleared and
// slot 1 takes over in the same call; slot 1's bit stays set
static void test_silence_clears_bit_and_held_takes_over(void **state) {
    uint64_t t0 = 73000000;
    prv_sim_hold_behind_alarm(t0);
    assert_int_equal(timer_watch_mask(), 0x3);

    prv_sim_press(BUTTON_ID_SELECT, 100);
    prv_assert_alarm_showing(1);
    assert_int_equal(timer_watch_mask(), 0x2);
}

// --- D17: the guard starts at every alarm start ---

// 1.5q: on a user launch, the on-screen countdown's own alarm is guarded: a
// Down 100 ms after the alarm starts is ignored, and a Down at 500 ms snoozes
static void test_sim_alarm_start_on_user_launch_guarded(void **state) {
    uint64_t t0 = 74000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 10000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    assert_int_equal(s_timer_list_push_count, 0);
    assert_int_equal(s_blocked_buttons, 0);

    uint64_t alarm = prv_sim_wait_for_alarm(11000);
    assert_true(alarm != 0);
    prv_run_until(alarm + 100);
    prv_sim_press(BUTTON_ID_DOWN, 100);
    prv_assert_alarm_showing(0);
    assert_int_equal(timer_data.length_ms, 30000);

    prv_run_until(alarm + 500);
    prv_sim_press(BUTTON_ID_DOWN, 100);
    assert_false(timer_is_vibrating());
    assert_int_equal(timer_data.length_ms, 30000 + SNOOZE_INCREMENT_MS);
}

// 1.5r: a snoozed timer that reaches zero again with the app open is guarded:
// a Back 100 ms after the alarm starts is ignored
static void test_sim_snoozed_alarm_is_guarded(void **state) {
    uint64_t t0 = 75000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);
    assert_true(prv_sim_wait_for_alarm(3000) != 0);
    prv_sim_wait(1000);
    prv_sim_press(BUTTON_ID_DOWN, 100);          // snooze: +5 min
    assert_false(timer_is_vibrating());

    uint64_t alarm = prv_sim_wait_for_alarm(SNOOZE_INCREMENT_MS + 1000);
    assert_true(alarm != 0);
    prv_run_until(alarm + 100);
    prv_sim_press(BUTTON_ID_BACK, 50);
    prv_assert_alarm_showing(0);
    assert_int_equal(s_window_pop_count, 0);
    assert_int_equal(prv_log_count("TEST_STATE:alarm_start"), 2);
}

// 1.5r: a Down held across the alarm start is ignored on release
static void test_sim_press_held_across_alarm_start_ignored(void **state) {
    uint64_t t0 = 76000000;
    prv_sim_begin(t0);
    prv_slot_countdown(0, 30000, 2000);
    prv_sim_save(0);
    prv_sim_launch_saved(APP_LAUNCH_SYSTEM, 0);

    prv_run_until(t0 + 1800);
    assert_false(timer_is_vibrating());
    prv_sim_press(BUTTON_ID_DOWN, 400);          // down at 1.8 s, up at 2.2 s
    prv_assert_alarm_showing(0);
    assert_int_equal(timer_data.length_ms, 30000);
}

// --- Lap stopwatch: double-press Select to pause, display freeze ------------
// The handlers are called directly in the order the SDK fires them: raw-down
// on each press, then the multi-click handler (a double press), or the single
// click handler after the double-press window (a single press), or the long
// click handler. A button is "armed" when it has a multi-click subscription.

#define LAP_TEST_T0 30000000

// A running lap stopwatch in slot 0 that has counted elapsed_ms, shown in
// Counting mode with the Lap Stopwatch setting on
static void prv_setup_lap_stopwatch(int64_t elapsed_ms) {
    prv_fake_timers_clear();
    prv_log_clear();
    prv_reset_app_statics();
    main_data.window = (Window *)1;
    main_data.flash_lap_slot = -1;
    main_data.control_mode = ControlModeCounting;
    s_mock_lap_stopwatch_enabled = true;
    s_mock_epoch = LAP_TEST_T0;
    memset(timer_slots, 0, sizeof(timer_slots));
    timer_count = 0;
    timer_set_active_slot(0);
    prv_slot_chrono(0, elapsed_ms);
    prv_refresh_click_config();
}

static int prv_lap_teardown(void **state) {
    s_mock_lap_stopwatch_enabled = false;
    prv_fake_timers_clear();
    return prv_sim_teardown(state);
}

static void prv_lap_at(uint64_t ms_after_t0) {
    s_mock_epoch = LAP_TEST_T0 + ms_after_t0;
}

static bool prv_select_is_armed(void) {
    return s_sub_multi[BUTTON_ID_SELECT] != NULL;
}

// 1.3: a double press pauses at the first press-down time and records no lap
static void test_double_press_pauses_at_first_press_down(void **state) {
    prv_setup_lap_stopwatch(5000);
    assert_true(prv_select_is_armed());

    prv_select_raw_click_handler(NULL, NULL);       // first press-down at 5.000 s
    prv_lap_at(150);
    prv_select_raw_click_handler(NULL, NULL);       // second press-down
    prv_lap_at(200);
    s_sub_multi[BUTTON_ID_SELECT](NULL, NULL);      // the double press is recognised

    assert_true(timer_is_paused());
    assert_int_equal(timer_get_value_ms(), 5000);
    assert_int_equal(timer_count, 1);
    assert_int_equal(prv_log_count("TEST_STATE:lap_recorded"), 0);
    assert_int_equal(prv_log_count("TEST_STATE:double_press_select"), 1);
    // Paused: the double press is no longer armed
    assert_false(prv_select_is_armed());
}

// 1.3: a double press during the lap flash cancels the flash and pauses
static void test_double_press_during_flash_pauses(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_select_raw_click_handler(NULL, NULL);
    prv_lap_at(350);
    prv_select_click_handler(NULL, NULL);           // lap 1, the flash starts
    assert_int_equal(timer_count, 2);
    assert_int_equal(main_data.flash_lap_slot, 1);

    prv_lap_at(2000);
    prv_select_raw_click_handler(NULL, NULL);       // first press-down at 7.000 s
    prv_lap_at(2150);
    prv_select_raw_click_handler(NULL, NULL);
    prv_lap_at(2200);
    s_sub_multi[BUTTON_ID_SELECT](NULL, NULL);

    assert_int_equal(main_data.flash_lap_slot, -1);
    assert_int_equal(timer_get_active_slot(), 0);
    assert_true(timer_is_paused());
    assert_int_equal(timer_get_value_ms(), 7000);
    assert_int_equal(timer_count, 2);
}

// The lap value is the stopwatch value at press-down, not at the delayed
// single click
static void test_single_press_lap_uses_press_down_time(void **state) {
    prv_setup_lap_stopwatch(5000);

    prv_select_raw_click_handler(NULL, NULL);       // press-down at 5.000 s
    prv_lap_at(350);                                // the double-press window is over
    prv_select_click_handler(NULL, NULL);

    assert_int_equal(timer_count, 2);
    assert_true(timer_slots[1].is_paused);
    assert_int_equal(timer_slots[1].start_ms, 5000);
    assert_int_equal(timer_slots[0].last_lap_ms, 5000);
    assert_false(timer_slots[0].is_paused);
}

// 1.4: multi-click is subscribed only for a running lap stopwatch in Counting
static void test_multi_click_subscribed_only_while_armed(void **state) {
    prv_setup_lap_stopwatch(5000);
    assert_true(prv_select_is_armed());
    assert_int_equal(s_sub_multi_timeout[BUTTON_ID_SELECT], 300);
    assert_null(s_sub_multi[BUTTON_ID_UP]);
    assert_null(s_sub_multi[BUTTON_ID_DOWN]);
    assert_null(s_sub_multi[BUTTON_ID_BACK]);

    // Edit modes
    main_data.control_mode = ControlModeNew;
    prv_refresh_click_config();
    assert_false(prv_select_is_armed());
    main_data.control_mode = ControlModeEditSec;
    prv_refresh_click_config();
    assert_false(prv_select_is_armed());

    // Back to Counting: armed again
    main_data.control_mode = ControlModeCounting;
    prv_refresh_click_config();
    assert_true(prv_select_is_armed());

    // Paused stopwatch
    timer_toggle_play_pause();
    prv_refresh_click_config();
    assert_false(prv_select_is_armed());
    timer_toggle_play_pause();
    prv_refresh_click_config();
    assert_true(prv_select_is_armed());

    // Setting off
    s_mock_lap_stopwatch_enabled = false;
    prv_refresh_click_config();
    assert_false(prv_select_is_armed());
    s_mock_lap_stopwatch_enabled = true;

    // Running countdown
    prv_slot_countdown(0, 5 * MIN_MS, 4 * MIN_MS);
    prv_refresh_click_config();
    assert_false(prv_select_is_armed());
}

// 1.4: the handlers keep the subscription in step: Up (to New mode) disarms,
// and a single Select that resumes a paused stopwatch arms
static void test_handlers_refresh_the_click_config(void **state) {
    prv_setup_lap_stopwatch(5000);

    prv_up_click_handler(NULL, NULL);
    assert_int_equal(main_data.control_mode, ControlModeNew);
    assert_false(prv_select_is_armed());

    prv_run_until(s_mock_epoch + 3100);             // the edit expires
    assert_int_equal(main_data.control_mode, ControlModeCounting);
    assert_true(prv_select_is_armed());

    timer_toggle_play_pause();
    prv_refresh_click_config();
    assert_false(prv_select_is_armed());
    prv_select_raw_click_handler(NULL, NULL);
    prv_select_click_handler(NULL, NULL);           // resumes at once: no lap
    assert_false(timer_is_paused());
    assert_int_equal(timer_count, 1);
    assert_true(prv_select_is_armed());
}

// 1.4: an alarm takeover disarms the double press
static void test_alarm_takeover_disarms_double_press(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_slot_countdown(1, 30000, -1000);
    assert_true(prv_select_is_armed());

    prv_take_over(1);

    prv_assert_alarm_showing(1);
    assert_false(prv_select_is_armed());
}

// 1.6: press-down while armed freezes the display at the press time
static void test_press_down_while_armed_freezes_display(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_lap_at(40);
    prv_select_raw_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, LAP_TEST_T0 + 40);
    // The timer state is not changed
    assert_false(timer_is_paused());
}

// 1.6: no freeze when the double press is not armed
static void test_press_down_when_not_armed_does_not_freeze(void **state) {
    prv_setup_lap_stopwatch(5000);
    timer_toggle_play_pause();                      // paused
    prv_refresh_click_config();
    prv_select_raw_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, -1);

    prv_setup_lap_stopwatch(5000);
    main_data.control_mode = ControlModeNew;        // edit mode
    prv_refresh_click_config();
    prv_select_raw_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, -1);

    prv_setup_lap_stopwatch(5000);
    s_mock_lap_stopwatch_enabled = false;           // setting off
    prv_refresh_click_config();
    prv_select_raw_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, -1);
}

// 1.6: the single, double, and long handlers each end the freeze
static void test_click_handlers_clear_the_freeze(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_select_raw_click_handler(NULL, NULL);
    assert_true(s_mock_freeze_ms >= 0);
    prv_lap_at(350);
    prv_select_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, -1);

    prv_setup_lap_stopwatch(5000);
    prv_select_raw_click_handler(NULL, NULL);
    prv_lap_at(150);
    prv_select_raw_click_handler(NULL, NULL);
    // The second press-down keeps the freeze of the first one
    assert_int_equal(s_mock_freeze_ms, LAP_TEST_T0);
    s_sub_multi[BUTTON_ID_SELECT](NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, -1);

    prv_setup_lap_stopwatch(5000);
    prv_select_raw_click_handler(NULL, NULL);
    prv_lap_at(BUTTON_HOLD_RESET_MS);
    assert_true(s_mock_freeze_ms >= 0);             // frozen while the button is held
    prv_select_long_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, -1);
    assert_int_equal(timer_get_value_ms(), 0);      // restarted
}

// 1.6: the lap-full warning ends the freeze
static void test_lap_full_clears_the_freeze(void **state) {
    prv_setup_lap_stopwatch(5000);
    for (uint8_t i = 1; i < MAX_TIMERS; i++) {
        prv_slot_chrono(i, 1000);
        timer_slots[i].is_paused = true;
        timer_slots[i].start_ms = 1000;
    }
    assert_int_equal(timer_count, MAX_TIMERS);

    prv_select_raw_click_handler(NULL, NULL);
    assert_true(s_mock_freeze_ms >= 0);
    prv_lap_at(350);
    prv_select_click_handler(NULL, NULL);

    assert_int_equal(s_mock_freeze_ms, -1);
    assert_int_equal(prv_log_count("TEST_STATE:lap_full"), 1);
    assert_int_equal(timer_count, MAX_TIMERS);
    assert_false(timer_is_paused());
}

// 1.6: with no click handler, the freeze ends after about 1 s and changes nothing
static void test_freeze_safety_timeout(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_select_raw_click_handler(NULL, NULL);
    // Still frozen at the end of the slowest press that resolves: a hold just
    // short of the long press, then the double-press window
    prv_run_until(LAP_TEST_T0 + BUTTON_HOLD_RESET_MS + 300);
    assert_int_equal(s_mock_freeze_ms, LAP_TEST_T0);
    prv_run_until(LAP_TEST_T0 + 1250);
    assert_int_equal(s_mock_freeze_ms, -1);
    assert_false(timer_is_paused());
    assert_int_equal(timer_count, 1);
    // The next press is a new press: it gets its own press-down time
    prv_lap_at(3000);
    prv_select_raw_click_handler(NULL, NULL);
    assert_int_equal(s_mock_freeze_ms, LAP_TEST_T0 + 3000);
}

// 1.6: a press-down during the lap flash cancels the flash and freezes the
// running stopwatch; a flash tick that is due before the press resolves does
// not change the frozen display
static void test_press_down_during_flash_freezes_running_stopwatch(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_select_raw_click_handler(NULL, NULL);
    prv_lap_at(350);
    prv_select_click_handler(NULL, NULL);           // lap 1: flash tick due at +1350
    assert_int_equal(s_mock_slot_override, 1);

    prv_run_until(LAP_TEST_T0 + 1250);
    assert_int_equal(s_mock_slot_override, 1);
    prv_select_raw_click_handler(NULL, NULL);       // press-down during the flash
    assert_int_equal(s_mock_slot_override, -1);
    assert_int_equal(main_data.flash_lap_slot, -1);
    assert_int_equal(s_mock_freeze_ms, LAP_TEST_T0 + 1250);

    prv_run_until(LAP_TEST_T0 + 1450);              // past the old flash tick
    assert_int_equal(s_mock_slot_override, -1);
    assert_int_equal(s_mock_freeze_ms, LAP_TEST_T0 + 1250);
    assert_int_equal(prv_log_count("TEST_STATE:flash_phase"), 0);

    // A single press then starts a new flash for the new lap
    prv_run_until(LAP_TEST_T0 + 1600);
    prv_select_click_handler(NULL, NULL);
    assert_int_equal(timer_count, 3);
    assert_int_equal(s_mock_slot_override, 2);
    assert_int_equal(timer_slots[2].start_ms, 6250);
    assert_int_equal(s_mock_freeze_ms, -1);
}

// 1.9: a double press that the wakeup input guard blocks does nothing
static void test_double_press_blocked_by_input_guard(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_start_input_guard();

    prv_lap_at(100);
    prv_select_raw_click_handler(NULL, NULL);       // press-down inside the window
    prv_lap_at(250);
    prv_select_raw_click_handler(NULL, NULL);
    prv_lap_at(300);
    s_sub_multi[BUTTON_ID_SELECT](NULL, NULL);

    assert_false(timer_is_paused());
    assert_int_equal(timer_count, 1);
    assert_int_equal(s_mock_freeze_ms, -1);
    assert_int_equal(prv_log_count("TEST_STATE:double_press_select"), 0);
    assert_true(prv_log_count("TEST_STATE:input_blocked") > 0);
    s_blocked_buttons = 0;
}

// 1.10: an alarm takeover with the display frozen ends the freeze and the
// pending press
static void test_alarm_takeover_clears_the_freeze(void **state) {
    prv_setup_lap_stopwatch(5000);
    prv_slot_countdown(1, 30000, -1000);
    prv_select_raw_click_handler(NULL, NULL);
    assert_true(s_mock_freeze_ms >= 0);
    assert_true(main_data.select_press_pending);

    prv_lap_at(100);
    prv_take_over(1);

    prv_assert_alarm_showing(1);
    assert_int_equal(s_mock_freeze_ms, -1);
    assert_false(main_data.select_press_pending);
    // The press in progress does not act on the alarm
    prv_lap_at(350);
    prv_select_click_handler(NULL, NULL);
    prv_assert_alarm_showing(1);
    assert_int_equal(timer_count, 2);
    s_blocked_buttons = 0;
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_sim_no_alarm_on_stopwatch_after_edit_increment),
        cmocka_unit_test(test_sim_ten_second_timer_counts_down_smoothly),
        cmocka_unit_test(test_sim_countdown_never_counts_up_sweep),
        cmocka_unit_test(test_sim_light_stays_on_after_select_starts_timer),
        cmocka_unit_test(test_sim_light_stays_on_after_select_silences_alarm),
        cmocka_unit_test(test_sim_guard_covers_alarm_start_after_early_wakeup),
        cmocka_unit_test(test_wakeup_guard_select_press_in_window_ignored),
        cmocka_unit_test(test_wakeup_guard_up_press_in_window_ignored),
        cmocka_unit_test(test_wakeup_guard_down_press_in_window_ignored),
        cmocka_unit_test(test_wakeup_guard_back_press_in_window_ignored),
        cmocka_unit_test(test_wakeup_guard_long_press_started_in_window_ignored),
        cmocka_unit_test(test_wakeup_guard_press_held_before_launch_ignored),
        cmocka_unit_test(test_wakeup_guard_down_press_after_window_snoozes),
        cmocka_unit_test(test_wakeup_guard_back_press_after_window_silences),
        cmocka_unit_test(test_wakeup_guard_new_press_after_ignored_press_acts),
        cmocka_unit_test(test_wakeup_guard_press_late_in_window_ignored),
        cmocka_unit_test(test_wakeup_guard_not_applied_on_user_launch),
        cmocka_unit_test(test_interaction_active_honors_screen_on_setting),
        cmocka_unit_test(test_down_extension_honors_down_extra_setting),
        cmocka_unit_test(test_down_press_records_extension_window),
        cmocka_unit_test(test_dictation_success_vibrates_and_sets_name),
        cmocka_unit_test(test_dictation_system_aborted_buzzes),
        cmocka_unit_test(test_dictation_no_speech_buzzes),
        cmocka_unit_test(test_dictation_connectivity_error_buzzes),
        cmocka_unit_test(test_dictation_disabled_buzzes),
        cmocka_unit_test(test_dictation_internal_error_buzzes),
        cmocka_unit_test(test_dictation_recognizer_error_buzzes),
        cmocka_unit_test(test_dictation_transcription_rejected_is_silent),
        cmocka_unit_test(test_dictation_rejected_with_error_is_silent),
        cmocka_unit_test(test_dictation_confirmation_disabled),
        cmocka_unit_test(test_restart_stopwatch_preserves_custom_name),
        cmocka_unit_test(test_restart_unnamed_stopwatch_reassigns_name),
        cmocka_unit_test(test_lap_setting_countdown_select_pauses_not_lap),
        cmocka_unit_test(test_apply_edit_increment_adds_time_and_sets_flag),
        cmocka_unit_test(test_down_click_in_new_mode_updates_backlight),
        cmocka_unit_test(test_down_click_in_edit_sec_mode_updates_backlight),
        cmocka_unit_test(test_seconds_timer_bug),
        cmocka_unit_test(test_first_launch_starts_in_new_mode),
        cmocka_unit_test(test_swap_back_toggles_to_editsec_from_new),
        cmocka_unit_test(test_swap_select_long_adds_time_in_new),
        cmocka_unit_test(test_up_long_restarts_repeating_timer_after_final_alarm),
        cmocka_unit_test(test_up_long_restarts_nonrepeating_timer_at_base_length),
        cmocka_unit_test(test_toggle_repeat_off_after_repeat_keeps_original_length),
        cmocka_unit_test(test_down_click_intermediate_repeat_keeps_base_length),
        // list-alarm-takeover: these change the saved-state mocks, so they run last
        cmocka_unit_test_teardown(test_show_alarm_on_vibrating_slot, prv_sim_teardown),
        cmocka_unit_test_teardown(test_show_alarm_on_unchecked_slot, prv_sim_teardown),
        cmocka_unit_test_teardown(test_show_alarm_guards_presses, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_takeover_when_not_busy, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_hold_logged_once, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_takes_over_on_select, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_takes_over_on_back, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_takes_over_on_down, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_takes_over_when_vibration_ends, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_up_on_alarm_keeps_held_alarm_waiting, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_behind_new_mode, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_behind_edit_sec, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_behind_edit_repeat, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_two_held_open_in_order, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_held_45s_vibrates_for_full_time, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_overdue_at_launch_never_takes_over, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_no_alarm_behind_the_list, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_list_exit_reruns_the_check, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_one_held, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_two_held, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_held_and_active_ending_later, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_held_and_active_ending_sooner, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_active_only, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_non_active_ends_first, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_two_non_active, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_primary_blocked_by_other_app, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_primary_and_backup_blocked, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_no_pending_alarm, prv_sim_teardown),
        cmocka_unit_test_teardown(test_primary_wakeup_cancels_backups, prv_sim_teardown),
        cmocka_unit_test_teardown(test_backup_wakeup_two_minutes_late, prv_sim_teardown),
        cmocka_unit_test_teardown(test_second_backup_wakeup_four_minutes_late, prv_sim_teardown),
        cmocka_unit_test_teardown(test_backup_launch_holds_second_ended_countdown, prv_sim_teardown),
        cmocka_unit_test_teardown(test_wakeup_launch_for_held_alarm, prv_sim_teardown),
        cmocka_unit_test_teardown(test_user_launch_with_held_alarm_shows_list, prv_sim_teardown),
        cmocka_unit_test_teardown(test_user_launch_held_slot0_no_list, prv_sim_teardown),
        cmocka_unit_test_teardown(test_user_launch_leftover_held_slot_takes_over, prv_sim_teardown),
        cmocka_unit_test_teardown(test_hold_down_shows_held_alarm, prv_sim_teardown),
        cmocka_unit_test_teardown(test_hold_down_exits_without_held_alarm, prv_sim_teardown),
        cmocka_unit_test_teardown(test_hold_down_in_edit_mode_shows_held_alarm, prv_sim_teardown),
        cmocka_unit_test_teardown(test_takeover_cancels_auto_quit, prv_sim_teardown),
        cmocka_unit_test_teardown(test_no_auto_quit_with_little_time_left, prv_sim_teardown),
        cmocka_unit_test_teardown(test_auto_quit_with_over_20_min_left, prv_sim_teardown),
        cmocka_unit_test_teardown(test_no_auto_quit_with_19_min_left, prv_sim_teardown),
        cmocka_unit_test_teardown(test_quit_callback_with_held_alarm_takes_over, prv_sim_teardown),
        cmocka_unit_test_teardown(test_quit_callback_during_alarm_does_not_quit, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_during_takeover_alarm_rings_again, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_before_alarm_vibrates_keeps_it_pending, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_during_own_alarm_rings_again, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_after_guarded_press_rings_again, prv_sim_teardown),
        cmocka_unit_test_teardown(test_exit_after_silenced_alarm_is_not_pending, prv_sim_teardown),
        cmocka_unit_test_teardown(test_alarm_that_stops_on_its_own_is_not_pending, prv_sim_teardown),
        cmocka_unit_test_teardown(test_silence_clears_bit_and_held_takes_over, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_alarm_start_on_user_launch_guarded, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_snoozed_alarm_is_guarded, prv_sim_teardown),
        cmocka_unit_test_teardown(test_sim_press_held_across_alarm_start_ignored, prv_sim_teardown),
        // lap-double-press-pause: these also change the slots, so they run last
        cmocka_unit_test_teardown(test_double_press_pauses_at_first_press_down, prv_lap_teardown),
        cmocka_unit_test_teardown(test_double_press_during_flash_pauses, prv_lap_teardown),
        cmocka_unit_test_teardown(test_single_press_lap_uses_press_down_time, prv_lap_teardown),
        cmocka_unit_test_teardown(test_multi_click_subscribed_only_while_armed, prv_lap_teardown),
        cmocka_unit_test_teardown(test_handlers_refresh_the_click_config, prv_lap_teardown),
        cmocka_unit_test_teardown(test_alarm_takeover_disarms_double_press, prv_lap_teardown),
        cmocka_unit_test_teardown(test_press_down_while_armed_freezes_display, prv_lap_teardown),
        cmocka_unit_test_teardown(test_press_down_when_not_armed_does_not_freeze, prv_lap_teardown),
        cmocka_unit_test_teardown(test_click_handlers_clear_the_freeze, prv_lap_teardown),
        cmocka_unit_test_teardown(test_lap_full_clears_the_freeze, prv_lap_teardown),
        cmocka_unit_test_teardown(test_freeze_safety_timeout, prv_lap_teardown),
        cmocka_unit_test_teardown(test_press_down_during_flash_freezes_running_stopwatch, prv_lap_teardown),
        cmocka_unit_test_teardown(test_double_press_blocked_by_input_guard, prv_lap_teardown),
        cmocka_unit_test_teardown(test_alarm_takeover_clears_the_freeze, prv_lap_teardown),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
