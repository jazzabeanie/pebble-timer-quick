// timer.c in the aplite configuration (this binary is built with
// -DPBL_PLATFORM_APLITE): 3 slots, "Timer N" names, and the load of saved data
// that has more slots than the limit. The alarm watch helpers are tested here
// too, so the alarm-delivery code is tested in the configuration that is
// trimmed.

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

// With test logs compiled out, test_log_state() is a macro and needs no stub
#if !defined(TEST_LOGS) || TEST_LOGS
void test_log_state(const char *event) {}
#endif

// Keys of timer.c (private there)
#define KEY_VERSION 4342896
#define KEY_COUNT 59000
#define KEY_SLOT(n) (59001 + (n))
#define SAVED_VERSION 9

#define T0 ((uint64_t)50000000)
static uint64_t s_now = T0;

uint64_t epoch(void) {
  return s_now;
}

// --- Fake persist store ---
#define STORE_MAX 16
static struct {
  bool used;
  uint32_t key;
  size_t size;
  uint8_t data[128];
} s_store[STORE_MAX];

static int prv_store_find(uint32_t key) {
  for (int i = 0; i < STORE_MAX; i++) {
    if (s_store[i].used && s_store[i].key == key) {
      return i;
    }
  }
  return -1;
}

int persist_write_data(const uint32_t key, const void *data, const size_t size) {
  int i = prv_store_find(key);
  for (int j = 0; i < 0 && j < STORE_MAX; j++) {
    if (!s_store[j].used) {
      i = j;
    }
  }
  assert_true(i >= 0);
  assert_true(size <= sizeof(s_store[i].data));
  s_store[i].used = true;
  s_store[i].key = key;
  s_store[i].size = size;
  memcpy(s_store[i].data, data, size);
  return (int)size;
}

status_t persist_write_int(const uint32_t key, const int32_t value) {
  persist_write_data(key, &value, sizeof(value));
  return 0;
}

int32_t persist_read_int(const uint32_t key) {
  int i = prv_store_find(key);
  int32_t value = 0;
  if (i >= 0) {
    memcpy(&value, s_store[i].data, sizeof(value));
  }
  return value;
}

bool persist_exists(const uint32_t key) {
  return prv_store_find(key) >= 0;
}

status_t persist_delete(const uint32_t key) {
  int i = prv_store_find(key);
  if (i >= 0) {
    s_store[i].used = false;
  }
  return 0;
}

int persist_read_data(const uint32_t key, void *buffer, const size_t buffer_size) {
  int i = prv_store_find(key);
  if (i < 0) {
    return 0;
  }
  size_t size = s_store[i].size < buffer_size ? s_store[i].size : buffer_size;
  memcpy(buffer, s_store[i].data, size);
  return (int)size;
}

void vibes_long_pulse(void) {}
void vibes_enqueue_custom_pattern(VibePattern pattern) {}
void vibes_cancel(void) {}

static int setup(void **state) {
  s_now = T0;
  memset(s_store, 0, sizeof(s_store));
  timer_count = 0;
  timer_set_active_slot(0);
  memset(timer_slots, 0, sizeof(timer_slots));
  timer_watch_restore(0);
  return 0;
}

// Save `count` slots as an older version with a higher limit would: slot i is
// a running countdown of (i + 1) minutes named "saved <i>"
static void prv_save_slots(int32_t count) {
  persist_write_int(KEY_VERSION, SAVED_VERSION);
  persist_write_int(KEY_COUNT, count);
  for (int32_t i = 0; i < count; i++) {
    Timer t = {
      .length_ms = (i + 1) * 60000,
      .base_length_ms = (i + 1) * 60000,
      .start_ms = T0 - 1000 * i,
      .can_vibrate = true,
      .is_paused = (i == 1),
    };
    snprintf(t.name, sizeof(t.name), "saved %d", (int)i);
    persist_write_data(KEY_SLOT(i), &t, sizeof(t));
  }
}

// Make slot `i` a running countdown that ends `remaining_ms` from now
static void prv_make_countdown(uint8_t i, int64_t remaining_ms) {
  timer_slots[i].length_ms = 60000;
  timer_slots[i].base_length_ms = 60000;
  timer_slots[i].start_ms = (int64_t)s_now - (60000 - remaining_ms);
  timer_slots[i].is_paused = false;
  timer_slots[i].can_vibrate = true;
}


////////////////////////////////////////////////////////////////////////////////
// D1: "Timer N" names
//

static void test_first_name_is_timer_1(void **state) {
  assert_int_equal(timer_slot_create(), 0);
  assert_string_equal(timer_slots[0].name, "Timer 1");
}

