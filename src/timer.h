//! @file timer.h
//! @brief Data and controls for timer
//!
//! Contains data and all functions for setting and accessing
//! a timer. Also saves and loads timers between closing and reopening.
//!
//! @author Eric D. Phillips
//! @data October 26, 2015
//! @bugs No known bugs

#pragma once
#include <pebble.h>

#define SNOOZE_INCREMENT_MS (MSEC_IN_MIN * 5)

// The stopwatch-laps feature set (lap recording, the post-lap flash,
// slot-limit warnings, and the Timer List "Delete all" row) does not fit in
// aplite's 24KB app region alongside the existing app (~1.7KB of headroom at
// baseline vs ~2.8KB of new code+data), so it is compiled out there. Aplite
// keeps the previous limits and button behavior.
#ifndef PBL_PLATFORM_APLITE
  #define LAP_FEATURE 1
#else
  #define LAP_FEATURE 0
#endif

// Maximum concurrent timer slots and stored name length. Aplite's 24KB
// app-RAM region was already within ~1.7KB of full before the stopwatch-laps
// feature, so it keeps the previous limits; every other platform gets the
// full 32 slots and 39-character names.
#ifdef PBL_PLATFORM_APLITE
  #define MAX_TIMERS 5
  #define TIMER_NAME_LEN 20
#else
  #define MAX_TIMERS 32
  #define TIMER_NAME_LEN 40
#endif

// Main data structure
typedef struct {
  int64_t     length_ms;      //< Length of timer in milliseconds
  int64_t     start_ms;       //< The start epoch of the timer in milliseconds
  int64_t     base_length_ms; //< Used to track the original timer value (for later repeating).
#if LAP_FEATURE
  int64_t     last_lap_ms;    //< Cumulative elapsed at the most recent lap (0 = no lap yet)
#endif
  bool        elapsed;        //< Used to start the vibration if first time as elapsed
  bool        can_vibrate;    //< Flag used to tell when the timer has completed
  bool        reset_on_init;  //< Flag to indicate if the timer should be reset on next initialization
  int8_t      auto_snooze_count; //< Count of how many times the timer has auto-snoozed
  bool        is_repeating;   //< A flag to indicate that the timer is in repeat mode
  uint8_t     repeat_count;   //< A counter to track the number of times the timer has repeated
  uint8_t     base_repeat_count; //< The original repeat count set by the user (for restart)
  bool        is_paused;      //< A flag to indicate if the timer is paused
#if LAP_FEATURE
  uint8_t     lap_count;      //< Number of laps recorded from this timer (next lap is lap_count + 1)
#endif
  char        name[TIMER_NAME_LEN]; //< Mnemonic name assigned at creation; never changes
} Timer;

extern Timer timer_slots[MAX_TIMERS];
extern uint8_t timer_count;

// Active-slot indirection: all code that touches the current timer uses timer_data.xxx
uint8_t timer_get_active_slot(void);
void timer_set_active_slot(uint8_t index);
#define timer_data (timer_slots[timer_get_active_slot()])


//! Get timer value
//! @param hr A pointer to where to store the hour value of the timer
//! @param min A pointer to where to store the minute value of the timer
//! @param sec A pointer to where to store the second value of the timer
void timer_get_time_parts(uint16_t *hr, uint16_t *min, uint16_t *sec);

//! Get the millisecond component (0-999) of the current timer value
//! @return The remainder milliseconds within the current second
uint16_t timer_get_ms_part(void);

//! Get the timer time in milliseconds
//! @return The current value of the timer in milliseconds
int64_t timer_get_value_ms(void);

//! Get the current split in milliseconds: the timer value minus the cumulative
//! elapsed at the most recent lap. Equals the timer value when no lap has been
//! recorded (last_lap_ms == 0).
//! @return The current split of the timer in milliseconds
int64_t timer_get_split_ms(void);

//! Get the total timer time in milliseconds
//! @return The total value of the timer in milliseconds
int64_t timer_get_length_ms(void);

//! Check if the timer is vibrating
//! @return True if the timer is currently vibrating
bool timer_is_vibrating(void);

//! Check if timer is in stopwatch mode
//! @return True if it is counting up as a stopwatch
bool timer_is_chrono(void);

//! Check if timer or stopwatch is paused
//! @return True if the timer is paused
bool timer_is_paused(void);

//! Check if the timer is elapsed and vibrate if this is the first call after elapsing
void timer_check_elapsed(void);

//! Increment timer value currently being edited
//! @param increment The amount to increment by
void timer_increment(int64_t increment);

//! Increment stopwatch (chrono) value currently being edited by adjusting start time
//! @param increment The amount to increment by
void timer_increment_chrono(int64_t increment);

//! Restart the current cycle at the base length, deducting the overshoot past
//! the alarm so repeated cycles stay aligned with the original schedule
void timer_repeat_restart(void);

//! Toggle play pause state for timer
void timer_toggle_play_pause(void);

//! Rewind the timer back to its original value
void timer_rewind(void);

//! Restart the timer from its original value
void timer_restart(void);

//! Reset the timer to zero
void timer_reset(void);

//! Save the timer to persistent storage
void timer_persist_store(void);

//! Read the timer from persistent storage
void timer_persist_read(void);

//! Reset the auto snooze count
void timer_reset_auto_snooze(void);

//! Allocate next free slot as a running stopwatch; returns slot index or -1 if full
int8_t timer_slot_create(void);

//! Record a lap of the slot at src_idx: allocate a free slot holding a paused
//! copy of the source frozen at its current value, named "Lap [n]: <src name>"
//! (the end of the source name is trimmed if the prefix would overflow the
//! buffer). The source keeps running: its last_lap_ms is set to the value at
//! the snapshot and its lap_count is incremented.
//! @param src_idx The slot index to record a lap of
//! @return The new lap slot index, or -1 when no slot is free
int8_t timer_slot_lap(uint8_t src_idx);

//! Assign (or reassign) a mnemonic name to an existing slot; call after start_ms is set
void timer_assign_name(uint8_t idx);

//! Set a user-provided name on a slot (e.g. from voice dictation).
//! Trims leading/trailing whitespace, truncates at a word boundary to fit the
//! name field (hard-truncates a single oversized token), and persists.
//! @param idx The slot index to rename
//! @param name The null-terminated source name (may contain surrounding whitespace)
void timer_set_name(uint8_t idx, const char *name);

//! Delete the slot at index, compact the array, and clear the freed persist key
void timer_slot_delete(uint8_t index);

//! Fill out_indices with slot indices sorted by expiry (countdown soonest first, then stopwatches longest first)
void timer_get_sorted_slots(uint8_t *out_indices, uint8_t *out_count);
