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
void drawing_set_slot_override(int8_t slot) {}
int8_t drawing_get_slot_override(void) { return -1; }

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
static bool s_mock_lap_stopwatch_enabled = false;
bool settings_get_lap_stopwatch_enabled(void) { return s_mock_lap_stopwatch_enabled; }
static uint32_t s_mock_screen_on_seconds = 10;
static uint32_t s_mock_down_extra_seconds = 60;
uint32_t settings_get_screen_on_seconds(void) { return s_mock_screen_on_seconds; }
uint32_t settings_get_down_extra_seconds(void) { return s_mock_down_extra_seconds; }

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

int main(void) {
    const struct CMUnitTest tests[] = {
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
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
