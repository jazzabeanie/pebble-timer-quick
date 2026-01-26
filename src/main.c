// @file main.c
// @brief Main logic for Timer++
//
// Contains the higher level logic code
//
// @author Eric D. Phillips & Jared Johnston
// @date November 11, 2025
// @bugs No known bugs

#include <pebble.h>
#include "main.h"
#include "drawing.h"
#include "timer.h"
#include "utility.h"

// Main constants
#define AUTO_BACKGROUND_TIMER_LENGTH_MS (MSEC_IN_MIN * 20)
#define AUTO_BACKGROUND_CHRONO 1
#define QUIT_DELAY_MS 7000
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
  } main_data;

// Function declarations
static void prv_app_timer_callback(void *data);
static void prv_new_expire_callback(void *data);
static void prv_reset_new_expire_timer(void);
static void prv_quit_callback(void *data);
static void prv_cancel_quit_timer(void);


////////////////////////////////////////////////////////////////////////////////////////////////////
// Private Functions
//

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
  if (main_data.is_editing_existing_timer && timer_is_chrono()) {
    timer_increment_chrono(increment);
  } else {
    timer_increment(increment);
  }
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
    // previous code before merge:
    //  // Store the "base" duration in the persistent struct
    //  if (timer_data.length_ms > 0) {
    //    timer_data.base_length_ms = timer_data.length_ms;
    //  } else {
    //    // It's a stopwatch (chrono), no base duration
    //    timer_data.base_length_ms = 0;
    //  }

    // Store the "base" duration in the persistent struct
    if (!main_data.is_editing_existing_timer || main_data.timer_length_modified_in_edit_mode) {
      if (timer_data.length_ms > 0) {
        timer_data.base_length_ms = timer_data.length_ms;
      } else {
        // It's a stopwatch (chrono), no base duration
        timer_data.base_length_ms = 0;
      }
    }
    main_data.control_mode = ControlModeCounting;

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

// Rewind timer if button is clicked to stop vibration
static bool prv_handle_alarm(void) {
  // check if timer is vibrating
  if (timer_is_vibrating()) {
    APP_LOG(APP_LOG_LEVEL_DEBUG, "Cancelling vibration");
    timer_data.can_vibrate = false;
    vibes_cancel();
    drawing_update();
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

// Background layer update procedure
static void prv_layer_update_proc_handler(Layer *layer, GContext *ctx) {
  // render the timer's visuals
  drawing_render(layer, ctx);
}

// Back click handler
static void prv_back_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Back button pressed");
  if (main_data.control_mode == ControlModeNew) {
    // increment timer by 1 hour
    prv_update_timer(BACK_BUTTON_INCREMENT_MS);
    main_data.timer_length_modified_in_edit_mode = true;
  } else if (main_data.control_mode == ControlModeEditSec) {
    // increment timer by 30 seconds
    prv_update_timer(BACK_BUTTON_INCREMENT_SEC_MS);
    main_data.timer_length_modified_in_edit_mode = true;
  } else if (main_data.control_mode == ControlModeEditRepeat) {
    timer_data.repeat_count = 1;
    prv_reset_new_expire_timer();
  } else {
    // silence the alarm, or quit if no alarm
    if (!prv_handle_alarm()) {
      window_stack_pop(true);
    }
  }
  drawing_update();
  layer_mark_dirty(main_data.layer);
}

// Up click handler
static void prv_up_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Up button handler");
 if (timer_is_vibrating()) {
    prv_handle_alarm();
  }

  // If timer is counting (but not vibrating), go to edit mode.
  if (main_data.control_mode == ControlModeCounting) {
    main_data.is_reverse_direction = false;
    if (timer_get_value_ms() == 0 && timer_is_paused()) {
      main_data.control_mode = ControlModeEditSec;
      prv_stop_new_expire_timer();
    } else {
      main_data.control_mode = ControlModeNew;
    }
    main_data.is_editing_existing_timer = true;
    main_data.timer_length_modified_in_edit_mode = false;
    drawing_update();
    layer_mark_dirty(main_data.layer);
    return;
  }
  // increment repeats
  if (main_data.control_mode == ControlModeEditRepeat) {
    timer_data.repeat_count += 20;
    prv_reset_new_expire_timer();
    drawing_update();
    layer_mark_dirty(main_data.layer);
    return;
  }
  // increment timer
  int64_t increment = UP_BUTTON_INCREMENT_MS;
  if (main_data.control_mode == ControlModeEditSec) {
    increment = UP_BUTTON_INCREMENT_SEC_MS;
  }
  // increment timer
  prv_update_timer(increment);
  main_data.timer_length_modified_in_edit_mode = true;
  drawing_update();
  layer_mark_dirty(main_data.layer);
}

