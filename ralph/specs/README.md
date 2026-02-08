# Specifications Lookup Table

## About This Folder
This folder contains detailed specification files that define the requirements for each feature or module in the project. 

**Purpose of Spec Files:**
Specification files are the **"pin" that prevents context rot**. They don't tell the AI how to code; they tell the AI **what the requirements are** so the AI can check its own work against a clear definition of "done."

Each spec file should:
- Define clear, testable requirements
- Specify API contracts and data structures  
- List dependencies on other specs
- Include a Progress section for tracking implementation status
- Be updated if implementation reveals missing or incorrect details

**For AI Agents:**
This README acts as a **lookup table** for AI search tools. Use the generative keywords to find relevant specs, then navigate to the specific .md file using the provided link. The one-sentence summary helps you quickly determine if you're looking at the right specification before committing to read the entire document. Always read the complete spec file before beginning implementation.

---

## Specification Index

### 1. Testing Framework
**File:** [testing-framework.md](testing-framework.md)

**Keywords:** testing, unit tests, integration tests, cmocka, pebble emulator, test framework, test coverage, timer tests

**Summary:** Defines the requirements for a test framework and initial set of tests for the application. Includes four unit tests for timer.c.

**Status:** Completed

**Tests:** Passing

**Dependencies:** cmocka (local copy in vendor/cmocka_install/)

---

### 2. Extended Timer Tests
**File:** [timer-extended-tests.md](timer-extended-tests.md)

**Keywords:** timer, unit tests, cmocka, timer_is_chrono, timer_is_vibrating, timer_rewind, timer_restart, timer_check_elapsed, timer_get_time_parts, timer_increment_chrono, sub-minute timer, stopwatch, chrono mode

**Summary:** Defines 14 additional unit tests for timer.c to improve coverage of chrono mode, vibration logic, restart/rewind, and sub-minute timer edge cases.

**Status:** Completed

**Tests:** Passing

