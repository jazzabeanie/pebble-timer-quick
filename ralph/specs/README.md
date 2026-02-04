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
