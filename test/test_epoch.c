#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>

#include "pebble.h"

// --- Mock watch clock ---------------------------------------------------------
// The "true" time in ms moves forward by 1 ms on every clock read, so a second
// boundary can fall between two reads, as it can on the watch.
static uint64_t s_true_ms;

time_t time(time_t *tloc) {
  time_t s = (time_t)(s_true_ms / 1000);
  s_true_ms++;
  if (tloc) *tloc = s;
  return s;
}

uint16_t time_ms(time_t *tloc, uint16_t *out_ms) {
  time_t s = (time_t)(s_true_ms / 1000);
  uint16_t ms = (uint16_t)(s_true_ms % 1000);
  s_true_ms++;
  if (tloc) *tloc = s;
  if (out_ms) *out_ms = ms;
  return ms;
}

// --- Stubs for the rest of utility.c -------------------------------------------
#include "../src/timer.h"
#include "../src/main.h"
Timer timer_slots[MAX_TIMERS];
uint8_t timer_get_active_slot(void) { return 0; }
void timer_get_time_parts(uint16_t *hr, uint16_t *min, uint16_t *sec) { *hr = *min = *sec = 0; }
bool timer_is_paused(void) { return true; }
bool timer_is_vibrating(void) { return false; }
bool timer_is_chrono(void) { return true; }
ControlMode main_get_control_mode(void) { return ControlModeNew; }
bool main_is_reverse_direction(void) { return false; }
bool main_is_backlight_on(void) { return false; }

#include "../src/utility.c"

// epoch() must read seconds and milliseconds from the same instant. Reading
// them with two calls can be off by a whole second when a second boundary
// falls between the reads.
static void test_epoch_is_consistent_across_a_second_boundary(void **state) {
  for (uint64_t start = 1999; start < 5000; start += 1000) {
    // The boundary falls between the first and second clock read
    s_true_ms = 1000000000ULL + start;
    uint64_t before = s_true_ms;
    uint64_t value = epoch();
    uint64_t after = s_true_ms;
    assert_true(value >= before);
    assert_true(value <= after);
  }
}

// Away from a boundary the value is the clock time (within the 1 ms that
// each mock read takes).
static void test_epoch_value(void **state) {
  s_true_ms = 1000000000ULL + 1234;
  uint64_t value = epoch();
  assert_true(value >= 1000000000ULL + 1234);
  assert_true(value <= s_true_ms);
}

int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test(test_epoch_value),
    cmocka_unit_test(test_epoch_is_consistent_across_a_second_boundary),
  };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
