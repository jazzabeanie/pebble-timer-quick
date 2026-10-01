// animation.c: the heap use of animations. On aplite the heap is about 2KB,
// so an animation must use one small allocation, and an allocation that fails
// must not stop the app (the value jumps to its end instead).

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <cmocka.h>

#include "pebble.h"

// --- Counted allocator, used by animation.c in place of malloc/free ---
static int s_alloc_count;      //< allocations made since the last reset
static int s_live_count;       //< allocations not freed yet
static int s_fail_after = -1;  //< fail every allocation after this many (-1 = never)
static int s_crash_count;      //< times the app would have stopped on a NULL pointer

static void *counted_malloc(size_t size) {
  if (s_fail_after >= 0 && s_alloc_count >= s_fail_after) {
    return NULL;
  }
  s_alloc_count++;
  s_live_count++;
  return calloc(1, size);
}

static void counted_free(void *ptr) {
  if (ptr) {
    s_live_count--;
  }
  free(ptr);
}

// utility.h: MALLOC() ends the app when the allocation fails
void *malloc_check(uint16_t size, const char *file, int line) {
  void *ptr = counted_malloc(size);
  if (!ptr) {
    s_crash_count++;
    // Return memory anyway so the test itself can go on and report the crash
    ptr = calloc(1, size);
  }
  return ptr;
}

static uint64_t s_now;
uint64_t epoch(void) { return s_now; }

// One AppTimer at a time, as animation.c uses it
static AppTimerCallback s_timer_callback;
AppTimer *app_timer_register(uint32_t timeout_ms, AppTimerCallback callback, void *data) {
  s_timer_callback = callback;
  return (AppTimer *)1;
}
void app_timer_cancel(AppTimer *timer) { s_timer_callback = NULL; }

// Linear interpolation is enough for these tests
#include "../src/interpolation.h"
int32_t interpolation_integer(int32_t from, int32_t to, uint32_t percent, uint32_t percent_max,
                              InterpolationCurve curve) {
  if (percent >= percent_max) {
    return to;
  }
  return from + (int32_t)((int64_t)(to - from) * percent / percent_max);
}

#define malloc counted_malloc
#define free counted_free
#include "../src/animation.c"
#undef malloc
#undef free

// Run the animation timer until no animation is left (or a step limit)
static void prv_run(uint32_t ms) {
  uint64_t end = s_now + ms;
  while (s_now < end) {
    s_now += 30;
    if (!s_timer_callback) {
      continue;
    }
    AppTimerCallback callback = s_timer_callback;
    s_timer_callback = NULL;
    callback(NULL);
  }
}

static int setup(void **state) {
  animation_stop_all();
  s_alloc_count = 0;
  s_live_count = 0;
  s_fail_after = -1;
  s_crash_count = 0;
  s_now = 1000000;
  s_timer_callback = NULL;
  return 0;
}

static const GRect RECT_A = {{0, 0}, {10, 10}};
static const GRect RECT_B = {{40, 20}, {30, 50}};
static const GRect RECT_C = {{5, 5}, {5, 5}};

static void test_grect_animation_reaches_its_end(void **state) {
  GRect value = RECT_A;
  animation_grect_start(&value, RECT_B, 140, 0, CurveLinear);
  prv_run(60);
  assert_true(value.origin.x > 0 && value.origin.x < 40);
  prv_run(300);
  assert_memory_equal(&value, &RECT_B, sizeof(GRect));
  assert_int_equal(s_live_count, 0);
  assert_null(s_timer_callback);
}

static void test_int32_animation_reaches_its_end(void **state) {
  int32_t value = 100;
  animation_int32_start(&value, 500, 250, 0, CurveLinear);
  prv_run(600);
  assert_int_equal(value, 500);
  assert_int_equal(s_live_count, 0);
}

// One allocation for the whole life of an animation, also after its first step
static void test_one_allocation_per_animation(void **state) {
  GRect rect = RECT_A;
  int32_t number = 0;
  animation_grect_start(&rect, RECT_B, 140, 0, CurveLinear);
  animation_int32_start(&number, 7, 140, 0, CurveLinear);
  prv_run(60);
  assert_int_equal(s_alloc_count, 2);
  assert_int_equal(s_live_count, 2);
}

