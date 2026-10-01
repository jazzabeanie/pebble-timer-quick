#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <cmocka.h>

#include "pebble.h"
#include "utility.h"
#include "timer.h"

void test_log_state(const char *event) {}

// The watch-mask tests read the clock many times per call, so they use a fixed
// clock (setup_fixed) instead of queueing one will_return per epoch() call.
static bool s_use_fixed_epoch = false;
static uint64_t s_fixed_epoch = 0;

uint64_t epoch(void) {
  if (s_use_fixed_epoch) {
    return s_fixed_epoch;
  }
  return (uint64_t)mock();
}

int32_t persist_read_int(const uint32_t key) {
  return (int32_t)mock();
}

status_t persist_write_int(const uint32_t key, const int32_t value) {
  return 0;
}

int persist_write_data(const uint32_t key, const void *data, const size_t size) {
  return (int)size;
}

bool persist_exists(const uint32_t key) {
  return false;
}

status_t persist_delete(const uint32_t key) {
  return 0;
}

int persist_read_data(const uint32_t key, void *buffer, const size_t buffer_size) {
  return 0;
}

void vibes_long_pulse(void) {}
static int s_alarm_vibe_count = 0;
void vibes_enqueue_custom_pattern(VibePattern pattern) { s_alarm_vibe_count++; }
void vibes_cancel(void) {}

static int setup(void **state) {
  s_use_fixed_epoch = false;
  timer_count = 0;
  timer_set_active_slot(0);
  memset(timer_slots, 0, sizeof(timer_slots));
  return 0;
}

// Fixed-clock setup for the watch-mask tests
#define WATCH_T0 ((uint64_t)50000000)

static int setup_fixed(void **state) {
  setup(state);
  s_use_fixed_epoch = true;
  s_fixed_epoch = WATCH_T0;
  s_alarm_vibe_count = 0;
  timer_watch_restore(0);
  return 0;
}

static int setup_utc(void **state) {
  setenv("TZ", "UTC", 1);
  tzset();
  return setup(state);
}

static int teardown(void **state) {
  return 0;
}

// 3.1a: timer_slot_create succeeds when fewer than MAX_TIMERS slots exist
static void test_slot_create_success(void **state) {
  will_return(epoch, 1000);
  int8_t idx = timer_slot_create();

  assert_int_equal(idx, 0);
  assert_int_equal(timer_count, 1);
  assert_int_equal(timer_slots[0].start_ms, 1000);
  assert_false(timer_slots[0].is_paused);
  assert_int_equal(timer_slots[0].length_ms, 0);
}

// 3.1b: timer_slot_create returns -1 when at MAX_TIMERS capacity
static void test_slot_create_at_capacity(void **state) {
  // Fill all slots
  for (uint8_t i = 0; i < MAX_TIMERS; i++) {
    will_return(epoch, 1000 + i * 1000);
    int8_t idx = timer_slot_create();
    assert_int_equal(idx, (int8_t)i);
  }
  assert_int_equal(timer_count, MAX_TIMERS);

  // Now try to create one more
  int8_t idx = timer_slot_create();
  assert_int_equal(idx, -1);
  assert_int_equal(timer_count, MAX_TIMERS);
}

// 3.2a: timer_slot_delete compacts the array correctly
static void test_slot_delete_compaction(void **state) {
  // Create 3 slots
  for (int i = 0; i < 3; i++) {
    will_return(epoch, 1000 * (i + 1));
    timer_slot_create();
  }
  assert_int_equal(timer_count, 3);

  // Record slot 2's start_ms (the one that should move to index 1)
  int64_t slot2_start = timer_slots[2].start_ms;

  // Delete slot 1 (middle)
  timer_slot_delete(1);

  assert_int_equal(timer_count, 2);
  // What was slot 2 is now at slot 1
  assert_int_equal(timer_slots[1].start_ms, slot2_start);
  // Slot 0 unchanged
  assert_int_equal(timer_slots[0].start_ms, 1000);
}

