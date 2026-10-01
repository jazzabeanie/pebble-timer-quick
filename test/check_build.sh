#!/bin/sh
# Build check for the aplite trims (openspec change aplite-ram-trim).
#
# Makes a test build and then a release build, and checks what each binary
# contains:
#   - aplite test build:    has the TEST_STATE log text
#   - aplite release build: no TEST_STATE log text, no app_message_open
#   - basalt release build: has the TEST_STATE log text and app_message_open
#
# The release build is made last, so build/ holds a release build at the end.
#
# Usage: test/check_build.sh [path to the pebble tool]

cd "$(dirname "$0")/.." || exit 1

PEBBLE="${1:-./conda-env/bin/pebble}"
NM="${NM:-$HOME/.pebble-sdk/SDKs/current/toolchain/arm-none-eabi/bin/arm-none-eabi-nm}"
failures=0

check() {
  # check <description> <expected: 0 = found, 1 = not found> <command...>
  description="$1"
  expected="$2"
  shift 2
  "$@" > /dev/null 2>&1
  result=$?
  [ "$result" -ne 0 ] && result=1
  if [ "$result" -eq "$expected" ]; then
    echo "PASS: $description"
  else
    echo "FAIL: $description"
    failures=$((failures + 1))
  fi
}

has_text() {
  [ -f "$1" ] && strings "$1" | grep -q "$2"
}

has_symbol() {
  [ -f "$1" ] && "$NM" "$1" | grep -q " $2\$"
}

build() {
  # build <description> [environment assignment]
  description="$1"
  shift
  rm -f build/aplite/pebble-app.bin build/aplite/pebble-app.elf \
        build/basalt/pebble-app.bin build/basalt/pebble-app.elf
  if env "$@" "$PEBBLE" build > /dev/null 2>&1; then
    echo "PASS: $description"
  else
    echo "FAIL: $description"
    failures=$((failures + 1))
  fi
}

build "test build links for every platform" QT_TEST_BUILD=1
check "aplite test build has TEST_STATE" 0 has_text build/aplite/pebble-app.bin TEST_STATE
check "basalt test build has TEST_STATE" 0 has_text build/basalt/pebble-app.bin TEST_STATE

build "release build links for every platform" QT_TEST_BUILD=0
check "aplite release build has no TEST_STATE" 1 has_text build/aplite/pebble-app.bin TEST_STATE
check "aplite release build exists" 0 test -f build/aplite/pebble-app.bin
check "basalt release build has TEST_STATE" 0 has_text build/basalt/pebble-app.bin TEST_STATE
check "aplite release build has no app_message_open" 1 has_symbol build/aplite/pebble-app.elf app_message_open
check "aplite release build has app_timer_register (symbol check works)" 0 has_symbol build/aplite/pebble-app.elf app_timer_register
check "basalt release build has app_message_open" 0 has_symbol build/basalt/pebble-app.elf app_message_open

if [ "$failures" -ne 0 ]; then
  echo "$failures build check(s) failed"
  exit 1
fi
echo "All build checks passed"
