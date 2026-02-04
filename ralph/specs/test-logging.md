# Specification: Test Logging for Functional Tests

## Overview
This specification defines a structured logging system that outputs timer state to the console, enabling functional tests to verify app behavior by parsing log output instead of relying on OCR image recognition. This approach is more reliable than OCR, which struggles with the custom LECO 7-segment font.

## Motivation
Current functional tests use EasyOCR to read the display, but this has reliability issues:
- The LECO 7-segment font causes frequent digit confusion (0/8, 5/6, 1/7)
- Extensive workaround code exists to handle OCR errors (`has_time_pattern()`, `normalize_time_text()`)
- OCR is slow (~2-3 seconds per image), requiring careful timing to avoid interfering with app behavior
- Small text (like repeat indicators) is particularly unreliable

Structured logging provides exact state values without ambiguity.

## Requirements

### 1. TEST_LOG Macro

Create a `TEST_LOG` macro in `src/utility.h` that currently wraps `APP_LOG`:

```c
//! ============================================================================
//! TEST_LOG: Structured logging for functional test assertions
//! ============================================================================
//!
//! PURPOSE:
//! This macro enables functional tests to verify app state by parsing log
//! output instead of using unreliable OCR on screenshots. Tests run
//! `pebble logs` to capture these structured log lines.
//!
//! WHY WRAP APP_LOG?
//! Currently this just calls APP_LOG, but wrapping it allows us to easily
//! disable test logging in production builds later by changing this one macro.
//!
//! TO DISABLE IN PRODUCTION (Option B - zero overhead):
//! Replace the #define below with:
//!   #ifdef TEST_BUILD
//!   #define TEST_LOG(level, fmt, ...) APP_LOG(level, fmt, ##__VA_ARGS__)
//!   #else
//!   #define TEST_LOG(level, fmt, ...) ((void)0)
//!   #endif
//! Then add -DTEST_BUILD to CFLAGS in wscript for emulator/test builds.
//!
//! ============================================================================
#define TEST_LOG(level, fmt, ...) APP_LOG(level, fmt, ##__VA_ARGS__)
```

This design allows easy migration to Option B (compile-time filtering) by adding the `#ifdef` wrapper later.

### 2. Structured State Log Format

Add a function that logs the complete timer state in a parseable format:

```c
void test_log_state(const char *event);
```

The log output format is a single line with key=value pairs (comma-separated).
Field names are abbreviated to fit within APP_LOG's ~100 character limit:

```
TEST_STATE:<event>,t=<M>:<SS>,m=<mode_name>,r=<count>,p=<0|1>,v=<0|1>,d=<1|-1>
```

**Fields:**
| Field | Key | Description | Example Values |
|-------|-----|-------------|----------------|
| event | (prefix) | What triggered this log | `button_up`, `button_down`, `button_select`, `button_back`, `mode_change`, `init` |
| time | t | Current timer value (minutes:seconds) | `5:30`, `0:00`, `12:05` |
| mode | m | Control mode name | `New`, `Counting`, `EditSec`, `EditRepeat` |
| repeat | r | Repeat counter value | `0`, `1`, `5`, `20` |
| paused | p | Whether timer is paused | `0` (running), `1` (paused) |
| vibrating | v | Whether alarm is vibrating | `0`, `1` |
| direction | d | Increment direction | `1` (forward), `-1` (reverse) |

**Example log lines:**
```
TEST_STATE:init,t=0:00,m=New,r=0,p=1,v=0,d=1
TEST_STATE:button_down,t=1:00,m=New,r=0,p=1,v=0,d=1
TEST_STATE:button_down,t=2:00,m=New,r=0,p=1,v=0,d=1
TEST_STATE:mode_change,t=1:57,m=Counting,r=0,p=0,v=0,d=1
```

### 3. Log Trigger Points

Call `test_log_state()` at these points in the code:

| Location | Event Name | File |
|----------|------------|------|
| After app initialization | `init` | `main.c` |
| After Up button handler | `button_up` | `main.c` |
| After Down button handler | `button_down` | `main.c` |
| After Select button handler | `button_select` | `main.c` |
| After Back button handler | `button_back` | `main.c` |
| After mode transitions | `mode_change` | `main.c` |
| After long-press handlers | `long_press_<button>` | `main.c` |
| When alarm starts vibrating | `alarm_start` | `main.c` or `timer.c` |
| When alarm stops | `alarm_stop` | `main.c` |

### 4. Test Infrastructure Updates

#### 4.1 Log Capture Helper

Add a log capture mechanism to `test/functional/conftest.py`:

```python
class LogCapture:
    """Captures pebble logs in background and provides parsing."""

    def __init__(self, platform: str):
        self.platform = platform
        self.process = None
        self.log_lines = []

    def start(self):
        """Start capturing logs in background."""
        # Run: pebble logs --emulator=<platform>
        pass

    def stop(self):
        """Stop capturing and return collected logs."""
        pass

    def get_state_logs(self) -> list[dict]:
        """Parse TEST_STATE lines into dictionaries."""
        pass

    def wait_for_state(self, event: str = None, timeout: float = 5.0) -> dict:
        """Wait for next state log, optionally matching event type."""
        pass
```

#### 4.2 Updated EmulatorHelper

Extend `EmulatorHelper` to integrate log capture:

```python
class EmulatorHelper:
    def __init__(self, ...):
        ...
        self._log_capture = None

    def start_log_capture(self):
        """Start capturing logs for this emulator."""
        self._log_capture = LogCapture(self.platform)
        self._log_capture.start()

    def get_last_state(self) -> dict:
        """Get the most recent TEST_STATE log entry."""
        pass

    def wait_for_state(self, event: str = None, timeout: float = 5.0) -> dict:
        """Wait for a state log entry."""
        pass
```

#### 4.3 State Assertion Helpers

Add helper functions for common assertions:

```python
def assert_time_equals(state: dict, minutes: int, seconds: int):
    """Assert the timer shows exactly this time."""
    expected = f"{minutes}:{seconds:02d}"
    assert state['time'] == expected, f"Expected {expected}, got {state['time']}"

def assert_time_approximately(state: dict, minutes: int, seconds: int, tolerance: int = 5):
    """Assert the timer is within tolerance seconds of expected."""
    pass

def assert_mode(state: dict, mode: str):
    """Assert the control mode matches."""
    assert state['mode'] == mode, f"Expected mode {mode}, got {state['mode']}"

def assert_paused(state: dict, paused: bool = True):
    """Assert pause state."""
    expected = '1' if paused else '0'
    assert state['paused'] == expected
```

### 5. Migration Path for Existing Tests

Existing OCR-based tests should continue to work. New tests can use log-based assertions. Over time, OCR assertions can be replaced with log assertions where appropriate.

**Tests that should still use screenshots:**
- Visual appearance tests (icon tests, layout tests)
- Tests that verify what the user actually sees

**Tests that can migrate to log assertions:**
- Timer value verification
- Mode state verification
- Repeat count verification
- Pause state verification

## Implementation Notes

### Mode Name Mapping

```c
const char* get_mode_name(ControlMode mode) {
    switch (mode) {
        case ControlModeNew: return "New";
        case ControlModeCounting: return "Counting";
        case ControlModeEditSec: return "EditSec";
        case ControlModeEditRepeat: return "EditRepeat";
        default: return "Unknown";
    }
}
```

### Time Formatting

Use `timer_get_time_parts()` to get minutes and seconds for the log output.

## Dependencies

- **functional-tests-emulator.md** (spec #4): Base functional test infrastructure
- **Pebble SDK**: APP_LOG functionality

## File Changes

| File | Change |
|------|--------|
| `src/utility.h` | Add `TEST_LOG` macro |
| `src/main.c` | Add `test_log_state()` function and calls at trigger points |
| `src/main.h` | Export `test_log_state()` if needed |
| `test/functional/conftest.py` | Add `LogCapture` class and helpers |

## Future: Migration to Option B

To eliminate logging overhead in production builds:

1. Add to `wscript` in the build section:
   ```python
   # For test/emulator builds, define TEST_BUILD
   ctx.env.CFLAGS.append('-DTEST_BUILD')
   ```

2. Update `TEST_LOG` macro in `utility.h`:
   ```c
   #ifdef TEST_BUILD
   #define TEST_LOG(level, fmt, ...) APP_LOG(level, fmt, ##__VA_ARGS__)
   #else
   #define TEST_LOG(level, fmt, ...) ((void)0)
   #endif
   ```

## Progress

- [x] Create structured logging helper in `utility.c` (2026-02-04)
- [x] Implement `alarm_start` and `alarm_stop` events (2026-02-04)
- [x] Implement `timer_repeat` event (2026-02-04)
- [x] Update `test_chrono_select_icon` (2026-02-04)
- [x] Update `test_timer_transitions_to_counting_mode` (2026-02-04)
- [x] Update `test_long_press_select_resets_in_control_mode_new` (2026-02-04)
- [x] Update `test_editrepeat_shows_repeat_counter` (2026-02-04)
- [x] Update `test_chrono_subtraction_converts_to_countdown` (2026-02-04)
- [x] Update `test_snooze_completed_timer` (2026-02-04)
- [x] Update `test_repeat_completed_timer` (2026-02-04)
- [x] Update `test_quiet_alarm_with_back_button` (2026-02-04)
- [x] Update `test_pause_completed_timer` (2026-02-04)
- [x] Update `test_edit_completed_timer_add_minute` (2026-02-04)
- [x] Update `test_enable_repeating_timer` (2026-02-04)
- [x] Update `test_long_press_select_in_edit_mode_resets_to_edit_seconds` (2026-02-04)
- [x] Update `test_long_press_select_in_edit_sec_mode_does_nothing` (2026-02-04)
- [x] Update `test_long_press_select_in_edit_repeat_mode_does_nothing` (2026-02-04)

### Implementation Notes (2026-02-04)

- Field names abbreviated (t, m, r, p, v, d) to fit within APP_LOG's ~100 char limit
- Log format verified working: `TEST_STATE:mode_change,t=0:00,m=Counting,r=0,p=0,v=0,d=1`
- `test_log_state` moved to `utility.c` for global accessibility.
- `alarm_start` and `alarm_stop` logic uses a persistent `elapsed` flag in `Timer` struct to ensure reliability.
- `timer_repeat` event added for intermediate repeat restarts.
- All functional tests verified on `basalt` platform.


## Notes

- The `TEST_STATE:` prefix makes it easy to grep for state logs among other debug output
- The pipe-separated format is easy to parse while remaining human-readable
- Log capture runs in a separate process to avoid blocking test execution
- Tests may use both screenshots (for visual verification) and logs (for state verification) in the same test
