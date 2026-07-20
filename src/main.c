// @file main.c
// @brief Main logic for QuickTimer
//
// Contains the higher level logic code
//
// @author Eric D. Phillips & Jared Johnston
// @date November 11, 2025
// @bugs No known bugs

#include <pebble.h>
#include "main.h"
#include "drawing.h"
#include "settings.h"
#include "timer.h"
#include "timer_list.h"
#include "utility.h"

// Main constants
#define AUTO_BACKGROUND_TIMER_LENGTH_MS (MSEC_IN_MIN * 20)
#define AUTO_BACKGROUND_CHRONO 0
#define QUIT_DELAY_MS 60000
#define BUTTON_HOLD_REPEAT_MS 100
#define UP_BUTTON_INCREMENT_MS MSEC_IN_MIN * 20
#define SELECT_BUTTON_INCREMENT_MS MSEC_IN_MIN * 5
#define DOWN_BUTTON_INCREMENT_MS MSEC_IN_MIN
#define BACK_BUTTON_INCREMENT_MS MSEC_IN_MIN * 60
#define UP_BUTTON_INCREMENT_SEC_MS MSEC_IN_SEC * 20
#define SELECT_BUTTON_INCREMENT_SEC_MS MSEC_IN_SEC * 5
#define DOWN_BUTTON_INCREMENT_SEC_MS MSEC_IN_SEC
#define BACK_BUTTON_INCREMENT_SEC_MS MSEC_IN_SEC * 60
#define NEW_EXPIRE_TIME_MS MSEC_IN_SEC * 3
#define BACKLIGHT_EDIT_LINGER_MS MSEC_IN_SEC
#define INTERACTION_TIMEOUT_MS 10000

// Main data structure
static struct {
  Window      *window;      //< The base window for the application
  Layer       *layer;       //< The base layer on which everything will be drawn
  ControlMode control_mode; //< The current control mode of the timer
  AppTimer    *app_timer;   //< The AppTimer to keep the screen refreshing
    AppTimer    *new_expire_timer; //< Moves to counting mode if a button is not pressed in the given time
    AppTimer    *quit_timer;      //< The AppTimer to quit the app after a delay
    bool        is_editing_existing_timer; //< True if the app is in ControlModeNew for editing an existing timer
    uint64_t    last_interaction_time;     //< Time of the last user interaction
    bool        timer_length_modified_in_edit_mode; //< True if the timer's length has been modified while in ControlModeNew
    bool        last_interaction_was_down; //< True if the last interaction was a down button press
    bool        is_reverse_direction; //< True if the timer should be decremented instead of incremented
#if LAP_FEATURE
    // Lap flash state: after a lap is recorded the display alternates between
    // the paused lap slot and the original timer for FLASH_WINDOW_MS
    AppTimer    *flash_timer;         //< 1s toggle timer driving the lap flash
    int8_t      flash_lap_slot;       //< Lap slot shown during "on" frames (-1 = no flash)
    uint64_t    flash_deadline_ms;    //< Epoch (ms) at which the flash stops
    bool        flash_showing_lap;    //< True while the lap slot is the rendered frame
    bool        flash_show_limit_warning; //< Show the slots-left warning in the "original" frames
#endif
  } main_data;

static AppTimer *backlight_timer = NULL;
static bool backlight_on = false;

// POC: Up+Back chord feasibility test
static bool s_up_held = false;

static bool s_up_chord_consumed = false;

#ifdef PBL_MICROPHONE
// Voice naming: dictation session for the Up+Back chord rename gesture
static DictationSession *s_dictation_session = NULL;
// Offline feedback: shown when a rename is started while the phone is disconnected
#define NO_PHONE_FEEDBACK_MS 1000
static bool s_show_no_phone = false;
static AppTimer *s_no_phone_timer = NULL;
#endif

#if LAP_FEATURE
// Lap flash timing: alternate lap/original every 1s for 5 seconds
#define FLASH_TICK_MS 1000
#define FLASH_WINDOW_MS 5000

// Slot-limit warning overlay ("N slots left" / "No free slots"), held 3 seconds
#define WARNING_FEEDBACK_MS 3000
static char s_warning_text[32];
static bool s_show_warning = false;
static AppTimer *s_warning_timer = NULL;
#endif

// Function declarations
static void prv_app_timer_callback(void *data);
static void prv_new_expire_callback(void *data);
static void prv_reset_new_expire_timer(void);
static void prv_quit_callback(void *data);
static void prv_cancel_quit_timer(void);
static void prv_set_backlight(bool on);
static void prv_update_backlight(void);


////////////////////////////////////////////////////////////////////////////////////////////////////
// Private Functions
//

// Callback for the backlight timer
static void prv_backlight_timer_callback(void *data) {
  backlight_timer = NULL;
  prv_update_backlight();
}

// Helper to set backlight state
static void prv_set_backlight(bool on) {
  // Cancel existing timer
  if (backlight_timer) {
    app_timer_cancel(backlight_timer);
    backlight_timer = NULL;
  }

  if (on != backlight_on) {
    backlight_on = on;
    light_enable(on);
    test_log_state("backlight_change");
  }

  if (on) {
    backlight_timer = app_timer_register(30000, prv_backlight_timer_callback, NULL);
  }
}

// Helper to check if currently in an edit mode
static bool prv_is_edit_mode(void) {
  return main_data.control_mode == ControlModeNew ||
         main_data.control_mode == ControlModeEditSec ||
         main_data.control_mode == ControlModeEditRepeat;
}

// Helper to update backlight based on state
static void prv_update_backlight(void) {
  prv_set_backlight(prv_is_edit_mode() || timer_is_vibrating());
}

// Common epilogue for interaction handlers: redraw, refresh the backlight to
// match the resulting mode, and log the new state for functional tests.
static void prv_finish_interaction(const char *log_tag) {
  drawing_update();
  layer_mark_dirty(main_data.layer);
  prv_update_backlight();
  test_log_state(log_tag);
}