// 3.2b: timer_slot_delete decrements count correctly when deleting first slot
static void test_slot_delete_first(void **state) {
  for (int i = 0; i < 2; i++) {
    will_return(epoch, 1000 * (i + 1));
    timer_slot_create();
  }
  int64_t slot1_start = timer_slots[1].start_ms;

  timer_slot_delete(0);

  assert_int_equal(timer_count, 1);
  assert_int_equal(timer_slots[0].start_ms, slot1_start);
}

// 3.2c: timer_slot_delete adjusts active slot when deleting active
static void test_slot_delete_adjusts_active_slot(void **state) {
  for (int i = 0; i < 3; i++) {
    will_return(epoch, 1000 * (i + 1));
    timer_slot_create();
  }
  // Set active slot to last (index 2)
  timer_set_active_slot(2);
  // Delete index 2
  timer_slot_delete(2);

  // Active slot should have been clamped to new last (1)
  assert_int_equal(timer_get_active_slot(), 1);
}

// 3.3: timer_get_sorted_slots orders countdown before stopwatch, soonest first
static void test_sorted_slots_order(void **state) {
  // Create slot 0: countdown timer, 10s remaining (length=10000, start at epoch=0 while paused)
  timer_slots[0] = (Timer){
    .length_ms  = 10000,
    .start_ms   = 0,  // paused, elapsed=0, remaining=10000
    .is_paused  = true,
  };
  // Create slot 1: countdown timer, 5s remaining
  timer_slots[1] = (Timer){
    .length_ms  = 5000,
    .start_ms   = 0,  // paused, elapsed=0, remaining=5000
    .is_paused  = true,
  };
  // Create slot 2: stopwatch (chrono), elapsed 20s
  timer_slots[2] = (Timer){
    .length_ms  = 0,
    .start_ms   = 20000,  // paused, elapsed=20000 -> chrono
    .is_paused  = true,
  };
  timer_count = 3;

  uint8_t indices[MAX_TIMERS];
  uint8_t count = 0;
  timer_get_sorted_slots(indices, &count);

  assert_int_equal(count, 3);
  // Soonest countdown (5s) should be first, then 10s countdown, then stopwatch
  assert_int_equal(indices[0], 1);  // 5s remaining
  assert_int_equal(indices[1], 0);  // 10s remaining
  assert_int_equal(indices[2], 2);  // stopwatch
}

// 3.3b: stopwatches sorted longest-elapsed first
static void test_sorted_slots_chrono_order(void **state) {
  // Two stopwatches: slot 0 elapsed 5s, slot 1 elapsed 20s
  timer_slots[0] = (Timer){
    .length_ms = 0,
    .start_ms  = 5000,
    .is_paused = true,
  };
  timer_slots[1] = (Timer){
    .length_ms = 0,
    .start_ms  = 20000,
    .is_paused = true,
  };
  timer_count = 2;

  uint8_t indices[MAX_TIMERS];
  uint8_t count = 0;
  timer_get_sorted_slots(indices, &count);

  assert_int_equal(count, 2);
  // Longest elapsed first: slot 1 (20s) before slot 0 (5s)
  assert_int_equal(indices[0], 1);
  assert_int_equal(indices[1], 0);
}

// epoch ms for 14:30:00 UTC on 1970-01-01
#define EPOCH_14_30_UTC ((uint64_t)((14 * 3600 + 30 * 60) * 1000))

// 5.2: timer created at 14:30 UTC gets name "dry mouse"
static void test_name_assigned_from_time(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  int8_t idx = timer_slot_create();
  assert_int_equal(idx, 0);
  assert_string_equal(timer_slots[0].name, "dry mouse");
}

// 5.3: second timer at the same minute gets suffix " 2"
static void test_name_collision_second_gets_suffix_2(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();
  will_return(epoch, EPOCH_14_30_UTC + 1);
  timer_slot_create();
  assert_string_equal(timer_slots[0].name, "dry mouse");
  assert_string_equal(timer_slots[1].name, "dry mouse 2");
}