static void test_second_name_is_timer_2(void **state) {
  timer_slot_create();
  assert_int_equal(timer_slot_create(), 1);
  assert_string_equal(timer_slots[0].name, "Timer 1");
  assert_string_equal(timer_slots[1].name, "Timer 2");
}

static void test_lowest_free_number_after_delete(void **state) {
  timer_slot_create();
  timer_slot_create();
  // Delete "Timer 1": "Timer 2" moves down to slot 0
  timer_slot_delete(0);
  assert_string_equal(timer_slots[0].name, "Timer 2");
  assert_int_equal(timer_slot_create(), 1);
  assert_string_equal(timer_slots[1].name, "Timer 1");
}

static void test_no_duplicate_names_after_delete_and_create(void **state) {
  // Every order of "delete one slot, create one slot" from a full app
  for (uint8_t first = 0; first < MAX_TIMERS; first++) {
    for (uint8_t second = 0; second < MAX_TIMERS; second++) {
      setup(state);
      for (uint8_t i = 0; i < MAX_TIMERS; i++) {
        timer_slot_create();
      }
      timer_slot_delete(first);
      assert_true(timer_slot_create() >= 0);
      timer_slot_delete(second);
      assert_true(timer_slot_create() >= 0);
      assert_int_equal(timer_count, MAX_TIMERS);
      for (uint8_t a = 0; a < timer_count; a++) {
        assert_memory_equal(timer_slots[a].name, "Timer ", 6);
        for (uint8_t b = a + 1; b < timer_count; b++) {
          assert_string_not_equal(timer_slots[a].name, timer_slots[b].name);
        }
      }
    }
  }
}

static void test_saved_mnemonic_name_is_kept_and_not_counted(void **state) {
  timer_slot_create();
  snprintf(timer_slots[0].name, sizeof(timer_slots[0].name), "dry mouse");
  assert_int_equal(timer_slot_create(), 1);
  assert_string_equal(timer_slots[0].name, "dry mouse");
  // The slot with the mnemonic name does not use a number
  assert_string_equal(timer_slots[1].name, "Timer 1");
}

static void test_reassign_name_of_existing_slot(void **state) {
  timer_slot_create();
  timer_slot_create();
  // A restart gives slot 0 a new name: its own old name does not block "Timer 1"
  timer_assign_name(0);
  assert_string_equal(timer_slots[0].name, "Timer 1");
  assert_string_equal(timer_slots[1].name, "Timer 2");
}


////////////////////////////////////////////////////////////////////////////////
// D5: 3 slots, and saved data with more slots
//

static void test_max_timers_is_3(void **state) {
  assert_int_equal(MAX_TIMERS, 3);
}

static void test_fourth_slot_is_refused(void **state) {
  for (int i = 0; i < 3; i++) {
    assert_int_equal(timer_slot_create(), i);
  }
  assert_int_equal(timer_slot_create(), -1);
  assert_int_equal(timer_count, 3);
}

static void test_read_five_saved_slots_keeps_first_three(void **state) {
  prv_save_slots(5);

  timer_persist_read();

  assert_int_equal(timer_count, 3);
  for (int i = 0; i < 3; i++) {
    char name[20];
    snprintf(name, sizeof(name), "saved %d", i);
    assert_string_equal(timer_slots[i].name, name);
    assert_int_equal(timer_slots[i].length_ms, (i + 1) * 60000);
    assert_int_equal(timer_slots[i].start_ms, T0 - 1000 * i);
    assert_true(timer_slots[i].can_vibrate);
    assert_int_equal(timer_slots[i].is_paused, i == 1);
    assert_true(persist_exists(KEY_SLOT(i)));
  }
  // The saved data of the dropped slots is removed
  assert_false(persist_exists(KEY_SLOT(3)));
  assert_false(persist_exists(KEY_SLOT(4)));
  assert_int_equal(timer_get_active_slot(), 0);
}

static void test_read_five_saved_slots_then_store(void **state) {
  prv_save_slots(5);
  timer_persist_read();
  timer_persist_store();
  assert_int_equal(persist_read_int(KEY_COUNT), 3);

  // The next launch loads the same 3 timers
  memset(timer_slots, 0, sizeof(timer_slots));
  timer_count = 0;
  timer_persist_read();
  assert_int_equal(timer_count, 3);
  assert_string_equal(timer_slots[2].name, "saved 2");
}

static void test_read_three_saved_slots(void **state) {
  prv_save_slots(3);
  timer_persist_read();
  assert_int_equal(timer_count, 3);
  assert_string_equal(timer_slots[0].name, "saved 0");
  assert_string_equal(timer_slots[2].name, "saved 2");
  assert_int_equal(timer_slots[2].length_ms, 180000);
}

static void test_read_one_saved_slot(void **state) {
  prv_save_slots(1);
  timer_persist_read();
  assert_int_equal(timer_count, 1);
  assert_string_equal(timer_slots[0].name, "saved 0");
}