// Helper to record interaction time
static void prv_record_interaction(void) {
  main_data.last_interaction_time = epoch();
  main_data.last_interaction_was_down = false;
  if (main_data.app_timer) {
    app_timer_reschedule(main_data.app_timer, 10);
  }
}

// Helper to update timer based on mode
static void prv_update_timer(int64_t increment) {
  if (main_data.is_reverse_direction) {
    increment = -increment;
  }
  if (main_data.is_editing_existing_timer && timer_data.base_length_ms == 0) {
    timer_increment_chrono(increment);
  } else {
    timer_increment(increment);
  }
}

// Check for zero-crossing and auto-flip direction to forward
static void prv_check_zero_crossing_direction_flip(bool was_chrono, int64_t increment) {
  if (was_chrono != timer_is_chrono()) {  // TODO: make this more clear. Does this mean if change crossed zero? if so, perhaps use a variable change_crossed_zero
    main_data.is_reverse_direction = false;
    // Normalize the timer's internal state to match the new type.
    // After timer_increment crosses zero, length_ms and start_ms may not
    // represent the new type correctly (e.g. negative length_ms for chrono).
    // We must fix this so that prv_new_expire_callback and
    // timer_check_elapsed work correctly when the timer starts running.
    //
    // Note: the timer may be running (not paused) during edit mode.
    // When running: start_ms = epoch start time, elapsed = epoch() - start_ms
    // When paused:  start_ms = elapsed time
    int64_t display_value = timer_get_value_ms();
    if (timer_is_chrono()) {
      // Chrono: length_ms=0, elapsed=display_value
      timer_data.length_ms = 0;
      if (!timer_data.is_paused) {
        timer_data.start_ms = epoch() - display_value;
      } else {
        timer_data.start_ms = display_value;
      }
      timer_data.can_vibrate = false;
      timer_data.base_length_ms = 0;
      main_data.is_editing_existing_timer = true;
    } else {
      // Countdown: normalize length_ms for header/base, and adjust start_ms
      // so the display value accounts for elapsed time.
      // length_ms = increment gives the correct header (e.g. 20:00).
      // start_ms is set so that length_ms - elapsed = display_value,
      // preserving the correct countdown display (e.g. 19:52 if 8s elapsed).
      if (main_data.is_editing_existing_timer) {
        timer_data.length_ms = increment;
        if (timer_data.is_paused) {
          timer_data.start_ms = increment - display_value;
        } else {
          timer_data.start_ms = epoch() - (increment - display_value);
        }
      } else {
        // New timer: keep start_ms as-is so elapsed time from app start
        // is deducted from the countdown value.
      }
      timer_data.can_vibrate = true;
      timer_data.base_length_ms = timer_data.length_ms;
    }
  }
}

// Apply an edit-mode increment: adjust the timer, auto-flip direction to
// forward on a zero crossing, and flag the length as modified so the new
// duration is committed when the edit expires (prv_new_expire_callback).
static void prv_apply_edit_increment(int64_t increment_ms) {
  bool was_chrono = timer_is_chrono();
  prv_update_timer(increment_ms);
  prv_check_zero_crossing_direction_flip(was_chrono, increment_ms);
  main_data.timer_length_modified_in_edit_mode = true;
}

// Callback to quit the app
static void prv_quit_callback(void *data) {
  main_data.quit_timer = NULL;
  window_stack_pop(true);
}

// Cancel the quit timer
static void prv_cancel_quit_timer(void) {
  if (main_data.quit_timer) {
    app_timer_cancel(main_data.quit_timer);
    main_data.quit_timer = NULL;
  }
}

// Helper to get last interaction time
uint64_t main_get_last_interaction_time(void) {
  return main_data.last_interaction_time;
}

// Callback for when the new timer expires
static void prv_new_expire_callback(void *data) {
  main_data.new_expire_timer = NULL;
  main_data.is_reverse_direction = false;
  if (main_data.control_mode == ControlModeNew || main_data.control_mode == ControlModeEditSec || main_data.control_mode == ControlModeEditRepeat) {
    // Track if we're coming from EditSec mode (sub-minute timer)
    bool was_edit_sec_mode = (main_data.control_mode == ControlModeEditSec);

    // Store the "base" duration in the persistent struct
    if (!main_data.is_editing_existing_timer || main_data.timer_length_modified_in_edit_mode) {
      if (timer_data.length_ms > 0) {
        timer_data.base_length_ms = timer_data.length_ms;
      } else {
        // It's a stopwatch (chrono), no base duration
        timer_data.base_length_ms = 0;
      }
    }

    if (main_data.control_mode == ControlModeEditRepeat) {
      timer_data.base_repeat_count = timer_data.repeat_count;
    }

    main_data.control_mode = ControlModeCounting;
    // Sub-minute timers (from EditSec mode) should stay paused and require manual start
    if (timer_is_paused() && !was_edit_sec_mode && !main_data.is_editing_existing_timer) {
      timer_toggle_play_pause();
    }
    if (backlight_on) {
      if (backlight_timer) {
        app_timer_cancel(backlight_timer);
      }
      backlight_timer = app_timer_register(BACKLIGHT_EDIT_LINGER_MS, prv_backlight_timer_callback, NULL);
    } else {
      prv_update_backlight();
    }
    test_log_state("mode_change");

    // Exit if timer is longer than AUTO_BACKGROUND_TIMER_LENGTH_MS, after a delay
    if (timer_data.length_ms > AUTO_BACKGROUND_TIMER_LENGTH_MS || (timer_is_chrono() && AUTO_BACKGROUND_CHRONO)) {
      main_data.quit_timer = app_timer_register(QUIT_DELAY_MS, prv_quit_callback, NULL);
    }
  }
}

// Stop the new expire timer
static void prv_stop_new_expire_timer(void) {
  if (main_data.new_expire_timer) {
    app_timer_cancel(main_data.new_expire_timer);
    main_data.new_expire_timer = NULL;
  }
}