// 5.4: third timer at the same minute gets suffix " 3"
static void test_name_collision_third_gets_suffix_3(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();
  will_return(epoch, EPOCH_14_30_UTC + 1);
  timer_slot_create();
  will_return(epoch, EPOCH_14_30_UTC + 2);
  timer_slot_create();
  assert_string_equal(timer_slots[0].name, "dry mouse");
  assert_string_equal(timer_slots[1].name, "dry mouse 2");
  assert_string_equal(timer_slots[2].name, "dry mouse 3");
}

// 5.6: editing a timer's length_ms does not change its name
static void test_name_unchanged_after_length_edit(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();
  assert_string_equal(timer_slots[0].name, "dry mouse");

  timer_slots[0].length_ms = 300000; // edit to 5 minutes
  assert_string_equal(timer_slots[0].name, "dry mouse");
}

////////////////////////////////////////////////////////////////////////////////////////////////////
// Lap recording (timer_slot_lap / timer_get_split_ms)
//

// Lap copy is paused and frozen at the source's value at the snapshot
static void test_lap_copy_paused_at_snapshot(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  int8_t src = timer_slot_create();  // running chrono started at 14:30
  assert_int_equal(src, 0);

  // Lap 5 seconds later
  will_return(epoch, EPOCH_14_30_UTC + 5000);
  int8_t lap = timer_slot_lap(0);

  assert_int_equal(lap, 1);
  assert_int_equal(timer_count, 2);
  assert_true(timer_slots[1].is_paused);
  // Paused slot stores elapsed in start_ms: frozen at 5000ms
  assert_int_equal(timer_slots[1].start_ms, 5000);
  assert_int_equal(timer_slots[1].length_ms, 0);

  // The copy's value does not advance: read it as the active slot
  timer_set_active_slot(1);
  assert_int_equal(timer_get_value_ms(), 5000);
}

// The copy carries the previous lap boundary; the source's split restarts
static void test_lap_split_and_cumulative(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();

  // First lap at 5s
  will_return(epoch, EPOCH_14_30_UTC + 5000);
  timer_slot_lap(0);
  assert_int_equal(timer_slots[0].last_lap_ms, 5000);
  assert_int_equal(timer_slots[0].lap_count, 1);
  // First lap copy: no previous lap, split == cumulative == 5000
  assert_int_equal(timer_slots[1].last_lap_ms, 0);

  // Second lap at 7s
  will_return(epoch, EPOCH_14_30_UTC + 7000);
  int8_t lap2 = timer_slot_lap(0);
  assert_int_equal(lap2, 2);
  // Copy carries the previous boundary (5000): its split is 7000 - 5000 = 2000
  assert_int_equal(timer_slots[2].last_lap_ms, 5000);
  timer_set_active_slot(2);
  assert_int_equal(timer_get_value_ms(), 7000);   // cumulative at the lap
  assert_int_equal(timer_get_split_ms(), 2000);   // this lap's split

  // Source: split restarts from the second lap
  assert_int_equal(timer_slots[0].last_lap_ms, 7000);
  assert_int_equal(timer_slots[0].lap_count, 2);
  timer_set_active_slot(0);
  will_return(epoch, EPOCH_14_30_UTC + 8500);  // running: value needs epoch
  will_return(epoch, EPOCH_14_30_UTC + 8500);
  assert_int_equal(timer_get_split_ms(), 1500);   // 8500 - 7000
  assert_int_equal(timer_get_value_ms(), 8500);   // total unchanged by laps
}

// Split equals the value while no lap has been recorded
static void test_split_equals_value_without_laps(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();
  timer_set_active_slot(0);
  will_return(epoch, EPOCH_14_30_UTC + 4000);
  will_return(epoch, EPOCH_14_30_UTC + 4000);
  assert_int_equal(timer_get_split_ms(), 4000);
  assert_int_equal(timer_get_value_ms(), 4000);
}

