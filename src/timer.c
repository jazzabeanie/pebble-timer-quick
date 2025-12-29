// @file timer.c
// @brief Data and controls for timer
//
// Contains data and all functions for setting and accessing
// a timer. Also saves and loads timers between closing and reopening.
//
// @author Eric D. Phillips
// @data October 26, 2015
// @bugs No known bugs

#include "timer.h"
#include "utility.h"

#define PERSIST_VERSION 3
#define PERSIST_VERSION_KEY 4342896
#define PERSIST_TIMER_KEY_V2_DATA 58734
#define PERSIST_TIMER_KEY 58736
#define VIBRATION_LENGTH_MS 30000
// legacy persistent storage
#define PERSIST_TIMER_KEY_V1_LEGACY 3456
// TODO: I think I can remove V2 and V3 once I have updated my app to all devices

// Vibration sequence
static const uint32_t vibe_sequence[] = {150, 200, 300};
static const VibePattern vibe_pattern = {
  .durations = vibe_sequence,
  .num_segments = ARRAY_LENGTH(vibe_sequence),
};

// Main data structure
Timer timer_data;


////////////////////////////////////////////////////////////////////////////////////////////////////
// API Functions
//

// Get timer value divided into time parts
void timer_get_time_parts(uint16_t *hr, uint16_t *min, uint16_t *sec) {
  int64_t value = timer_get_value_ms();
  (*hr) = value / MSEC_IN_HR;
  (*min) = value % MSEC_IN_HR / MSEC_IN_MIN;
  (*sec) = value % MSEC_IN_MIN / MSEC_IN_SEC;
}

// Get the timer time in milliseconds assuming the following conditions
// 1. when the timer is running, start_ms represents the epoch when it was started
// 2. when it is paused, start_ms represents the negative of the time is has been running
int64_t timer_get_value_ms(void) {
  int64_t value = timer_data.length_ms - epoch() +
    (((timer_data.start_ms + epoch() - 1) % epoch()) + 1);
  if (value < 0) {
    return -value;
  }
  return value;
}

// Get the total timer time in milliseconds
int64_t timer_get_length_ms(void) {
  return timer_data.length_ms;
}

// Check if the timer is vibrating
bool timer_is_vibrating(void) {
  return timer_is_chrono() && !timer_is_paused() && timer_data.can_vibrate;
}

// Check if timer is in stopwatch mode
bool timer_is_chrono(void) {
  // see timer_get_timer_parts for explanation of equation
  return timer_data.length_ms - (int64_t)epoch() +
    ((timer_data.start_ms + (int64_t)epoch() - 1) % (int64_t)epoch() + 1) <= 0;
}

// Check if timer or stopwatch is paused
bool timer_is_paused(void) {
  return timer_data.start_ms <= 0;
}

// Check if the timer is elapsed and vibrate if this is the first call after elapsing
void timer_check_elapsed(void) {
  if (timer_is_chrono() && !timer_is_paused() && timer_data.can_vibrate) {
    // stop vibration after certain duration
    if (timer_get_value_ms() > VIBRATION_LENGTH_MS) {
      timer_data.can_vibrate = false;
      if (timer_data.auto_snooze_count < 5) {
        timer_data.auto_snooze_count++;
        timer_increment(SNOOZE_INCREMENT_MS);
      }
    } else {
      // vibrate
      vibes_enqueue_custom_pattern(vibe_pattern);
    }
  }
}