// Reset the new expire timer
static void prv_reset_new_expire_timer(void) {
  // cancel previous timer
  if (main_data.new_expire_timer) {
    app_timer_cancel(main_data.new_expire_timer);
  }
  // create new timer
  main_data.new_expire_timer = app_timer_register(NEW_EXPIRE_TIME_MS, prv_new_expire_callback, NULL);
}



////////////////////////////////////////////////////////////////////////////////////////////////////
// Slot-Limit Warnings and Lap Flash
//

#if LAP_FEATURE
// Three short pulses: durations alternate on/off, so five 100ms segments
// produce on-off-on-off-on = three distinct buzzes.
static void prv_three_pulse_vibe(void) {
  static const uint32_t segments[] = {100, 100, 100, 100, 100};
  VibePattern pattern = {
    .durations = segments,
    .num_segments = ARRAY_LENGTH(segments),
  };
  vibes_enqueue_custom_pattern(pattern);
}

// Build the approaching-limit message, e.g. "3 slots left"
static void prv_format_slots_left(char *buf, size_t buf_size, uint8_t free_slots) {
  snprintf(buf, buf_size, "%u slot%s left", (unsigned)free_slots,
           free_slots == 1 ? "" : "s");
}

// Hide the warning overlay after WARNING_FEEDBACK_MS
static void prv_warning_hide_callback(void *data) {
  s_warning_timer = NULL;
  s_show_warning = false;
  main_force_redraw();
  TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:warning_dismiss,shown=0");
}

// Show a transient full-screen warning message with three short vibration pulses
static void prv_show_warning_overlay(const char *msg) {
  snprintf(s_warning_text, sizeof(s_warning_text), "%s", msg);
  s_show_warning = true;
  prv_three_pulse_vibe();
  main_force_redraw();
  if (s_warning_timer) {
    app_timer_cancel(s_warning_timer);
  }
  s_warning_timer = app_timer_register(WARNING_FEEDBACK_MS, prv_warning_hide_callback, NULL);
}
#endif  // LAP_FEATURE

// Get the warning message to draw instead of the timer view (NULL = none)
const char *main_get_warning_message(void) {
#if LAP_FEATURE
  if (s_show_warning) {
    return s_warning_text;
  }
  // During the lap flash near the slot limit, the "original" phase shows the
  // warning while the "lap" phase keeps flashing the paused lap slot
  if (main_data.flash_lap_slot >= 0 && main_data.flash_show_limit_warning &&
      !main_data.flash_showing_lap) {
    return s_warning_text;
  }
#endif
  return NULL;
}

// Notify that a new timer slot was created: warn when the limit is approached
void main_notify_timer_created(void) {
#if LAP_FEATURE
  uint8_t free_slots = MAX_TIMERS - timer_count;
  if (free_slots > 3) {
    return;
  }
  char msg[32];
  prv_format_slots_left(msg, sizeof(msg), free_slots);
  TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:limit_warning,src=timer,free=%u",
           (unsigned)free_slots);
  prv_show_warning_overlay(msg);
#endif
}

#if LAP_FEATURE
// Stop the lap flash: clear the render override and all flash state
static void prv_flash_cancel(void) {
  if (main_data.flash_timer) {
    app_timer_cancel(main_data.flash_timer);
    main_data.flash_timer = NULL;
  }
  main_data.flash_lap_slot = -1;
  main_data.flash_showing_lap = false;
  main_data.flash_show_limit_warning = false;
  drawing_set_slot_override(-1);
}

// Flip the flash between the lap slot and the original every FLASH_TICK_MS,
// stopping at the deadline or if the app left Counting mode
static void prv_flash_tick_callback(void *data) {
  main_data.flash_timer = NULL;
  if (main_data.flash_lap_slot < 0) {
    return;
  }
  if (epoch() >= main_data.flash_deadline_ms ||
      main_data.control_mode != ControlModeCounting) {
    int8_t slot = main_data.flash_lap_slot;
    prv_flash_cancel();
    TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:flash_end,slot=%d", (int)slot);
    main_force_redraw();
    return;
  }
  main_data.flash_showing_lap = !main_data.flash_showing_lap;
  drawing_set_slot_override(main_data.flash_showing_lap ? main_data.flash_lap_slot : -1);
  TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:flash_phase,lap=%d,slot=%d",
           main_data.flash_showing_lap ? 1 : 0, (int)main_data.flash_lap_slot);
  main_force_redraw();
  main_data.flash_timer = app_timer_register(FLASH_TICK_MS, prv_flash_tick_callback, NULL);
}

// Start (or restart) the lap flash for a freshly recorded lap slot
static void prv_flash_start(int8_t lap_slot) {
  main_data.flash_lap_slot = lap_slot;
  main_data.flash_deadline_ms = epoch() + FLASH_WINDOW_MS;
  main_data.flash_showing_lap = true;
  drawing_set_slot_override(lap_slot);
  main_force_redraw();
  if (main_data.flash_timer) {
    app_timer_cancel(main_data.flash_timer);
  }
  main_data.flash_timer = app_timer_register(FLASH_TICK_MS, prv_flash_tick_callback, NULL);
}

// Record a lap of the active timer and start the flash; at capacity, warn and
// leave the original running with its play/pause state unchanged
static void prv_record_lap(void) {
  // A Select during the flash window cancels it and records the next lap
  prv_flash_cancel();
  int8_t lap_slot = timer_slot_lap(timer_get_active_slot());
  if (lap_slot < 0) {
    TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:lap_full,free=0,p=%d",
             timer_is_paused() ? 1 : 0);
    prv_show_warning_overlay("No free slots");
    return;
  }
  uint8_t free_slots = MAX_TIMERS - timer_count;
  TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:lap_recorded,slot=%d,name=%s,free=%u,p=%d",
           (int)lap_slot, timer_slots[lap_slot].name, (unsigned)free_slots,
           timer_is_paused() ? 1 : 0);
  timer_persist_store();
  prv_flash_start(lap_slot);
  // Near the slot limit: vibrate and show the warning within the flash window
  if (free_slots <= 3) {
    prv_format_slots_left(s_warning_text, sizeof(s_warning_text), free_slots);
    main_data.flash_show_limit_warning = true;
    prv_three_pulse_vibe();
    TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:limit_warning,src=lap,free=%u",
             (unsigned)free_slots);
  }
}

