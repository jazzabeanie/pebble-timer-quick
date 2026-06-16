// @file timer.c
// @brief Data and controls for timer
//
// Contains data and all functions for setting and accessing
// a timer. Also saves and loads timers between closing and reopening.
//
// @author Eric D. Phillips & Jared Johnston
// @date October 26, 2015
// @bugs No known bugs

#include "timer.h"
#include "utility.h"
#include "mnemonic.h"
#include <time.h>

#define PERSIST_VERSION 7
#define PERSIST_VERSION_KEY 4342896
// Legacy keys kept for cleanup only
#define PERSIST_TIMER_KEY_V2_DATA 58734
#define PERSIST_TIMER_KEY         58736
#define PERSIST_TIMER_KEY_V1_LEGACY 3456

// Multi-timer persistence
#define PERSIST_TIMER_COUNT_KEY     59000
#define PERSIST_TIMER_SLOTS_BASE    59001
#define PERSIST_TIMER_SLOT_KEY(n)   (PERSIST_TIMER_SLOTS_BASE + (n))

#define VIBRATION_LENGTH_MS 30000

// Vibration sequence
static const uint32_t vibe_sequence[] = {150, 200, 300};
static const VibePattern vibe_pattern = {
  .durations = vibe_sequence,
  .num_segments = ARRAY_LENGTH(vibe_sequence),
};

// Multi-timer globals
Timer timer_slots[MAX_TIMERS];
uint8_t timer_count = 0;
static uint8_t s_active_slot = 0;


////////////////////////////////////////////////////////////////////////////////////////////////////
// Active Slot Helpers
//

uint8_t timer_get_active_slot(void) {
  return s_active_slot;
}

