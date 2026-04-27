#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <string.h>
#include <cmocka.h>

#include "pebble.h"
#include "mnemonic.h"

// 5.1a: hour 14, minute 30 → "dry", "mouse"
static void test_mnemonic_14_30(void **state) {
  const char *adj, *noun;
  mnemonic_generate_name(14, 30, &adj, &noun);
  assert_string_equal(adj, "dry");
  assert_string_equal(noun, "mouse");
}

// 5.1b: hour 0, minute 0 → "sissy", "sauce"
static void test_mnemonic_00_00(void **state) {
  const char *adj, *noun;
  mnemonic_generate_name(0, 0, &adj, &noun);
  assert_string_equal(adj, "sissy");
  assert_string_equal(noun, "sauce");
}

// 5.1c: hour 23, minute 59 → "numb", "lip"
static void test_mnemonic_23_59(void **state) {
  const char *adj, *noun;
  mnemonic_generate_name(23, 59, &adj, &noun);
  assert_string_equal(adj, "numb");
  assert_string_equal(noun, "lip");
}

// 5.1d: hour 3, minute 29 → "awesome", "honeybee" (longest combo)
static void test_mnemonic_03_29(void **state) {
  const char *adj, *noun;
  mnemonic_generate_name(3, 29, &adj, &noun);
  assert_string_equal(adj, "awesome");
  assert_string_equal(noun, "honeybee");
}

int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test(test_mnemonic_14_30),
    cmocka_unit_test(test_mnemonic_00_00),
    cmocka_unit_test(test_mnemonic_23_59),
    cmocka_unit_test(test_mnemonic_03_29),
  };
  return cmocka_run_group_tests(tests, NULL, NULL);
}