// Up long click handler
static void prv_up_long_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Up long press");

  if (timer_is_vibrating()) {
    // Check if we have a "base" duration to add
    if (timer_data.base_length_ms > 0) {
      APP_LOG(APP_LOG_LEVEL_DEBUG, "Up long press: Extending timer by %lld ms.", timer_data.base_length_ms);
      vibes_cancel(); // Stop the alarm vibration
      timer_data.is_repeating = false;
      timer_data.repeat_count = 0;
      timer_increment(timer_data.base_length_ms); // Add the base duration
    }
    drawing_update();
    layer_mark_dirty(main_data.layer);
    return;
  }

  // In counting mode, toggle repeat on/off
  if (main_data.control_mode == ControlModeCounting) {
    // No effect in chrono mode (spec 2.6)
    if (timer_is_chrono()) {
      return;
    }
    timer_data.is_repeating = !timer_data.is_repeating;
    if (timer_data.is_repeating) {
      timer_data.repeat_count = 2;
      main_data.control_mode = ControlModeEditRepeat;
      prv_reset_new_expire_timer();
    } else {
      timer_data.repeat_count = 0;
      main_data.control_mode = ControlModeCounting;
    }
    vibes_short_pulse();
    drawing_update();
    layer_mark_dirty(main_data.layer);
    return;
  }

  // In edit modes, toggle reverse direction
  main_data.is_reverse_direction = !main_data.is_reverse_direction;
  vibes_short_pulse();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Reverse direction: %d", main_data.is_reverse_direction);

  prv_reset_new_expire_timer();
  drawing_update();
  layer_mark_dirty(main_data.layer);
}

// Select click handler
static void prv_select_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Select button pressed");
  if (prv_handle_alarm()) {
    if (main_data.control_mode == ControlModeCounting) {
      timer_toggle_play_pause();
    }
    return;
  }
  // change timer mode
  int64_t increment = SELECT_BUTTON_INCREMENT_MS;
  switch (main_data.control_mode) {
    case ControlModeEditHr:
      break;
    case ControlModeEditMin:
      break;
    case ControlModeEditSec:
      prv_update_timer(SELECT_BUTTON_INCREMENT_SEC_MS);
      break;
    case ControlModeEditRepeat:
      timer_data.repeat_count += 5;
      prv_reset_new_expire_timer();
      break;
    case ControlModeCounting:
      timer_toggle_play_pause();
      break;
    case ControlModeNew:
      prv_update_timer(increment);
      main_data.timer_length_modified_in_edit_mode = true;
      break;
  }
  // refresh
  drawing_update();
  layer_mark_dirty(main_data.layer);
}

// Select raw click handler
static void prv_select_raw_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  prv_reset_new_expire_timer();
  timer_reset_auto_snooze();
  // stop vibration
  vibes_cancel();
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
  main_data.is_reverse_direction = false;
  if (main_data.control_mode == ControlModeCounting) {
    if (timer_is_chrono()) {
      if (timer_is_paused()) {
        // Paused Chrono -> Paused New Timer (0:00) -> Edit Seconds
        timer_reset();
        timer_data.start_ms = 0; // Pause it
        main_data.control_mode = ControlModeEditSec;
        prv_stop_new_expire_timer();
      } else {
        // Running Chrono -> Counting New Timer (0:00)
        timer_reset();
        // timer_reset sets start_ms to epoch(), so it starts running
        main_data.control_mode = ControlModeCounting;
      }
    } else {
      timer_restart();
    }
  } else {
    timer_reset();
    main_data.control_mode = ControlModeNew;
    main_data.is_editing_existing_timer = false;
  }
  main_data.timer_length_modified_in_edit_mode = false;
  // animate and refresh
  drawing_update();
  layer_mark_dirty(main_data.layer);
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
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Down button pressed");
  if (timer_is_vibrating()) {
    vibes_cancel();
    if (timer_data.is_repeating && timer_data.repeat_count > 1) {
      // Intermediate alarm: just restart the timer (no snooze)
      timer_data.repeat_count--;
      timer_increment(timer_data.base_length_ms);
    } else {
      // Final alarm or non-repeating: normal snooze
      timer_increment(SNOOZE_INCREMENT_MS);
    }
    drawing_update();
    layer_mark_dirty(main_data.layer);
    return;
  }
  else if (main_data.control_mode == ControlModeCounting) {
    prv_check_down_button_extended_refresh();
  }
  else if (main_data.control_mode == ControlModeNew) {
    int64_t increment = DOWN_BUTTON_INCREMENT_MS;
    prv_update_timer(increment);
    main_data.timer_length_modified_in_edit_mode = true;
    drawing_update();
    layer_mark_dirty(main_data.layer);
  }
  else if (main_data.control_mode == ControlModeEditSec) {
    int64_t increment = DOWN_BUTTON_INCREMENT_SEC_MS;
    prv_update_timer(increment);
    main_data.timer_length_modified_in_edit_mode = true;
    drawing_update();
    layer_mark_dirty(main_data.layer);
  }
  else if (main_data.control_mode == ControlModeEditRepeat) {
    timer_data.repeat_count += 1;
    prv_reset_new_expire_timer();
    drawing_update();
    layer_mark_dirty(main_data.layer);
  }
}