// Lap slots are named "Lap [n]: <name>" with n incrementing per source timer
static void test_lap_names_increment(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();
  assert_string_equal(timer_slots[0].name, "dry mouse");

  will_return(epoch, EPOCH_14_30_UTC + 5000);
  timer_slot_lap(0);
  assert_string_equal(timer_slots[1].name, "Lap 1: dry mouse");

  will_return(epoch, EPOCH_14_30_UTC + 7000);
  timer_slot_lap(0);
  assert_string_equal(timer_slots[2].name, "Lap 2: dry mouse");
}

// A long source name is trimmed at the END so the prefix stays intact
static void test_lap_long_name_trimmed(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();
  // Fill the source name to buffer capacity (39 chars + null in char[40])
  const char *long_name = "abcdefghijklmnopqrstuvwxyz0123456789abc";
  assert_int_equal(strlen(long_name), sizeof(timer_slots[0].name) - 1);
  snprintf(timer_slots[0].name, sizeof(timer_slots[0].name), "%s", long_name);

  will_return(epoch, EPOCH_14_30_UTC + 5000);
  int8_t lap = timer_slot_lap(0);
  assert_int_equal(lap, 1);

  // Prefix intact, source name trimmed at the end, null within the buffer
  assert_memory_equal(timer_slots[1].name, "Lap 1: ", 7);
  assert_int_equal(strlen(timer_slots[1].name), sizeof(timer_slots[1].name) - 1);
  assert_memory_equal(timer_slots[1].name + 7, long_name,
                      sizeof(timer_slots[1].name) - 1 - 7);
}

// timer_slot_lap returns -1 at capacity and leaves the source untouched
static void test_lap_returns_minus1_at_capacity(void **state) {
  for (uint8_t i = 0; i < MAX_TIMERS; i++) {
    will_return(epoch, EPOCH_14_30_UTC + i * MSEC_IN_MIN);
    assert_int_equal(timer_slot_create(), (int8_t)i);
  }
  assert_int_equal(timer_count, MAX_TIMERS);

  int8_t lap = timer_slot_lap(0);
  assert_int_equal(lap, -1);
  assert_int_equal(timer_count, MAX_TIMERS);
  assert_int_equal(timer_slots[0].lap_count, 0);
  assert_int_equal(timer_slots[0].last_lap_ms, 0);
}

// Recording a lap does not change the original's running state or total
static void test_lap_original_keeps_running(void **state) {
  will_return(epoch, EPOCH_14_30_UTC);
  timer_slot_create();

  will_return(epoch, EPOCH_14_30_UTC + 5000);
  timer_slot_lap(0);

  assert_false(timer_slots[0].is_paused);
  // start_ms (epoch anchor) unchanged: the total keeps counting from creation
  timer_set_active_slot(0);
  will_return(epoch, EPOCH_14_30_UTC + 9000);
  assert_int_equal(timer_get_value_ms(), 9000);
}

////////////////////////////////////////////////////////////////////////////////////////////////////
// Watch mask and ended-countdown helpers (openspec: list-alarm-takeover)
//

// Put a running countdown in a slot: `remaining_ms` left at the current fixed
// clock (negative = it ended that long ago)
static void prv_set_countdown(uint8_t slot, int64_t length_ms, int64_t remaining_ms) {
  timer_slots[slot] = (Timer){
    .length_ms = length_ms,
    .base_length_ms = length_ms,
    .start_ms = (int64_t)s_fixed_epoch - (length_ms - remaining_ms),
    .can_vibrate = true,
    .is_paused = false,
  };
  if (slot >= timer_count) {
    timer_count = slot + 1;
  }
}

// A paused countdown with `remaining_ms` left
static void prv_set_paused_countdown(uint8_t slot, int64_t length_ms, int64_t remaining_ms) {
  timer_slots[slot] = (Timer){
    .length_ms = length_ms,
    .base_length_ms = length_ms,
    .start_ms = length_ms - remaining_ms,
    .can_vibrate = true,
    .is_paused = true,
  };
  if (slot >= timer_count) {
    timer_count = slot + 1;
  }
}