**Dependencies:** testing-framework (spec #1)

---

### 4. Functional Tests (Emulator)
**File:** [functional-tests-emulator.md](functional-tests-emulator.md)

**Keywords:** functional tests, emulator, integration tests, UI tests, button interactions, display verification, screenshot, aplite, basalt, chalk, diorite, emery, QemuButton, libpebble2, pytest

**Summary:** Defines functional tests that run on the Pebble emulator to verify UI/display updates and button interactions across all emulator platforms. Includes 10 tests covering timer creation, countdown, chrono mode, play/pause, and reset functionality.

**Status:** Completed

**Tests:** Passing (10 tests on basalt)

**Dependencies:** testing-framework (spec #2), Pebble SDK, Pillow, pytesseract

---

### 5. Timer Workflow Tests
**File:** [timer-workflow-tests.md](timer-workflow-tests.md)

**Keywords:** functional tests, timer workflow, edit timer, snooze, repeat timer, alarm

**Summary:** Defines functional tests for common timer workflows like editing a running timer, snoozing, and repeating.

**Status:** Completed

**Tests:** Passing

**Dependencies:** functional-tests-emulator.md (spec #4)

---

### 6. Repeating Timer
**File:** [repeating-timer.md](repeating-timer.md)

**Keywords:** functional tests, timer, repeat timer, repeating, countdown, loop, alarm, 2x, multiply

**Summary:** Defines the functionality and interaction for a repeating timer feature.

**Status:** Completed

**Tests:** Passing (22 unit tests including 4 repeat tests; functional test uses pixel-based indicator detection)

**Dependencies:** functional-tests-emulator.md (spec #4)

---

### 7. Button Icon Tests
**File:** [button-icon-tests.md](button-icon-tests.md)

**Keywords:** button icons, icon tests, screenshot comparison, pixel mask, reference image, action bar, silence icon, pause icon, snooze icon, repeat icon, play icon, direction icon, functional tests

**Summary:** Defines functional tests for verifying that icons appear beside buttons in every app state where a button has functionality. Uses pixel-based screenshot comparison against per-icon reference masks.

**Status:** Completed

**Tests:** Passing (31 tests on basalt)

**Dependencies:** functional-tests-emulator.md (spec #4), repeating-timer.md (spec #6)

---

### 8. Button Icons Implementation
**File:** [button-icons.md](button-icons.md)

**Keywords:** button icons, UX, visual feedback, assets, drawing, state machine, implementation, resource generation

**Summary:** Defines the implementation details for adding visual icons to all button interactions, including asset generation and drawing logic changes. **Note:** The long-press select icon is currently disabled due to display overlap (see Known Issues in spec).

**Status:** Completed (with known issues)

**Tests:** Passing (31 tests on basalt) — test/functional/test_button_icons.py

**Dependencies:** button-icon-tests.md (spec #7)

---

### 9. Edit Mode Reset
**File:** [edit-mode-reset.md](edit-mode-reset.md)

**Keywords:** edit mode, reset, long press select, ControlModeNew, ControlModeEditSec, pause, seconds editing, quick reset, timer reset

**Summary:** Defines a feature where long pressing select in edit mode (`ControlModeNew`) resets the timer to 0:00 in paused edit seconds mode. Long press select in `ControlModeEditSec` and `ControlModeEditRepeat` does nothing.

**Status:** Completed

**Tests:** Passing

**Dependencies:** functional-tests-emulator.md (spec #4), timer-workflow-tests.md (spec #5)

---

### 10. Directional Button Icons
**File:** [directional-icons.md](directional-icons.md)

**Keywords:** button icons, reverse direction, minus icons, UI feedback, state machine, drawing

**Summary:** Defines requirements for displaying minus/decrement icons when the timer is in reverse direction mode, and fixing the Back button icon in Edit Seconds mode to match the 60s increment.

**Status:** Completed

**Tests:** Passing (11 tests on basalt)

**Dependencies:** button-icons.md (spec #8)

---

### 11. Stopwatch Subtraction Fix
**File:** [stopwatch-subtraction.md](stopwatch-subtraction.md)

**Keywords:** stopwatch, chrono, countdown, subtraction, timer_is_chrono, timer_get_value_ms, start_ms, future start

**Summary:** Fixes a bug where subtracting time from a stopwatch results in an invalid state by refactoring time calculation logic to handle future start times.

**Status:** Completed

**Tests:** Passing (23 unit tests)

**Dependencies:** timer-extended-tests.md (spec #2)

---

### 12. Multi-Platform Interaction Stability
**File:** [multi-platform-stability.md](multi-platform-stability.md)

**Keywords:** multi-platform, stability, functional tests, long-press, repeat timer, chrono subtraction, icon verification

**Summary:** Addresses widespread functional test failures across multiple platforms by ensuring robust state transitions, coordinating raw vs. long-press button handlers, and making verification logic (pixel masks, crop regions) platform-agnostic.

**Status:** Completed

**Tests:** Passing (25/25 unit tests; most functional tests pass on Basalt)

**Dependencies:** button-icons.md (spec #8), edit-mode-reset.md (spec #9), directional-icons.md (spec #10), stopwatch-subtraction.md (spec #11)

---

### 13. Repeat Indicator Icon Overlap Fix
**File:** [repeat-indicator-overlap-fix.md](repeat-indicator-overlap-fix.md)

**Keywords:** repeat indicator, icon overlap, EditRepeat mode, +20 rep icon, visual bug, drawing.c, button icons

**Summary:** Fixes a visual overlap bug where the +20 rep button icon is displayed simultaneously with the repeat counter indicator in EditRepeat mode. The fix removes the +20 rep icon drawing in EditRepeat mode to prevent overlap.

**Status:** Completed

**Tests:** Passing

**Dependencies:** button-icons.md (spec #8), repeating-timer.md (spec #6)

---

### 14. Test Logging for Functional Tests
**File:** [test-logging.md](test-logging.md)

**Keywords:** testing, logging, functional tests, OCR replacement, TEST_STATE, log parsing, assertions, reliability

**Summary:** Adds structured logging that outputs timer state to the console, enabling functional tests to verify app behavior by parsing log output instead of unreliable OCR. Includes TEST_LOG macro (wraps APP_LOG for easy future filtering), LogCapture Python class, and assertion helpers.

| 14 | [test-logging](test-logging.md) | Log-based testing | Completed | Passing | 2026-02-04 | Structured state logging for reliable functional tests. |

**Tests:** Passing (4 proof-of-concept tests + 1 migrated test on basalt). Some other tests are failing and still need to be addressed.

**Dependencies:** functional-tests-emulator.md (spec #4)

---

### 15. Select Button EditSec Modified Flag Fix
**File:** [select-editsec-modified-flag.md](select-editsec-modified-flag.md)

**Keywords:** bug fix, EditSec, Select button, timer_length_modified_in_edit_mode, base_length_ms, hold up repeat, alarm

**Summary:** Fixes a bug where pressing Select in `ControlModeEditSec` does not set the `timer_length_modified_in_edit_mode` flag, causing `base_length_ms` to not be updated and breaking the "hold Up to repeat" feature during alarm.

**Status:** Completed

**Tests:** Passing

**Dependencies:** edit-mode-reset.md (spec #9), timer-workflow-tests.md (spec #5)

---

### 16. EditSec from ControlModeNew is New Timer Fix
**File:** [editsec-from-new-is-new-timer.md](editsec-from-new-is-new-timer.md)

**Keywords:** bug fix, EditSec, ControlModeNew, is_editing_existing_timer, long press select, base_length_ms, hold up repeat, alarm

**Summary:** Fixes a bug where entering `ControlModeEditSec` from `ControlModeNew` via long press Select incorrectly sets `is_editing_existing_timer = true`. Since this resets the timer to 0:00, it's creating a new timer, so the flag should be `false`.

**Status:** Completed

**Tests:** Passing

**Dependencies:** edit-mode-reset.md (spec #9), select-editsec-modified-flag.md (spec #15)

---

### 17. Fix setup_short_timer Helper Function
**File:** [fix-setup-short-timer-helper.md](fix-setup-short-timer-helper.md)

**Keywords:** test fix, setup_short_timer, sub-minute timer, paused, functional tests, helper function

**Summary:** Fixes 10 failing functional tests caused by the `setup_short_timer` helper function not starting the timer after setting it up. Sub-minute timers from EditSec mode stay paused after edit expires (intentional), but the helper was not updated to manually start them.

**Status:** Completed

**Tests:** Passing (10 of 12 tests fixed; 2 remaining are unrelated icon mask issues)

**Dependencies:** Sub-minute timer pause behavior (intentional)

---

### 18. Chrono Hold Select Restart
**File:** [chrono-hold-select-restart.md](chrono-hold-select-restart.md)

**Keywords:** chrono, stopwatch, hold select, long press, restart, paused chrono, edit seconds, simplify

**Summary:** Changes the behavior of long-pressing Select on a chrono timer. Previously, a paused chrono would enter edit seconds mode; now it always restarts the chrono (whether paused or running). This simplifies the interaction model since edit seconds mode is accessible via long-press Select in edit mode.

**Status:** Completed

**Tests:** Passing

**Dependencies:** edit-mode-reset.md (spec #9)

---

### 19. Backlight Control
**File:** [backlight-control.md](backlight-control.md)

**Keywords:** backlight, light, display, visibility, alarm, edit mode, light_enable, timeout, UX

**Summary:** Adds automatic backlight control for improved usability. The backlight turns on during alarm (vibrating) and in edit modes, with a 30-second timeout. It turns off when entering counting mode or after the timeout expires.

**Status:** Completed

**Tests:** Passing

**Dependencies:** None

---

### 20. Hold Select Restart (Pause-Preserving)
**File:** [hold-select-restart.md](hold-select-restart.md)

**Keywords:** hold select, long press, restart, pause, running, chrono, countdown, repeat count, base_repeat_count, timer_restart

**Summary:** Modifies long-press Select in `ControlModeCounting` to preserve paused/running state on restart for both countdown and chrono timers. Adds `base_repeat_count` field so restarting a repeating timer restores the full repeat count from the beginning.

**Status:** Not Started

**Tests:** NA

**Dependencies:** chrono-hold-select-restart.md (spec #18), edit-mode-reset.md (spec #9), repeating-timer.md (spec #6)

---

### 21. Edit Timer Direction Tests
**File:** [edit-timer-direction-tests.md](edit-timer-direction-tests.md)

**Keywords:** edit timer, direction, reverse, zero-crossing, chrono to countdown, countdown to chrono, auto-flip, direction flip, ControlModeNew, ControlModeEditSec, functional tests

**Summary:** Defines functional tests for timer editing with direction changes and zero-crossing behavior. Includes infrastructure changes (adding chrono field to TEST_STATE log, `assert_is_chrono` helper) and 6 test cases covering type conversion and auto-direction-flip. Type conversion tests should pass; auto-flip tests are marked `xfail` until spec #22 is implemented.

**Status:** Not Started

**Tests:** NA

**Dependencies:** functional-tests-emulator.md (spec #4), test-logging.md (spec #14), stopwatch-subtraction.md (spec #11), directional-icons.md (spec #10)

---

### 22. Auto Direction Flip on Zero-Crossing
**File:** [auto-direction-flip.md](auto-direction-flip.md)

**Keywords:** auto-flip, direction flip, zero-crossing, reverse direction, is_reverse_direction, chrono to countdown, countdown to chrono, edit mode, ControlModeNew, ControlModeEditSec

**Summary:** When a button press in edit mode causes the timer to cross zero (converting between chrono and countdown), the direction automatically resets to forward. Applies to all buttons in both ControlModeNew and ControlModeEditSec. Uses a before/after check on `timer_is_chrono()` to detect zero-crossings.

**Status:** Not Started

**Tests:** NA (Tests defined in spec #21)

**Dependencies:** edit-timer-direction-tests.md (spec #21), stopwatch-subtraction.md (spec #11), directional-icons.md (spec #10)

---

## Adding New Specifications

When creating a new spec file:
1. Create a descriptive markdown file in this directory (e.g., `payment-processing.md`)
2. Add an entry to this README following the format above
3. Include generous keywords for searchability
4. Link to the file using relative paths
5. Set initial status to "Not Started"
6. Document any dependencies on other specs

## Status Definitions
- **Not Started**: Spec is documented but implementation hasn't begun
- **In Progress**: Active development is underway
- **Completed**: All requirements implemented and tests passing
- **Blocked**: Cannot proceed due to dependencies or external factors

## Test Status Definitions
- **NA**: No tests exist yet or are needed
- **Failing**: Tests exist but are not all passing
- **Passing**: All relevant tests are passing