// Back within the flash window opens the lap that was just recorded: cancel the
// flash and make the lap slot the active timer. Returns false when no flash is
// running, leaving Back to its usual behavior.
static bool prv_flash_view_lap(void) {
  if (main_data.flash_lap_slot < 0) {
    return false;
  }
  int8_t slot = main_data.flash_lap_slot;
  prv_flash_cancel();
  timer_set_active_slot((uint8_t)slot);
  TEST_LOG(APP_LOG_LEVEL_DEBUG, "TEST_STATE:flash_view_lap,slot=%d", (int)slot);
  return true;
}
#else
// Without the lap feature there is never a flash to cancel or a lap to view
#define prv_flash_cancel() ((void)0)
#define prv_flash_view_lap() (false)
#endif  // LAP_FEATURE

// Rewind timer if button is clicked to stop vibration
static bool prv_handle_alarm(void) {
  // check if timer is vibrating
  if (timer_is_vibrating()) {
    timer_data.can_vibrate = false;
    vibes_cancel();
    drawing_update();
    prv_update_backlight();
    test_log_state("alarm_stop");
    return true;
  }
  return false;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
// Callbacks
//

// Get the current control mode of the timer
ControlMode main_get_control_mode(void) {
  return main_data.control_mode;
}

// Get whether the app is currently editing an existing timer
bool main_is_editing_existing_timer(void) {
  return main_data.is_editing_existing_timer;
}

// Get whether the user has interacted with the app recently
bool main_is_interaction_active(void) {
  return (epoch() - main_data.last_interaction_time < INTERACTION_TIMEOUT_MS);
}

// Get whether the last interaction was a down button press
bool main_is_last_interaction_down(void) {
  return main_data.last_interaction_was_down;
}

// Get whether the app is in reverse direction mode
bool main_is_reverse_direction(void) {
  return main_data.is_reverse_direction;
}

// Get whether the backlight is currently on
bool main_is_backlight_on(void) {
  return backlight_on;
}

// Set the current control mode (called by Timer List window on selection)
void main_set_control_mode(ControlMode mode) {
  // The Timer List may switch the active slot; never leave a lap flash running
  prv_flash_cancel();
  main_data.control_mode = mode;
}

// Reset the new-expire timer (called by Timer List when entering edit mode)
void main_reset_new_expire_timer(void) {
  prv_reset_new_expire_timer();
}

// Force a redraw of the main window layer
void main_force_redraw(void) {
  drawing_update();
  layer_mark_dirty(main_data.layer);
}

// Background layer update procedure
static void prv_layer_update_proc_handler(Layer *layer, GContext *ctx) {
  // render the timer's visuals
  drawing_render(layer, ctx);
}

#ifdef PBL_MICROPHONE
// Dictation result callback. The SDK confirmation screen is disabled, so this
// runs the moment the transcription is ready: rename the active timer and give
// one short pulse. Failures leave the name alone; whether they buzz depends on
// who ended the session - if the user exited the dictation UI themselves they
// are already looking at the watch, so three pulses would just be noise.
static void prv_dictation_callback(DictationSession *session, DictationSessionStatus status,
                                   char *transcription, void *context) {
  switch (status) {
    case DictationSessionStatusSuccess:
      if (transcription != NULL) {
        timer_set_name(timer_get_active_slot(), transcription);
        vibes_short_pulse();
        main_force_redraw();
      }
      break;
    // The user exited the dictation UI: stay silent
    case DictationSessionStatusFailureTranscriptionRejected:
    case DictationSessionStatusFailureTranscriptionRejectedWithError:
      break;
    // Ended without the user dismissing anything: three pulses mean "nothing changed"
    case DictationSessionStatusFailureSystemAborted:
    case DictationSessionStatusFailureNoSpeechDetected:
    case DictationSessionStatusFailureConnectivityError:
    case DictationSessionStatusFailureDisabled:
    case DictationSessionStatusFailureInternalError:
    case DictationSessionStatusFailureRecognizerError:
      prv_three_pulse_vibe();
      break;
  }
}

// Hide the no-phone feedback icon and return to ControlModeEditSec, name unchanged
static void prv_no_phone_hide_callback(void *data) {
  s_no_phone_timer = NULL;
  s_show_no_phone = false;
  main_data.control_mode = ControlModeEditSec;
  main_force_redraw();
  test_log_state("voice_no_phone_dismiss");
}

// Show no-phone feedback: icon for ~1s plus three short vibration pulses
static void prv_show_no_phone_feedback(void) {
  s_show_no_phone = true;
  prv_three_pulse_vibe();
  main_force_redraw();
  test_log_state("voice_no_phone");
  if (s_no_phone_timer) {
    app_timer_cancel(s_no_phone_timer);
  }
  s_no_phone_timer = app_timer_register(NO_PHONE_FEEDBACK_MS, prv_no_phone_hide_callback, NULL);
}

// Launch a voice dictation session to rename the active timer
static void prv_start_voice_rename(void) {
  // Pre-check the phone connection; dictation needs the phone app. If it is not
  // connected (e.g. airplane mode), show feedback instead of silently failing.
  if (!connection_service_peek_pebble_app_connection()) {
    prv_show_no_phone_feedback();
    return;
  }
  if (!s_dictation_session) {
    s_dictation_session = dictation_session_create(64, prv_dictation_callback, NULL);
    if (!s_dictation_session) {
      return;
    }
    // No confirmation screen: the result callback fires as soon as the
    // transcription is ready and vibrates there. A wrong transcription is
    // corrected by simply repeating the rename gesture.
    dictation_session_enable_confirmation(s_dictation_session, false);
    dictation_session_enable_error_dialogs(s_dictation_session, true);
  }
  dictation_session_start(s_dictation_session);
}
#endif

// Report whether the no-phone feedback icon is currently being shown
bool main_is_showing_no_phone(void) {
#ifdef PBL_MICROPHONE
  return s_show_no_phone;
#else
  return false;
#endif
}

// Back click handler
static void prv_back_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
#ifdef PBL_MICROPHONE
  // Up+Back chord (Up pressed first) launches voice rename when enabled
  if ((main_data.control_mode == ControlModeEditSec || main_data.control_mode == ControlModeNew)
      && s_up_held && settings_get_voice_naming_enabled()) {
    s_up_chord_consumed = true;
    prv_start_voice_rename();
    test_log_state("button_back");
    return;
  }
#endif
  if (main_data.control_mode == ControlModeNew) {
    if (settings_get_swap_back_and_select_long()) {
      main_data.control_mode = ControlModeEditSec;
    } else {
      prv_apply_edit_increment(BACK_BUTTON_INCREMENT_MS);
    }
  } else if (main_data.control_mode == ControlModeEditSec) {
    if (settings_get_swap_back_and_select_long()) {
      main_data.control_mode = ControlModeNew;
    } else {
      prv_apply_edit_increment(BACK_BUTTON_INCREMENT_SEC_MS);
    }
  } else if (main_data.control_mode == ControlModeEditRepeat) {
    timer_data.repeat_count = 0;
    prv_reset_new_expire_timer();
  } else {
    // view the lap just recorded, else silence the alarm, or quit if no alarm
    if (!prv_flash_view_lap() && !prv_handle_alarm()) {
      window_stack_pop(true);
    }
  }
  prv_finish_interaction("button_back");
}