// Increment timer value currently being edited
void timer_increment(int64_t increment) {
  // if in paused stopwatch mode, rewind to previous time
  // JJ: actually it just checks if timer_is_chrono and it's active. I think
  // it's assumed to be paused if this code is running
  // if (timer_is_chrono() && timer_data.start_ms) {
  //   timer_rewind();
  //   return;
  // }
  // identify increment class
  // int64_t interval;
  // if (abs(increment) < MSEC_IN_MIN) {
  //   interval = MSEC_IN_MIN;
  // } else if (abs(increment) < MSEC_IN_HR) {
  //   interval = MSEC_IN_HR;
  // } else {
  //   interval = MSEC_IN_HR * 100;
  // }
  // calculate new time by incrementing with wrapping
  // int64_t ls_bit = (timer_data.length_ms + timer_data.start_ms) % interval;
  // int64_t ls_bit = (timer_data.length_ms + timer_data.start_ms) % interval;
  // int64_t step = (ls_bit + interval + increment) % interval - ls_bit;
  // if (timer_data.start_ms) {
  //   timer_data.start_ms += step;
  //   if (timer_data.start_ms > 0) {
  //     timer_data.length_ms += timer_data.start_ms;
  //     timer_data.start_ms = 0;
  //   }
  // } else {
  //   timer_data.length_ms += step;
  // }
  // timer_data.length_ms += step;
  APP_LOG(APP_LOG_LEVEL_DEBUG, "in timer_increment, timer_data.start_ms = %lld", timer_data.start_ms);
  APP_LOG(APP_LOG_LEVEL_DEBUG, "in timer_increment, timer_data.length_ms = %lld", timer_data.length_ms);
  APP_LOG(APP_LOG_LEVEL_DEBUG, "in timer_increment, increment = %lld", increment);
  timer_data.length_ms += increment;
  APP_LOG(APP_LOG_LEVEL_DEBUG, "in timer_increment, new timer_data.length_ms = %lld", timer_data.length_ms);
  // if at zero, remove any leftover milliseconds
  if (timer_get_value_ms() < MSEC_IN_SEC) {
    timer_reset();
  }
  // enable vibration
  if (timer_data.length_ms) {
    timer_data.can_vibrate = true;
  }
}

// Increment stopwatch (chrono) value currently being edited by adjusting start time
void timer_increment_chrono(int64_t increment) {
  // adjust start time to effectively add time to the stopwatch
  timer_data.start_ms -= increment;
}

// Toggle play pause state for timer
void timer_toggle_play_pause(void) {
  if (timer_data.start_ms > 0) {
    timer_data.start_ms -= epoch();
  } else {
    timer_data.start_ms += epoch();
  }
}

//! Rewind the timer back to its original value
void timer_rewind(void) {
  timer_data.start_ms = 0;  // this also pauses the timer
  // enable vibration
  if (timer_data.length_ms) {
    timer_data.can_vibrate = true;
  }
}

// Reset the timer to zero
void timer_reset(void) {
  timer_data.length_ms = 0;
  timer_data.base_length_ms = 0;
  // timer_data.start_ms = 0;  // other code infers the timer is paused by start_ms = 0
  timer_data.start_ms = epoch();
  // disable vibration
  timer_data.can_vibrate = false;
  timer_data.auto_snooze_count = 0;
}

// Save the timer to persistent storage
void timer_persist_store(void) {
// write out current persistent data version
  persist_write_int(PERSIST_VERSION_KEY, PERSIST_VERSION);
  // Always write to the new V3 key
  persist_write_data(PERSIST_TIMER_KEY, &timer_data, sizeof(timer_data));

  // TODO: can I remove this code once all devices have been update?
  // Clean up old keys if they still exist
  if (persist_exists(PERSIST_TIMER_KEY_V2_DATA)) {
    persist_delete(PERSIST_TIMER_KEY_V2_DATA);
  }
  if (persist_exists(PERSIST_TIMER_KEY_V1_LEGACY)) {
    persist_delete(PERSIST_TIMER_KEY_V1_LEGACY);
  }
}

// Reset the auto snooze count
void timer_reset_auto_snooze(void) {
  timer_data.auto_snooze_count = 0;
}

// Read the timer from persistent storage
void timer_persist_read(void) {
  // --- Destructive Update Logic ---
  // 1. If the old V2 key exists, delete it.
  if (persist_exists(PERSIST_TIMER_KEY_V2_DATA)) {
    APP_LOG(APP_LOG_LEVEL_INFO, "Deleting old V2 data.");
    persist_delete(PERSIST_TIMER_KEY_V2_DATA);
  }
  // 2. If the old V1 key exists, delete it.
  if (persist_exists(PERSIST_TIMER_KEY_V1_LEGACY)) {
    APP_LOG(APP_LOG_LEVEL_INFO, "Deleting old V1 data.");
    persist_delete(PERSIST_TIMER_KEY_V1_LEGACY);
  }

  // TODO: can I remove deleting old key code once all devices have been updated?
  // --- Now, just try to load the new (V3) data ---
  if (persist_exists(PERSIST_TIMER_KEY)) {
    // User has run the new app before, load their new V3 data
    persist_read_data(PERSIST_TIMER_KEY, &timer_data, sizeof(timer_data));
  } else {
    // First time running V3 (or no data saved), reset to default
    timer_reset();
  }
}
