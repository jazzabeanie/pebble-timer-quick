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

#define PERSIST_VERSION 4
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
// 2. when it is paused, start_ms represents the time is has been running (elapsed)
int64_t timer_get_value_ms(void) {
  // Calculate elapsed time based on timer state
  int64_t elapsed;
  if (!timer_data.is_paused) {
    // Running timer: elapsed = current time - start time
    // Note: elapsed can be negative if start_ms is in the future
    elapsed = epoch() - timer_data.start_ms;
  } else {
    // Paused timer: start_ms stores the elapsed time
    elapsed = timer_data.start_ms;
  }

  // Calculate raw value: positive = countdown time remaining, negative = chrono time elapsed
  int64_t raw_value = timer_data.length_ms - elapsed;

  // Return absolute value
  if (raw_value < 0) {
    return -raw_value;
  }
  return raw_value;
}

// Get the total timer time in milliseconds
int64_t timer_get_length_ms(void) {
  return timer_data.length_ms;
}

// Check if the timer is vibrating
bool timer_is_vibrating(void) {
  return timer_is_chrono() && !timer_data.is_paused && timer_data.can_vibrate;
}

// Check if timer is in stopwatch mode
bool timer_is_chrono(void) {
  // Calculate elapsed time based on timer state
  int64_t elapsed_ms;
  if (!timer_data.is_paused) {
    // Running timer: elapsed = current time - start time
    // Note: elapsed can be negative if start_ms is in the future
    elapsed_ms = epoch() - timer_data.start_ms;
  } else {
    // Paused timer: start_ms stores the elapsed time
    elapsed_ms = timer_data.start_ms;
  }

  // Chrono mode when elapsed time exceeds length (raw_value <= 0)
  return timer_data.length_ms - elapsed_ms <= 0;
}

// Check if timer or stopwatch is paused
bool timer_is_paused(void) {
  return timer_data.is_paused;
}

// Check if the timer is elapsed and vibrate if this is the first call after elapsing
void timer_check_elapsed(void) {
  if (timer_is_chrono() && !timer_is_paused() && timer_data.can_vibrate) {
    timer_data.elapsed = true;
    if (timer_data.is_repeating && timer_data.repeat_count > 1) {
      timer_data.repeat_count--;
      timer_increment(timer_data.base_length_ms);
      vibes_long_pulse(); // Vibrate briefly on repeat
      test_log_state("timer_repeat");
      return;
    }
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
  timer_data.length_ms += increment;
  // if at zero, remove any leftover milliseconds
  if (timer_get_value_ms() < MSEC_IN_SEC) {
    timer_reset();
  }
  // enable vibration
  if (timer_data.length_ms) {
    timer_data.can_vibrate = true;
  }
  timer_data.elapsed = false;
}

// Increment stopwatch (chrono) value currently being edited by adjusting start time
void timer_increment_chrono(int64_t increment) {
  // adjust start time or elapsed time effectively add time to the stopwatch
  if (!timer_data.is_paused) {
    timer_data.start_ms -= increment;
  } else {
    timer_data.start_ms += increment;
  }
  timer_data.elapsed = false;
}

// Toggle play pause state for timer
void timer_toggle_play_pause(void) {
  if (!timer_data.is_paused) {
    // Pause: store elapsed time in start_ms
    timer_data.start_ms = epoch() - timer_data.start_ms;
    timer_data.is_paused = true;
  } else {
    // Resume: store start epoch in start_ms
    timer_data.start_ms = epoch() - timer_data.start_ms;
    timer_data.is_paused = false;
  }
}

//! Rewind the timer back to its original value
void timer_rewind(void) {
  timer_data.start_ms = 0;
  timer_data.is_paused = true;
  // enable vibration
  if (timer_data.length_ms) {
    timer_data.can_vibrate = true;
  }
  timer_data.elapsed = false;
}

// Restart the timer from its original value
void timer_restart(void) {
  if (timer_data.base_length_ms > 0) {
      // Countdown: restore to base length
      timer_data.length_ms = timer_data.base_length_ms;
  } else {
      // Chrono: reset to 0
      timer_data.length_ms = 0;
  }

  if (timer_data.is_paused) {
      // If paused, reset elapsed time to 0
      timer_data.start_ms = 0;
  } else {
      // If running, restart running from now
      timer_data.start_ms = epoch();
  }

  // enable vibration if length > 0
  if (timer_data.length_ms > 0) {
    timer_data.can_vibrate = true;
  } else {
    timer_data.can_vibrate = false;
  }

  timer_data.auto_snooze_count = 0;
  timer_data.elapsed = false;
}

// Reset the timer to zero
void timer_reset(void) {
  timer_data.length_ms = 0;
  timer_data.base_length_ms = 0;
  timer_data.start_ms = 0;
  timer_data.is_paused = true;
  // disable vibration
  timer_data.can_vibrate = false;
  timer_data.auto_snooze_count = 0;
  timer_data.is_repeating = false;
  timer_data.repeat_count = 0;
  timer_data.elapsed = false;
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
  // Check version
  int version = persist_read_int(PERSIST_VERSION_KEY);
  if (version < PERSIST_VERSION) {
    APP_LOG(APP_LOG_LEVEL_INFO, "Old version (%d), resetting data.", version);
    timer_reset();
    return;
  }

  // --- Now, just try to load the current data ---
  if (persist_exists(PERSIST_TIMER_KEY)) {
    // User has run the current app before, load their data
    persist_read_data(PERSIST_TIMER_KEY, &timer_data, sizeof(timer_data));
  } else {
    // No data saved, reset to default
    timer_reset();
  }
}