// A running stopwatch that has counted `elapsed_ms`
static void prv_set_chrono(uint8_t slot, int64_t elapsed_ms) {
  timer_slots[slot] = (Timer){
    .start_ms = (int64_t)s_fixed_epoch - elapsed_ms,
    .is_paused = false,
  };
  if (slot >= timer_count) {
    timer_count = slot + 1;
  }
}

// 1.1: only a running countdown with time left is in the mask
static void test_running_countdown_mask(void **state) {
  prv_set_countdown(0, 60000, 20000);          // running, time left
  prv_set_paused_countdown(1, 60000, 20000);   // paused
  prv_set_countdown(2, 60000, -5000);          // overdue
  prv_set_chrono(3, 8000);                     // stopwatch
  prv_set_countdown(4, 300000, 1);             // running, 1 ms left

  assert_int_equal(timer_running_countdown_mask(), (1u << 0) | (1u << 4));
}

// 1.2: none has ended
static void test_find_ended_none(void **state) {
  prv_set_countdown(0, 60000, 20000);
  prv_set_countdown(1, 60000, 1);
  assert_int_equal(timer_find_ended_countdown(0x3), -1);
}

// 1.2: slot 0 ended is reported as 0, not as "none"
static void test_find_ended_slot0(void **state) {
  prv_set_countdown(0, 60000, 0);
  prv_set_countdown(1, 60000, 20000);
  assert_int_equal(timer_find_ended_countdown(0x3), 0);
}

// 1.2: slot 1 ended while slot 0 still runs
static void test_find_ended_slot1(void **state) {
  prv_set_countdown(0, 300000, 200000);
  prv_set_countdown(1, 30000, -100);
  assert_int_equal(timer_find_ended_countdown(0x3), 1);
}

// 1.2: two ended: the first to end is returned, whatever its slot number
static void test_find_ended_first_of_two(void **state) {
  prv_set_countdown(0, 60000, -2000);
  prv_set_countdown(1, 60000, -9000);   // ended first
  prv_set_countdown(2, 60000, -4000);
  assert_int_equal(timer_find_ended_countdown(0x7), 1);
}

// 1.2: ended slots outside the mask are ignored
static void test_find_ended_ignores_slots_outside_mask(void **state) {
  prv_set_countdown(0, 60000, -9000);   // ended, not in the mask
  prv_set_countdown(1, 60000, 20000);
  prv_set_countdown(2, 60000, -1000);   // ended, in the mask
  assert_int_equal(timer_find_ended_countdown(0x6), 2);
  assert_int_equal(timer_find_ended_countdown(0x2), -1);
}

// 1.2c: timer_ended_mask returns only the ended slots of the mask
static void test_ended_mask(void **state) {
  prv_set_countdown(0, 60000, 20000);
  prv_set_countdown(1, 60000, 30000);
  assert_int_equal(timer_ended_mask(0x3), 0);            // none

  prv_set_countdown(0, 60000, -1000);
  assert_int_equal(timer_ended_mask(0x3), 0x1);          // slot 0
  assert_int_equal(timer_ended_mask(0x2), 0);            // slot 0 not in the mask

  prv_set_countdown(0, 60000, 20000);
  prv_set_countdown(1, 60000, 0);
  assert_int_equal(timer_ended_mask(0x3), 0x2);          // slot 1

  prv_set_countdown(0, 60000, -3000);
  assert_int_equal(timer_ended_mask(0x3), 0x3);          // both
}

// 1.2c: paused and stopwatch slots are never "ended", even inside the mask,
// and neither is a countdown whose alarm was silenced
static void test_ended_mask_excludes_paused_and_chrono(void **state) {
  prv_set_paused_countdown(0, 60000, -1000);   // paused past zero
  prv_set_chrono(1, 8000);                     // stopwatch
  prv_set_countdown(2, 60000, -1000);
  prv_set_countdown(3, 60000, -1000);
  timer_slots[3].can_vibrate = false;          // silenced
  assert_int_equal(timer_ended_mask(0xF), 0x4);
  assert_int_equal(timer_find_ended_countdown(0xB), -1);
}

