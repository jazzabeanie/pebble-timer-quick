# Specification: Functional Tests (Emulator)

## Overview
This specification defines functional tests that run on the Pebble emulator to verify UI/display updates and button interactions. These tests complement the existing unit tests by testing the application as a whole rather than individual functions.

## Requirements

### 1. Test Infrastructure
- **Language:** Python (to leverage existing `libpebble2` library)
- **Location:** Test scripts will be located in a new `test/functional/` directory
- **Emulator Control:** Use `libpebble2` and `QemuButton` to simulate button presses
- **Screenshot Capture:** Use `pebble screenshot` command to capture display state
- **Display Verification:** Image analysis using Pillow to detect expected text/numbers in screen regions
- **Platforms:** Tests run on all available emulator platforms: aplite, basalt, chalk, diorite, emery

### 2. Test Execution
- Tests can be run individually or as a suite across all platforms
- Each test should:
  1. Wipe emulator state to ensure a fresh start (`pebble wipe`)
  2. Build and install the app (`pebble build && pebble install --emulator <platform>`)
  3. Execute test steps (button presses, screenshot captures)
  4. Verify expected display state
  5. Report pass/fail status

### 3. Display Verification Approach
- **Primary Method:** Image analysis to detect key features (text, numbers) in expected screen regions
- **Fallback Method:** Pixel-based screenshot comparison against reference images (if text detection proves unreliable for specific tests)
- Screenshots are saved for debugging failed tests

## Test Cases

### Test 1: Create a 2-minute timer using the down button

**Purpose:** Verify that pressing the Down button in `ControlModeNew` increments the timer by 1 minute, and that the display updates correctly.

**Preconditions:**
- App launches fresh (no saved timer state)
- App starts in `ControlModeNew`

**Steps:**

| Step | Action | Expected Display State |
|------|--------|------------------------|
| 1 | Launch app (fresh state) | Header: "New", Main: shows "0:00" with "-" prefix indicator |
| 2 | Press Down button once | Header: "New", Main: shows "1:00" |
| 3 | Press Down button once | Header: "New", Main: shows "2:00" |

**Verification Details:**
- Step 1: Verify header region contains "New" text; main display region shows "0" for minutes and "00" for seconds
- Step 2: Verify main display shows "1" for minutes and "00" for seconds
- Step 3: Verify main display shows "2" for minutes and "00" for seconds

**Notes:**
- The "-" prefix in step 1 indicates the timer is in "new timer" mode with zero time set
- After each button press, a 3-second inactivity timer starts; test must complete verification before this expires (or reset the timer with another button press)

## Dependencies
- **testing-framework** (spec): For patterns and conventions
- **Pebble SDK:** In `conda-env/` directory
- **Python libraries:**
  - `libpebble2` (included with pebble-tool)
  - `Pillow` (for image analysis)

## File Structure

```
test/
├── functional/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures (emulator setup, screenshot helpers)
│   ├── test_create_timer.py  # Test case: Create 2-minute timer
│   └── screenshots/          # Directory for captured screenshots (gitignored)
├── test_timer.c              # Existing unit tests
├── pebble.h                  # Existing mock header
└── Makefile                  # Existing unit test makefile
```

## Running Tests

```bash
# Run functional tests on all platforms
cd test/functional
python -m pytest test_create_timer.py -v

# Run on a specific platform
python -m pytest test_create_timer.py -v --platform=basalt

# Run with screenshot saving for debugging
python -m pytest test_create_timer.py -v --save-screenshots
```

## Documentation Requirements

When implementation is complete, update the project root `README.md` to include a "Running Functional Tests" section after the existing "Running Tests" section:

```markdown
## Running Functional Tests

Functional tests run on the Pebble emulator to verify UI behavior and button interactions.

**Dependencies:** Python 3.10+, Pillow (`pip install Pillow`), and the Pebble SDK (in conda-env).

To run functional tests on all emulator platforms:

```bash
cd test/functional
python -m pytest test_create_timer.py -v
```

To run on a specific platform:

```bash
python -m pytest test_create_timer.py -v --platform=basalt
```

Available platforms: aplite, basalt, chalk, diorite, emery

To save screenshots for debugging:

```bash
python -m pytest test_create_timer.py -v --save-screenshots
```
```

## Progress
- 2026-01-25: Spec created.

## Notes
- The `QemuButton` class uses bitmask values: Back=1, Up=2, Select=4, Down=8
- Button press simulation requires sending a "press" state followed by a "release" state
- Allow sufficient delay between button press and screenshot to let the display update (suggest 100-200ms)
- The emulator must be running before sending button commands; `pebble install --emulator <platform>` handles this automatically