// Up click handler
static void prv_up_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  if (s_up_chord_consumed) {
    s_up_chord_consumed = false;
    return;
  }
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
 if (timer_is_vibrating()) {
    prv_handle_alarm();
  }

  // If timer is counting (but not vibrating), go to edit mode.
  if (main_data.control_mode == ControlModeCounting) {
    prv_flash_cancel();
    main_data.is_reverse_direction = false;
    if (timer_get_value_ms() == 0 && timer_is_paused()) {
      main_data.control_mode = ControlModeEditSec;
      prv_stop_new_expire_timer();
    } else {
      main_data.control_mode = ControlModeNew;
    }
    main_data.is_editing_existing_timer = true;
    main_data.timer_length_modified_in_edit_mode = false;
    prv_finish_interaction("button_up");
    return;
  }
  // increment repeats
  if (main_data.control_mode == ControlModeEditRepeat) {
    timer_data.repeat_count += 20;
    prv_reset_new_expire_timer();
    prv_finish_interaction("button_up");
    return;
  }
  // increment timer
  int64_t increment = UP_BUTTON_INCREMENT_MS;
  if (main_data.control_mode == ControlModeEditSec) {
    increment = UP_BUTTON_INCREMENT_SEC_MS;
  }
  // increment timer
  prv_apply_edit_increment(increment);
  prv_finish_interaction("button_up");
}

// Up long click handler
static void prv_up_long_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();

  if (timer_is_vibrating()) {
    // Check if we have a "base" duration to restart from
    if (timer_data.base_length_ms > 0) {
      APP_LOG(APP_LOG_LEVEL_DEBUG, "Up long press: Restarting %lld ms timer.", (long long)timer_data.base_length_ms);
      vibes_cancel(); // Stop the alarm vibration
      if (timer_data.is_repeating) {
        // Restart the full repeating timer, repeats included
        timer_data.repeat_count = timer_data.base_repeat_count;
      }
      timer_repeat_restart();
      test_log_state("alarm_stop");
    }
    prv_finish_interaction("long_press_up");
    return;
  }

  // In counting mode, toggle repeat on/off
  if (main_data.control_mode == ControlModeCounting) {
    // No effect in chrono mode (spec 2.6)
    if (timer_is_chrono()) {
      test_log_state("long_press_up");
      return;
    }
    timer_data.is_repeating = !timer_data.is_repeating;
    if (timer_data.is_repeating) {
      timer_data.repeat_count = 0;
      main_data.control_mode = ControlModeEditRepeat;
      prv_reset_new_expire_timer();
    } else {
      timer_data.repeat_count = 0;
      timer_data.base_repeat_count = 0;
      main_data.control_mode = ControlModeCounting;
    }
    vibes_short_pulse();
    prv_finish_interaction("long_press_up");
    return;
  }

  // In edit modes, toggle reverse direction
  main_data.is_reverse_direction = !main_data.is_reverse_direction;
  vibes_short_pulse();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Reverse direction: %d", main_data.is_reverse_direction);

  prv_reset_new_expire_timer();
  prv_finish_interaction("long_press_up");
}

// Select click handler
static void prv_select_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  if (prv_handle_alarm()) {
    if (main_data.control_mode == ControlModeCounting) {
      timer_toggle_play_pause();
    }
    prv_update_backlight();
    test_log_state("button_select");
    return;
  }
  // change timer mode
  int64_t increment = SELECT_BUTTON_INCREMENT_MS;
  switch (main_data.control_mode) {
    case ControlModeEditHr:
      break;
    case ControlModeEditMin:
      break;
    case ControlModeEditSec: {
      prv_apply_edit_increment(SELECT_BUTTON_INCREMENT_SEC_MS);
      break;
    }
    case ControlModeEditRepeat:
      timer_data.repeat_count += 5;
      prv_reset_new_expire_timer();
      break;
    case ControlModeCounting:
#if LAP_FEATURE
      // Lap Stopwatch: Select on a running timer records a lap instead of
      // pausing (a Select during the flash window re-laps immediately)
      if (settings_get_lap_stopwatch_enabled() && !timer_is_paused()) {
        prv_record_lap();
        break;
      }
#endif
      timer_toggle_play_pause();
      break;
    case ControlModeNew: {
      prv_apply_edit_increment(increment);
      break;
    }
  }
  // refresh
  prv_finish_interaction("button_select");
}