// 1.2a: timer_watch_add_running adds only running countdowns with time left
static void test_watch_add_running(void **state) {
  prv_set_countdown(0, 60000, 20000);
  prv_set_paused_countdown(1, 60000, 20000);
  prv_set_countdown(2, 60000, -5000);
  prv_set_chrono(3, 8000);
  assert_int_equal(timer_watch_mask(), 0);

  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x1);

  // It only adds: a later call keeps the bits that are already set
  prv_set_countdown(1, 60000, 20000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x3);
}

// 1.2a: a bit stays set after its countdown ends
static void test_watch_bit_stays_after_end(void **state) {
  prv_set_countdown(0, 60000, 2000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x1);

  s_fixed_epoch += 5000;   // slot 0 ended 3 s ago
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x1);
  assert_int_equal(timer_ended_mask(timer_watch_mask()), 0x1);
}

// 1.2a: timer_watch_clear clears one bit
static void test_watch_clear(void **state) {
  prv_set_countdown(0, 60000, 20000);
  prv_set_countdown(1, 60000, 20000);
  prv_set_countdown(2, 60000, 20000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x7);

  timer_watch_clear(1);
  assert_int_equal(timer_watch_mask(), 0x5);
}

// 1.2a: a watch bit of a slot that does not exist has no effect
static void test_watch_restore_ignores_missing_slots(void **state) {
  prv_set_countdown(0, 60000, -1000);
  prv_set_countdown(1, 60000, 20000);
  // Leftover data past the last slot must not be read as a timer
  timer_slots[2] = timer_slots[0];
  timer_watch_restore(0xFFFFFFFF);
  assert_int_equal(timer_ended_mask(timer_watch_mask()), 0x1);
  assert_int_equal(timer_find_ended_countdown(timer_watch_mask()), 0);
  assert_int_equal(timer_next_watched_end_ms(timer_watch_mask()), 20000);
}

// 1.2a: timer_slot_delete drops the deleted bit and shifts the higher bits
static void test_slot_delete_shifts_watch_mask(void **state) {
  // Slots 1 and 3 are watched
  for (uint8_t i = 0; i < 5; i++) {
    prv_set_paused_countdown(i, 60000, 20000);
  }
  prv_set_countdown(1, 60000, 20000);
  prv_set_countdown(3, 60000, 20000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0xA);   // 01010

  // Delete below both watched slots: both bits move down
  timer_slot_delete(0);
  assert_int_equal(timer_watch_mask(), 0x5);   // 0101

  // Delete above the first and below the second: only the second moves
  timer_slot_delete(1);
  assert_int_equal(timer_watch_mask(), 0x3);   // 011

  // Delete above both watched slots: no change
  timer_slot_delete(2);
  assert_int_equal(timer_watch_mask(), 0x3);

  // Delete a watched slot: its bit is dropped, the higher bit moves down
  timer_slot_delete(0);
  assert_int_equal(timer_watch_mask(), 0x1);
  timer_slot_delete(0);
  assert_int_equal(timer_watch_mask(), 0);
}

// 1.2a: the highest slot's bit shifts down correctly
static void test_slot_delete_shifts_highest_bit(void **state) {
  for (uint8_t i = 0; i < MAX_TIMERS; i++) {
    prv_set_paused_countdown(i, 60000, 20000);
  }
  prv_set_countdown(MAX_TIMERS - 1, 60000, 20000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 1u << (MAX_TIMERS - 1));

  timer_slot_delete(0);
  assert_int_equal(timer_watch_mask(), 1u << (MAX_TIMERS - 2));
}