static void test_read_negative_count_resets(void **state) {
  prv_save_slots(2);
  persist_write_int(KEY_COUNT, -1);
  timer_slots[0].length_ms = 1234;
  timer_persist_read();
  assert_int_equal(timer_count, 0);
  assert_int_equal(timer_slots[0].length_ms, 0);
  assert_true(timer_slots[0].is_paused);
}

// A count that no version can have saved is bad data: reset, as before
static void test_read_impossible_count_resets(void **state) {
  prv_save_slots(3);
  persist_write_int(KEY_COUNT, 33);
  timer_persist_read();
  assert_int_equal(timer_count, 0);
  // The saved slots are not touched by the reset
  assert_true(persist_exists(KEY_SLOT(0)));
}

static void test_read_highest_saved_count(void **state) {
  // 32 is the highest count that a version can have saved
  prv_save_slots(3);
  persist_write_int(KEY_COUNT, 32);
  timer_persist_read();
  assert_int_equal(timer_count, 3);
  assert_string_equal(timer_slots[1].name, "saved 1");
}


////////////////////////////////////////////////////////////////////////////////
// Alarm watch helpers with 3 slots
//

static void test_watch_ended_mask_three_slots(void **state) {
  for (int i = 0; i < 3; i++) {
    timer_slot_create();
  }
  prv_make_countdown(0, 5000);
  prv_make_countdown(1, 2000);
  prv_make_countdown(2, 9000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x7);
  assert_int_equal(timer_ended_mask(timer_watch_mask()), 0);
  assert_int_equal(timer_next_ending_slot(timer_watch_mask()), 1);
  assert_int_equal(timer_next_watched_end_ms(timer_watch_mask()), 2000);

  s_now += 6000;
  assert_int_equal(timer_ended_mask(timer_watch_mask()), 0x3);
  // Slot 1 ended first
  assert_int_equal(timer_find_ended_countdown(timer_watch_mask()), 1);
  assert_int_equal(timer_next_ending_slot(timer_watch_mask()), 2);
}

static void test_watch_mask_shift_on_delete(void **state) {
  for (int i = 0; i < 3; i++) {
    timer_slot_create();
  }
  prv_make_countdown(1, 2000);
  prv_make_countdown(2, 4000);
  timer_watch_add_running();
  assert_int_equal(timer_watch_mask(), 0x6);

  timer_slot_delete(0);
  assert_int_equal(timer_watch_mask(), 0x3);
  s_now += 3000;
  assert_int_equal(timer_find_ended_countdown(timer_watch_mask()), 0);
  assert_int_equal(timer_ended_mask(timer_watch_mask()), 0x1);
}

static void test_watch_alarm_of_loaded_slot_rings(void **state) {
  // A countdown kept by the "first 3" load still ends and vibrates
  prv_save_slots(5);
  timer_persist_read();
  timer_watch_restore(0x1f);  // a saved mask with bits of dropped slots
  s_now += 180000;
  // Slot 1 is paused; slots 0 and 2 ended; bits 3 and 4 have no effect
  assert_int_equal(timer_ended_mask(timer_watch_mask()), 0x5);
  assert_int_equal(timer_find_ended_countdown(timer_watch_mask()), 0);
}

int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test_setup(test_first_name_is_timer_1, setup),
    cmocka_unit_test_setup(test_second_name_is_timer_2, setup),
    cmocka_unit_test_setup(test_lowest_free_number_after_delete, setup),
    cmocka_unit_test_setup(test_no_duplicate_names_after_delete_and_create, setup),
    cmocka_unit_test_setup(test_saved_mnemonic_name_is_kept_and_not_counted, setup),
    cmocka_unit_test_setup(test_reassign_name_of_existing_slot, setup),
    cmocka_unit_test_setup(test_max_timers_is_3, setup),
    cmocka_unit_test_setup(test_fourth_slot_is_refused, setup),
    cmocka_unit_test_setup(test_read_five_saved_slots_keeps_first_three, setup),
    cmocka_unit_test_setup(test_read_five_saved_slots_then_store, setup),
    cmocka_unit_test_setup(test_read_three_saved_slots, setup),
    cmocka_unit_test_setup(test_read_one_saved_slot, setup),
    cmocka_unit_test_setup(test_read_negative_count_resets, setup),
    cmocka_unit_test_setup(test_read_impossible_count_resets, setup),
    cmocka_unit_test_setup(test_read_highest_saved_count, setup),
    cmocka_unit_test_setup(test_watch_ended_mask_three_slots, setup),
    cmocka_unit_test_setup(test_watch_mask_shift_on_delete, setup),
    cmocka_unit_test_setup(test_watch_alarm_of_loaded_slot_rings, setup),
  };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