// Select raw click handler
static void prv_select_raw_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  // stop vibration
  prv_handle_alarm();
  // animate and refresh
  drawing_start_reset_animation();
  layer_mark_dirty(main_data.layer);
}

// Select long click handler
static void prv_select_long_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();

  // EditSec: toggle to New mode (or add time if swap is on)
  if (main_data.control_mode == ControlModeEditSec) {
    if (settings_get_swap_back_and_select_long()) {
      prv_apply_edit_increment(BACK_BUTTON_INCREMENT_SEC_MS);
    } else {
      main_data.control_mode = ControlModeNew;
    }
    prv_finish_interaction("long_press_select");
    return;
  }

  // EditRepeat: no-op
  if (main_data.control_mode == ControlModeEditRepeat) {
    main_data.is_reverse_direction = false;
    prv_finish_interaction("long_press_select");
    return;
  }

  // New: toggle to EditSec mode (or add time if swap is on)
  if (main_get_control_mode() == ControlModeNew) {
    if (settings_get_swap_back_and_select_long()) {
      prv_apply_edit_increment(BACK_BUTTON_INCREMENT_MS);
    } else {
      main_data.control_mode = ControlModeEditSec;
    }
    prv_finish_interaction("long_press_select");
    return;
  }

  main_data.is_reverse_direction = false;
  if (main_data.control_mode == ControlModeCounting) {
    prv_flash_cancel();
    if (timer_data.is_paused) {
      // Paused: reset to 0:00 and enter EditSec
      timer_reset();
      timer_data.start_ms = 0;
      timer_data.is_paused = true;
      main_data.control_mode = ControlModeEditSec;
      prv_stop_new_expire_timer();
      main_data.is_editing_existing_timer = false;
      main_data.timer_length_modified_in_edit_mode = false;
    } else {
      // Running: restart as before
      timer_restart();
#if LAP_FEATURE
      if (settings_get_lap_stopwatch_enabled() && timer_is_chrono()) {
        // Lap Stopwatch: restarting a stopwatch also resets the lap session
        // (next lap is "Lap 1") and assigns a new name. Previously recorded
        // lap slots are independent copies and stay untouched. A stopwatch the
        // user has renamed keeps its custom name across the restart.
        timer_data.last_lap_ms = 0;
        timer_data.lap_count = 0;
        if (!timer_data.has_custom_name) {
          timer_assign_name(timer_get_active_slot());
        }
      }
#endif
      vibes_short_pulse();
      main_data.timer_length_modified_in_edit_mode = false;
    }
  } else {
    timer_reset();
    main_data.control_mode = ControlModeNew;
    main_data.is_editing_existing_timer = false;
    main_data.timer_length_modified_in_edit_mode = false;
  }
  // animate and refresh
  prv_finish_interaction("long_press_select");
}

// Helper to check if we should extend high refresh rate for down button
static void prv_check_down_button_extended_refresh(void) {
  // If timer is paused (e.g. editing mode), we don't extend the refresh rate
  // because the timer value isn't changing, which would lead to infinite high refresh.
  if (timer_is_paused()) {
    return;
  }

  int64_t val = timer_get_value_ms();
  bool near_minute = false;

  // Calculate distance to the next minute boundary (end of current minute)
  if (timer_is_chrono()) {
    // Counting up: Boundary is next multiple of 60s
    // Distance = 60000 - (val % 60000)
    if ((MSEC_IN_MIN - (val % MSEC_IN_MIN)) <= 3000) {
      near_minute = true;
    }
  } else {
    // Counting down: Boundary is 00 seconds (val % 60000 == 0)
    // Distance = val % 60000
    if ((val % MSEC_IN_MIN) <= 3000) {
      near_minute = true;
    }
  }

  // If we are close to the minute boundary (<= 3 seconds), the standard 10s interaction timeout
  // is sufficient and prevents the refresh from cutting off too early.
  // Otherwise, we set the flag to extend the high refresh rate until the minute boundary.
  if (!near_minute) {
    main_data.last_interaction_was_down = true;
  }
}

// Down click handler
static void prv_down_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  if (timer_is_vibrating()) {
    vibes_cancel();
    if (timer_data.is_repeating && timer_data.repeat_count > 1) {
      // Intermediate alarm: just restart the timer (no snooze)
      timer_data.repeat_count--;
      timer_repeat_restart();
      test_log_state("alarm_stop");
    } else {
      // Final alarm or non-repeating: normal snooze
      timer_increment(SNOOZE_INCREMENT_MS);
      test_log_state("alarm_stop");
    }
    prv_finish_interaction("button_down");
    return;
  }
  else if (main_data.control_mode == ControlModeCounting) {
    prv_check_down_button_extended_refresh();
    test_log_state("button_down");
  }
  else if (main_data.control_mode == ControlModeNew) {
    int64_t increment = DOWN_BUTTON_INCREMENT_MS;
    prv_apply_edit_increment(increment);
    prv_finish_interaction("button_down");
  }
  else if (main_data.control_mode == ControlModeEditSec) {
    int64_t increment = DOWN_BUTTON_INCREMENT_SEC_MS;
    prv_apply_edit_increment(increment);
    prv_finish_interaction("button_down");
  }
  else if (main_data.control_mode == ControlModeEditRepeat) {
    timer_data.repeat_count += 1;
    prv_reset_new_expire_timer();
    prv_finish_interaction("button_down");
  }
}

// Down long click handler
static void prv_down_long_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  timer_reset_auto_snooze();
  // Delete this timer slot and exit
  timer_slot_delete(timer_get_active_slot());
  prv_update_backlight();
  test_log_state("long_press_down");
  // quit app
  window_stack_pop(true);
}