// 1.2a: timer_slot_delete moves the "alarm shown" and "alarm rang" slots the
// same way: a slot above the deleted one moves down, the deleted one becomes -1
static void test_slot_delete_moves_alarm_slots(void **state) {
  prv_set_countdown(0, 60000, 20000);
  prv_set_countdown(1, 60000, 20000);
  prv_set_countdown(2, 60000, -2000);   // ended 2 s ago: it rings
  timer_set_active_slot(2);
  timer_alarm_mark_shown();
  timer_check_elapsed();
  assert_int_equal(timer_alarm_shown_slot(), 2);
  assert_int_equal(timer_alarm_rang_slot(), 2);

  // Delete below: both values move down with the timer
  timer_slot_delete(0);
  assert_int_equal(timer_alarm_shown_slot(), 1);
  assert_int_equal(timer_alarm_rang_slot(), 1);

  // Delete above (nothing there to move): no change
  prv_set_countdown(2, 60000, 20000);
  timer_slot_delete(2);
  assert_int_equal(timer_alarm_shown_slot(), 1);
  assert_int_equal(timer_alarm_rang_slot(), 1);

  // Delete the slot itself: both values become -1, so they cannot point at
  // the timer that moves into the deleted slot
  prv_set_countdown(2, 60000, 20000);
  timer_slot_delete(1);
  assert_int_equal(timer_alarm_shown_slot(), -1);
  assert_int_equal(timer_alarm_rang_slot(), -1);
}

// 1.2a: timer_next_watched_end_ms returns the soonest end, ignores ended
// slots, and returns -1 when no slot of the mask has time left
static void test_next_watched_end_ms(void **state) {
  prv_set_countdown(0, 300000, 200000);
  prv_set_countdown(1, 60000, 7000);
  prv_set_countdown(2, 60000, -3000);   // ended
  prv_set_countdown(3, 60000, 2500);    // not in the mask below

  assert_int_equal(timer_next_watched_end_ms(0x7), 7000);
  assert_int_equal(timer_next_watched_end_ms(0xF), 2500);
  assert_int_equal(timer_next_watched_end_ms(0x1), 200000);
  assert_int_equal(timer_next_watched_end_ms(0x4), -1);   // only an ended slot
  assert_int_equal(timer_next_watched_end_ms(0), -1);     // empty mask
}

// 1.2b (D11): an alarm shown 2 min after its end vibrates, and it stops and
// auto-snoozes 30 s after it was shown, not at once
static void test_alarm_shown_late_vibrates_for_full_time(void **state) {
  prv_set_countdown(0, 60000, -120000);   // ended 2 min ago
  timer_set_active_slot(0);

  timer_alarm_mark_shown();
  timer_check_elapsed();
  assert_int_equal(s_alarm_vibe_count, 1);
  assert_true(timer_is_vibrating());
  assert_int_equal(timer_slots[0].length_ms, 60000);
  assert_int_equal(timer_slots[0].auto_snooze_count, 0);

  // 29 s after it was shown: still vibrating
  s_fixed_epoch += 29000;
  timer_check_elapsed();
  assert_int_equal(s_alarm_vibe_count, 2);
  assert_true(timer_is_vibrating());

  // 31 s after it was shown: it stops and auto-snoozes
  s_fixed_epoch += 2000;
  timer_check_elapsed();
  assert_int_equal(s_alarm_vibe_count, 2);
  assert_false(timer_is_vibrating());
  assert_int_equal(timer_slots[0].auto_snooze_count, 1);
  assert_int_equal(timer_slots[0].length_ms, 60000 + SNOOZE_INCREMENT_MS);
}

// 1.2b: without the "shown" mark, an alarm 2 min past its end snoozes at once
// (the behavior for a timer that the app has shown since it ended)
static void test_alarm_not_marked_snoozes_at_once(void **state) {
  prv_set_countdown(0, 60000, -120000);
  timer_set_active_slot(0);

  timer_check_elapsed();
  assert_int_equal(s_alarm_vibe_count, 0);
  assert_int_equal(timer_slots[0].auto_snooze_count, 1);
}

// 1.2b: the offset of one slot does not affect another slot
static void test_alarm_shown_offset_is_per_slot(void **state) {
  prv_set_countdown(0, 60000, -120000);
  prv_set_countdown(1, 60000, -120000);
  timer_set_active_slot(0);
  timer_alarm_mark_shown();

  // Slot 1 was not marked: it uses the plain overtime and snoozes at once
  timer_set_active_slot(1);
  timer_check_elapsed();
  assert_int_equal(s_alarm_vibe_count, 0);
  assert_int_equal(timer_slots[1].auto_snooze_count, 1);

  // Slot 0 keeps its offset and vibrates
  timer_set_active_slot(0);
  timer_check_elapsed();
  assert_int_equal(s_alarm_vibe_count, 1);
  assert_int_equal(timer_slots[0].auto_snooze_count, 0);
}