// A full heap must not stop the app: the value jumps to its end
static void test_grect_allocation_failure_jumps_to_end(void **state) {
  GRect value = RECT_A;
  s_fail_after = 0;
  animation_grect_start(&value, RECT_B, 140, 0, CurveLinear);
  assert_int_equal(s_crash_count, 0);
  assert_memory_equal(&value, &RECT_B, sizeof(GRect));
  assert_int_equal(s_live_count, 0);
  prv_run(300);
  assert_int_equal(s_crash_count, 0);
  assert_memory_equal(&value, &RECT_B, sizeof(GRect));
}

static void test_int32_allocation_failure_jumps_to_end(void **state) {
  int32_t value = 3;
  s_fail_after = 0;
  animation_int32_start(&value, 90, 250, 0, CurveLinear);
  assert_int_equal(s_crash_count, 0);
  assert_int_equal(value, 90);
  assert_int_equal(s_live_count, 0);
}

// An animation that is running when the heap fills up still ends correctly
static void test_running_animation_survives_a_full_heap(void **state) {
  GRect first = RECT_A;
  GRect second = RECT_A;
  animation_grect_start(&first, RECT_B, 140, 0, CurveLinear);
  s_fail_after = s_alloc_count;
  animation_grect_start(&second, RECT_C, 140, 0, CurveLinear);
  prv_run(300);
  assert_int_equal(s_crash_count, 0);
  assert_memory_equal(&first, &RECT_B, sizeof(GRect));
  assert_memory_equal(&second, &RECT_C, sizeof(GRect));
  assert_int_equal(s_live_count, 0);
}

// The hold-to-reset animation: two animations of one value, the second one
// delayed. The value shrinks, and then returns after the delay.
static void test_two_animations_of_one_value_run_in_order(void **state) {
  GRect value = RECT_B;
  animation_grect_start(&value, RECT_C, 100, 0, CurveLinear);
  animation_grect_start(&value, RECT_B, 100, 750, CurveLinear);
  prv_run(300);
  assert_memory_equal(&value, &RECT_C, sizeof(GRect));
  prv_run(1000);
  assert_memory_equal(&value, &RECT_B, sizeof(GRect));
  assert_int_equal(s_live_count, 0);
}

static void test_stop_removes_one_animation(void **state) {
  GRect value = RECT_A;
  animation_grect_start(&value, RECT_B, 140, 0, CurveLinear);
  prv_run(60);
  animation_stop(&value);
  assert_int_equal(s_live_count, 0);
  GRect stopped = value;
  prv_run(300);
  assert_memory_equal(&value, &stopped, sizeof(GRect));
}

static void test_stop_all_frees_everything_and_can_start_again(void **state) {
  GRect rect = RECT_A;
  int32_t number = 0;
  animation_grect_start(&rect, RECT_B, 140, 0, CurveLinear);
  animation_int32_start(&number, 7, 140, 0, CurveLinear);
  prv_run(60);
  animation_stop_all();
  assert_int_equal(s_live_count, 0);
  // No stale list or timer is left: a new animation runs to its end
  animation_int32_start(&number, 9, 140, 0, CurveLinear);
  prv_run(300);
  assert_int_equal(number, 9);
  assert_int_equal(s_live_count, 0);
}

int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test_setup(test_grect_animation_reaches_its_end, setup),
    cmocka_unit_test_setup(test_int32_animation_reaches_its_end, setup),
    cmocka_unit_test_setup(test_one_allocation_per_animation, setup),
    cmocka_unit_test_setup(test_grect_allocation_failure_jumps_to_end, setup),
    cmocka_unit_test_setup(test_int32_allocation_failure_jumps_to_end, setup),
    cmocka_unit_test_setup(test_running_animation_survives_a_full_heap, setup),
    cmocka_unit_test_setup(test_two_animations_of_one_value_run_in_order, setup),
    cmocka_unit_test_setup(test_stop_removes_one_animation, setup),
    cmocka_unit_test_setup(test_stop_all_frees_everything_and_can_start_again, setup),
  };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