// Up raw down click handler
static void prv_up_raw_down_handler(ClickRecognizerRef recognizer, void *ctx) {
  s_up_held = true;
  prv_record_interaction();
  prv_stop_new_expire_timer();
}

// Up raw up handler (clears held flag)
static void prv_up_raw_up_handler(ClickRecognizerRef recognizer, void *ctx) {
  s_up_held = false;
}

static void prv_down_raw_down_handler(ClickRecognizerRef recognizer, void *ctx) {
}

// Click configuration provider
static void prv_click_config_provider(void *ctx) {
  window_single_click_subscribe(BUTTON_ID_BACK, prv_back_click_handler);
  window_single_click_subscribe(BUTTON_ID_UP, prv_up_click_handler);
  window_raw_click_subscribe(BUTTON_ID_UP, prv_up_raw_down_handler, prv_up_raw_up_handler, NULL);
  window_long_click_subscribe(BUTTON_ID_UP, BUTTON_HOLD_RESET_MS, prv_up_long_click_handler, NULL);
  window_single_click_subscribe(BUTTON_ID_SELECT, prv_select_click_handler);
  window_raw_click_subscribe(BUTTON_ID_SELECT, prv_select_raw_click_handler, NULL, NULL);
  window_long_click_subscribe(BUTTON_ID_SELECT, BUTTON_HOLD_RESET_MS, prv_select_long_click_handler,
    NULL);
  window_single_click_subscribe(BUTTON_ID_DOWN, prv_down_click_handler);
  window_raw_click_subscribe(BUTTON_ID_DOWN, prv_down_raw_down_handler, NULL, NULL); // POC
  window_long_click_subscribe(BUTTON_ID_DOWN, BUTTON_HOLD_RESET_MS, prv_down_long_click_handler, NULL);
}

// AppTimer callback
static void prv_app_timer_callback(void *data) {
  bool was_elapsed = timer_data.elapsed;
  // check if timer is complete
  timer_check_elapsed();
  bool is_elapsed = timer_data.elapsed;

  if (!was_elapsed && is_elapsed) {
    prv_update_backlight();
    test_log_state("alarm_start");
  } else if (was_elapsed && !is_elapsed) {
    prv_update_backlight();
    test_log_state("alarm_stop");
  }

  // refresh
  drawing_update();
  layer_mark_dirty(main_data.layer);
  // schedule next call
  main_data.app_timer = NULL;
  if (main_data.control_mode == ControlModeCounting || main_data.control_mode == ControlModeNew || main_data.control_mode == ControlModeEditSec || main_data.control_mode == ControlModeEditRepeat) {
    uint32_t duration;
    int64_t val = timer_get_value_ms();

#if REDUCE_SCREEN_UPDATES
    if (val > 5 * MSEC_IN_MIN) {
       // Update at next minute boundary
       duration = val % MSEC_IN_MIN;
    } else if (val >= 30 * MSEC_IN_SEC) {
       // Update at next 10s boundary
       duration = val % (10 * MSEC_IN_SEC);
    } else {
       // Normal update
       duration = val % MSEC_IN_SEC;
    }

    // Force high refresh rate if user recently interacted or down button extended logic
    bool high_refresh = (epoch() - main_data.last_interaction_time < INTERACTION_TIMEOUT_MS);

    // If the Down button was pressed, we extend the high refresh rate until the end of the current minute.
    // We clear the flag when we reach the minute boundary (tolerance of < 500ms).
    if (main_data.last_interaction_was_down) {
      uint32_t remainder = val % MSEC_IN_MIN;
      if (remainder < 500 || remainder > MSEC_IN_MIN - 500) {
        main_data.last_interaction_was_down = false;
      } else {
        high_refresh = true;
      }
    }

    if (high_refresh) {
      duration = val % MSEC_IN_SEC;
    }
#else
    duration = val % MSEC_IN_SEC;
#endif

    if (timer_is_chrono()) {
      // For chrono, we want to align to the next boundary upwards
      // If duration was "time past the boundary" (remainder),
      // we need "time until next boundary".
      // For countdown, remainder is exactly what we want to wait to reach the next lower boundary.
      // For chrono, we want (Interval - Remainder).

      // Re-calculate interval based on mode
#if REDUCE_SCREEN_UPDATES
      // Let's recalculate duration from scratch for chrono to be safe and clean.
      // Re-evaluate high_refresh logic for Chrono as well
      bool high_refresh_chrono = (epoch() - main_data.last_interaction_time < INTERACTION_TIMEOUT_MS);
      // Same extended logic for Chrono mode
      if (main_data.last_interaction_was_down) {
         // For chrono, val increases. If val is slightly above minute boundary, we clear.
         // val % 60000 being small means we just passed minute mark.
         uint32_t remainder = val % MSEC_IN_MIN;
         if (remainder < 500 || remainder > MSEC_IN_MIN - 500) {
            main_data.last_interaction_was_down = false;
         } else {
            high_refresh_chrono = true;
         }
      }

      if (high_refresh_chrono) {
         duration = MSEC_IN_SEC - (val % MSEC_IN_SEC);
      } else if (val > 5 * MSEC_IN_MIN) {
         duration = MSEC_IN_MIN - (val % MSEC_IN_MIN);
      } else if (val >= 30 * MSEC_IN_SEC) {
         duration = (10 * MSEC_IN_SEC) - (val % (10 * MSEC_IN_SEC));
      } else {
         duration = MSEC_IN_SEC - (val % MSEC_IN_SEC);
      }
#else
      duration = MSEC_IN_SEC - duration;
#endif
    }

    if (main_data.control_mode == ControlModeEditRepeat) {
      duration = 100;
    }

    main_data.app_timer = app_timer_register(duration + 5, prv_app_timer_callback, NULL);
  }
}