// 1.2b: a snooze, a reset, a repeat restart, and a restart clear the offset,
// so the next alarm of that slot uses the plain overtime
static void test_alarm_shown_offset_cleared(void **state) {
  timer_set_active_slot(0);

  prv_set_countdown(0, 60000, -120000);
  timer_alarm_mark_shown();
  timer_increment(SNOOZE_INCREMENT_MS);
  assert_int_equal(timer_alarm_shown_slot(), -1);

  prv_set_countdown(0, 60000, -120000);
  timer_alarm_mark_shown();
  timer_reset();
  assert_int_equal(timer_alarm_shown_slot(), -1);

  prv_set_countdown(0, 60000, -120000);
  timer_alarm_mark_shown();
  timer_repeat_restart();
  assert_int_equal(timer_alarm_shown_slot(), -1);

  prv_set_countdown(0, 60000, -120000);
  timer_alarm_mark_shown();
  timer_restart();
  assert_int_equal(timer_alarm_shown_slot(), -1);

  // A change to another slot leaves this slot's offset in place
  prv_set_countdown(0, 60000, -120000);
  prv_set_countdown(1, 60000, 20000);
  timer_alarm_mark_shown();
  timer_set_active_slot(1);
  timer_increment(1000);
  assert_int_equal(timer_alarm_shown_slot(), 0);
}

// D16: the "rang" slot is set when the alarm vibrates, not before, and a
// snooze clears it
static void test_alarm_rang_slot(void **state) {
  prv_set_countdown(0, 60000, 500);
  timer_set_active_slot(0);
  timer_check_elapsed();
  assert_int_equal(timer_alarm_rang_slot(), -1);   // not ended yet

  s_fixed_epoch += 1000;
  timer_check_elapsed();
  assert_int_equal(timer_alarm_rang_slot(), 0);

  timer_increment(SNOOZE_INCREMENT_MS);
  assert_int_equal(timer_alarm_rang_slot(), -1);
}

int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test_setup_teardown(test_slot_create_success, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_create_at_capacity, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_compaction, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_first, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_adjusts_active_slot, setup, teardown),
    cmocka_unit_test_setup_teardown(test_sorted_slots_order, setup, teardown),
    cmocka_unit_test_setup_teardown(test_sorted_slots_chrono_order, setup, teardown),
    cmocka_unit_test_setup_teardown(test_name_assigned_from_time, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_name_collision_second_gets_suffix_2, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_name_collision_third_gets_suffix_3, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_name_unchanged_after_length_edit, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_lap_copy_paused_at_snapshot, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_lap_split_and_cumulative, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_split_equals_value_without_laps, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_lap_names_increment, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_lap_long_name_trimmed, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_lap_returns_minus1_at_capacity, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_lap_original_keeps_running, setup_utc, teardown),
    cmocka_unit_test_setup_teardown(test_running_countdown_mask, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_find_ended_none, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_find_ended_slot0, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_find_ended_slot1, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_find_ended_first_of_two, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_find_ended_ignores_slots_outside_mask, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_ended_mask, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_ended_mask_excludes_paused_and_chrono, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_watch_add_running, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_watch_bit_stays_after_end, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_watch_clear, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_watch_restore_ignores_missing_slots, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_shifts_watch_mask, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_shifts_highest_bit, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_moves_alarm_slots, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_next_watched_end_ms, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_alarm_shown_late_vibrates_for_full_time, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_alarm_not_marked_snoozes_at_once, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_alarm_shown_offset_is_per_slot, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_alarm_shown_offset_cleared, setup_fixed, teardown),
    cmocka_unit_test_setup_teardown(test_alarm_rang_slot, setup_fixed, teardown),
  };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