// Down long click handler
static void prv_down_long_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_cancel_quit_timer();
  timer_reset_auto_snooze();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Down long press");
  // Reset timer
  timer_data.reset_on_init = true;
  // quit app
  window_stack_pop(true);
}

// Up raw down click handler
static void prv_up_raw_down_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_record_interaction();
  prv_stop_new_expire_timer();
}

// Click configuration provider
static void prv_click_config_provider(void *ctx) {
  window_single_click_subscribe(BUTTON_ID_BACK, prv_back_click_handler);
  window_single_click_subscribe(BUTTON_ID_UP, prv_up_click_handler);
  window_raw_click_subscribe(BUTTON_ID_UP, prv_up_raw_down_handler, NULL, NULL);
  window_long_click_subscribe(BUTTON_ID_UP, BUTTON_HOLD_RESET_MS, prv_up_long_click_handler, NULL);
  window_single_click_subscribe(BUTTON_ID_SELECT, prv_select_click_handler);
  window_raw_click_subscribe(BUTTON_ID_SELECT, prv_select_raw_click_handler, NULL, NULL);
  window_long_click_subscribe(BUTTON_ID_SELECT, BUTTON_HOLD_RESET_MS, prv_select_long_click_handler,
    NULL);
  window_single_click_subscribe(BUTTON_ID_DOWN, prv_down_click_handler);
  window_long_click_subscribe(BUTTON_ID_DOWN, BUTTON_HOLD_RESET_MS, prv_down_long_click_handler, NULL);
}

// AppTimer callback
static void prv_app_timer_callback(void *data) {
  // check if timer is complete
  timer_check_elapsed();
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

// Initialize the program
static void prv_initialize(void) {
  // cancel any existing wakeup events
  wakeup_cancel_all();
  // load timer
  timer_persist_read();
  APP_LOG(APP_LOG_LEVEL_DEBUG, "Timer data: length_ms=%lld, start_ms=%lld, elapsed=%d, can_vibrate=%d",
          timer_data.length_ms, timer_data.start_ms, timer_data.elapsed, timer_data.can_vibrate);
  // set initial states
  if (timer_data.reset_on_init) {
    // Check if timer needs to be reset from a previous long press
    main_data.control_mode = ControlModeNew;
    timer_reset();
    timer_data.reset_on_init = false;
    main_data.is_editing_existing_timer = false;
    vibes_short_pulse();
    main_data.timer_length_modified_in_edit_mode = false;
  } else if (timer_data.length_ms) {
    // A timer was set (counting down), so resume in counting mode
    main_data.control_mode = ControlModeCounting;
    main_data.is_editing_existing_timer = false;
    main_data.timer_length_modified_in_edit_mode = false;
  } else if (timer_is_chrono()) {
    // Chrono mode was active (counting up), so resume in counting mode
    main_data.control_mode = ControlModeCounting;
    main_data.is_editing_existing_timer = false;
    main_data.timer_length_modified_in_edit_mode = false;
  } else {
    // No timer was set and it wasn't in chrono mode, so start fresh
    main_data.control_mode = ControlModeNew;
    timer_reset();
    main_data.is_editing_existing_timer = false;
    vibes_short_pulse();
    main_data.timer_length_modified_in_edit_mode = false;
  }
  prv_reset_new_expire_timer();


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
}

// Terminate the program
static void prv_terminate(void) {
  // unsubscribe from timer service
  tick_timer_service_unsubscribe();
  // schedule wakeup
  if (!timer_is_chrono() && !timer_is_paused() && !timer_data.reset_on_init) {
    time_t wakeup_time = (epoch() + timer_get_value_ms()) / MSEC_IN_SEC;
    wakeup_schedule(wakeup_time, 0, true);
  }
  // destroy
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
}