void timer_set_active_slot(uint8_t index) {
  s_active_slot = index;
}


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
  if (timer_data.length_ms > 0) {
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

  // Restore repeat count from base
  if (timer_data.is_repeating) {
    timer_data.repeat_count = timer_data.base_repeat_count;
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
  timer_data.base_repeat_count = 0;
  timer_data.elapsed = false;
}

// Save all timer slots to persistent storage
void timer_persist_store(void) {
  persist_write_int(PERSIST_VERSION_KEY, PERSIST_VERSION);
  persist_write_int(PERSIST_TIMER_COUNT_KEY, (int32_t)timer_count);
  for (uint8_t i = 0; i < timer_count; i++) {
    persist_write_data(PERSIST_TIMER_SLOT_KEY(i), &timer_slots[i], sizeof(Timer));
  }
  // Clean up legacy single-timer keys
  if (persist_exists(PERSIST_TIMER_KEY)) {
    persist_delete(PERSIST_TIMER_KEY);
  }
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

// Read all timer slots from persistent storage
void timer_persist_read(void) {
  int version = persist_read_int(PERSIST_VERSION_KEY);
  if (version < PERSIST_VERSION) {
    APP_LOG(APP_LOG_LEVEL_INFO, "Old version (%d), resetting data.", version);
    timer_count = 0;
    s_active_slot = 0;
    timer_reset();
    return;
  }

  if (!persist_exists(PERSIST_TIMER_COUNT_KEY)) {
    timer_count = 0;
    s_active_slot = 0;
    timer_reset();
    return;
  }

  int32_t count = persist_read_int(PERSIST_TIMER_COUNT_KEY);
  if (count < 0 || count > MAX_TIMERS) {
    timer_count = 0;
    s_active_slot = 0;
    timer_reset();
    return;
  }

  timer_count = (uint8_t)count;
  if (timer_count == 0) {
    timer_reset();
  }
  for (uint8_t i = 0; i < timer_count; i++) {
    if (persist_exists(PERSIST_TIMER_SLOT_KEY(i))) {
      persist_read_data(PERSIST_TIMER_SLOT_KEY(i), &timer_slots[i], sizeof(Timer));
    } else {
      // Initialize missing slot as reset timer
      timer_slots[i] = (Timer){0};
      timer_slots[i].is_paused = true;
    }
  }
  s_active_slot = 0;
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Multi-Timer Management
//

void timer_assign_name(uint8_t new_idx) {
  time_t t = (time_t)(timer_slots[new_idx].start_ms / 1000);
  struct tm *tm_info = localtime(&t);
  const char *adj, *noun;
  mnemonic_generate_name(tm_info->tm_hour, tm_info->tm_min, &adj, &noun);

  // Max base: "awesome honeybee" = 16 chars; fits in 17-byte buffer.
  char base[17];
  snprintf(base, sizeof(base), "%s %s", adj, noun);

  int suffix = 1;
  bool collision;
  do {
    collision = false;
    if (suffix == 1) {
      snprintf(timer_slots[new_idx].name, sizeof(timer_slots[new_idx].name), "%s", base);
    } else {
      // suffix is bounded by MAX_TIMERS (5) — always a single digit.
      int len = snprintf(timer_slots[new_idx].name,
                         sizeof(timer_slots[new_idx].name) - 2, "%s", base);
      timer_slots[new_idx].name[len]     = ' ';
      timer_slots[new_idx].name[len + 1] = '0' + (char)suffix;
      timer_slots[new_idx].name[len + 2] = '\0';
    }
    for (uint8_t i = 0; i < new_idx; i++) {
      if (strncmp(timer_slots[i].name, timer_slots[new_idx].name,
                  sizeof(timer_slots[new_idx].name)) == 0) {
        collision = true;
        break;
      }
    }
    suffix++;
  } while (collision);
}

// Allocate next free slot as a running stopwatch; returns slot index or -1 if full
int8_t timer_slot_create(void) {
  if (timer_count >= MAX_TIMERS) return -1;
  uint8_t idx = timer_count;
  timer_count++;
  timer_slots[idx] = (Timer){
    .length_ms        = 0,
    .start_ms         = epoch(),
    .base_length_ms   = 0,
    .elapsed          = false,
    .can_vibrate      = false,
    .reset_on_init    = false,
    .auto_snooze_count = 0,
    .is_repeating     = false,
    .repeat_count     = 0,
    .base_repeat_count = 0,
    .is_paused        = false,
  };
  timer_assign_name(idx);
  return (int8_t)idx;
}

// Delete the slot at index, compact the array, and clear the freed persist key
void timer_slot_delete(uint8_t index) {
  if (index >= timer_count) return;
  // Compact: shift remaining slots down
  for (uint8_t i = index; i < timer_count - 1; i++) {
    timer_slots[i] = timer_slots[i + 1];
  }
  timer_count--;
  // Clear the now-unused last persist slot
  uint32_t freed_key = PERSIST_TIMER_SLOT_KEY(timer_count);
  if (persist_exists(freed_key)) {
    persist_delete(freed_key);
  }
  // Adjust active slot index
  if (timer_count == 0) {
    s_active_slot = 0;
  } else if (s_active_slot >= timer_count) {
    s_active_slot = timer_count - 1;
  } else if (s_active_slot > index) {
    s_active_slot--;
  }
}

// Helper: get elapsed ms for a slot (works for paused and running)
static int64_t prv_slot_elapsed_ms(const Timer *t) {
  if (t->is_paused) {
    return t->start_ms;
  }
  return epoch() - t->start_ms;
}

// Helper: returns true if a slot is in chrono (stopwatch) mode
static bool prv_slot_is_chrono(const Timer *t) {
  return t->length_ms - prv_slot_elapsed_ms(t) <= 0;
}

// Fill out_indices with slot indices sorted by expiry
void timer_get_sorted_slots(uint8_t *out_indices, uint8_t *out_count) {
  uint8_t countdown[MAX_TIMERS];
  uint8_t countdown_count = 0;
  uint8_t chrono[MAX_TIMERS];
  uint8_t chrono_count = 0;

  for (uint8_t i = 0; i < timer_count; i++) {
    if (prv_slot_is_chrono(&timer_slots[i])) {
      chrono[chrono_count++] = i;
    } else {
      countdown[countdown_count++] = i;
    }
  }

  // Sort countdown timers ascending by remaining ms (soonest first)
  for (uint8_t i = 1; i < countdown_count; i++) {
    uint8_t key = countdown[i];
    int64_t rem_key = timer_slots[key].length_ms - prv_slot_elapsed_ms(&timer_slots[key]);
    int8_t j = (int8_t)i - 1;
    while (j >= 0) {
      int64_t rem_j = timer_slots[countdown[j]].length_ms - prv_slot_elapsed_ms(&timer_slots[countdown[j]]);
      if (rem_j <= rem_key) break;
      countdown[j + 1] = countdown[j];
      j--;
    }
    countdown[j + 1] = key;
  }

  // Sort stopwatches descending by elapsed ms (longest running first)
  for (uint8_t i = 1; i < chrono_count; i++) {
    uint8_t key = chrono[i];
    int64_t ela_key = prv_slot_elapsed_ms(&timer_slots[key]);
    int8_t j = (int8_t)i - 1;
    while (j >= 0) {
      int64_t ela_j = prv_slot_elapsed_ms(&timer_slots[chrono[j]]);
      if (ela_j >= ela_key) break;
      chrono[j + 1] = chrono[j];
      j--;
    }
    chrono[j + 1] = key;
  }

  // Combine: countdown first, then stopwatches
  *out_count = 0;
  for (uint8_t i = 0; i < countdown_count; i++) {
    out_indices[(*out_count)++] = countdown[i];
  }
  for (uint8_t i = 0; i < chrono_count; i++) {
    out_indices[(*out_count)++] = chrono[i];
  }
}
