#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <string.h>
#include <cmocka.h>

#include "pebble.h"
#include "utility.h"
#include "timer.h"

void test_log_state(const char *event) {}

uint64_t epoch(void) {
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
void vibes_enqueue_custom_pattern(VibePattern pattern) {}
void vibes_cancel(void) {}

static int setup(void **state) {
  timer_count = 0;
  timer_set_active_slot(0);
  memset(timer_slots, 0, sizeof(timer_slots));
  return 0;
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

int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test_setup_teardown(test_slot_create_success, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_create_at_capacity, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_compaction, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_first, setup, teardown),
    cmocka_unit_test_setup_teardown(test_slot_delete_adjusts_active_slot, setup, teardown),
    cmocka_unit_test_setup_teardown(test_sorted_slots_order, setup, teardown),
    cmocka_unit_test_setup_teardown(test_sorted_slots_chrono_order, setup, teardown),
  };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