// TickTimerService callback
static void prv_tick_timer_service_callback(struct tm *tick_time, TimeUnits units_changed) {
  // refresh
  layer_mark_dirty(main_data.layer);
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Loading and Unloading
//

static void prv_settings_changed(void) {
  drawing_update();
  layer_mark_dirty(main_data.layer);
}

// Initialize the program
static void prv_initialize(void) {
  // cancel any existing wakeup events
  wakeup_cancel_all();
  // load timer and settings
  timer_persist_read();
  uint8_t persisted_count = timer_count;

  // If launched by a wakeup, restore the slot that scheduled the alarm and skip the timer list
  bool wakeup_launch = (launch_reason() == APP_LAUNCH_WAKEUP);
  if (wakeup_launch && timer_count > 0) {
    WakeupId wakeup_id;
    int32_t wakeup_cookie = 0;
    wakeup_get_launch_event(&wakeup_id, &wakeup_cookie);
    if (wakeup_cookie >= 0 && (uint8_t)wakeup_cookie < timer_count) {
      timer_set_active_slot((uint8_t)wakeup_cookie);
    }
  }

#if LAP_FEATURE
  // no lap flash active on launch
  main_data.flash_lap_slot = -1;
#endif

  settings_init(prv_settings_changed);
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Timer data: length_ms=%lld, start_ms=%lld, is_paused=%d, can_vibrate=%d",
          (long long)timer_data.length_ms, (long long)timer_data.start_ms, timer_data.is_paused, timer_data.can_vibrate);
  // set initial states
  if (timer_data.reset_on_init) {
    // Check if timer needs to be reset from a previous long press
    main_data.control_mode = ControlModeNew;
    timer_reset();
    // Start timer running immediately in ControlModeNew
    // This allows the timer to count while user is adding time
    timer_data.start_ms = epoch();
    timer_data.is_paused = false;
    timer_data.reset_on_init = false;
    main_data.is_editing_existing_timer = false;
    vibes_short_pulse();
    main_data.timer_length_modified_in_edit_mode = false;
  } else if (timer_data.length_ms) {
    // A timer was set (counting down), so resume in counting mode
    main_data.control_mode = ControlModeCounting;
    main_data.is_editing_existing_timer = false;
    main_data.timer_length_modified_in_edit_mode = false;
  } else if (timer_is_chrono() && (!timer_data.is_paused || timer_data.start_ms > 0)) {
    // Chrono mode was active (counting up), so resume in counting mode
    // Exclude freshly-reset state (is_paused=true, start_ms=0) which also
    // satisfies timer_is_chrono() since 0-0<=0, but is not an active chrono
    main_data.control_mode = ControlModeCounting;
    main_data.is_editing_existing_timer = false;
    main_data.timer_length_modified_in_edit_mode = false;
  } else {
    // No timer was set and it wasn't in chrono mode, so start fresh
    main_data.control_mode = ControlModeNew;
    timer_reset();
    // Formally claim slot 0 so this timer is persisted on exit
    if (timer_count == 0) timer_count = 1;
    // Start timer running immediately in ControlModeNew
    // This allows the timer to count while user is adding time
    timer_data.start_ms = epoch();
    timer_data.is_paused = false;
    main_data.is_editing_existing_timer = false;
    vibes_short_pulse();
    main_data.timer_length_modified_in_edit_mode = false;
    timer_assign_name(timer_get_active_slot());
  }
  prv_reset_new_expire_timer();
  prv_update_backlight();
  test_log_state("init");

  // If multi-timer enabled and timers existed before this launch, push the Timer List.
  // Skip the list on wakeup launches — go straight to the alarming timer.
  bool show_timer_list = !wakeup_launch && settings_get_multiple_timers_enabled() && persisted_count > 0;

  // initialize window
  main_data.window = window_create();
  ASSERT(main_data.window);
  window_set_click_config_provider(main_data.window, prv_click_config_provider);
  Layer *window_root = window_get_root_layer(main_data.window);
  GRect window_bounds = layer_get_bounds(window_root);
#ifdef PBL_SDK_2
  window_set_fullscreen(main_data.window, true);
  window_bounds.size.h = 168;
#endif
  window_stack_push(main_data.window, true);
  // initialize main layer
  main_data.layer = layer_create(window_bounds);
  ASSERT(main_data.layer);
  layer_set_update_proc(main_data.layer, prv_layer_update_proc_handler);
  layer_add_child(window_root, main_data.layer);

  // initialize drawing singleton
  drawing_initialize(main_data.layer);
  // subscribe to tick timer service
  tick_timer_service_subscribe(MINUTE_UNIT, prv_tick_timer_service_callback);
  // start refreshing
  prv_record_interaction();
  prv_app_timer_callback(NULL);

  // Push Timer List on top when multiple timers exist and feature is enabled
  if (show_timer_list) {
    timer_list_window_push();
  }
}

// Terminate the program
static void prv_terminate(void) {
  // unsubscribe from timer service
  tick_timer_service_unsubscribe();
  // stop any active lap flash and warning overlay
  prv_flash_cancel();
#if LAP_FEATURE
  if (s_warning_timer) {
    app_timer_cancel(s_warning_timer);
    s_warning_timer = NULL;
  }
#endif
  // cancel backlight timer
  if (backlight_timer) {
    app_timer_cancel(backlight_timer);
    backlight_timer = NULL;
  }
  // schedule wakeup for the active countdown timer (if any)
  if (timer_count > 0 && !timer_is_chrono() && !timer_is_paused() && !timer_data.reset_on_init) {
    time_t wakeup_time = (epoch() + timer_get_value_ms()) / MSEC_IN_SEC;
    wakeup_schedule(wakeup_time, (int32_t)timer_get_active_slot(), true);
  }
  // destroy
#ifdef PBL_MICROPHONE
  if (s_dictation_session) {
    dictation_session_destroy(s_dictation_session);
    s_dictation_session = NULL;
  }
#endif
  timer_persist_store();
  drawing_terminate();
  layer_destroy(main_data.layer);
  window_destroy(main_data.window);
}

// Entry point
int main(void) {
  prv_initialize();
  app_event_loop();
  prv_terminate();
  return 0;
}
