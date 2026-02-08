# Specification: Edit Timer Direction Tests

## Overview
Defines functional tests for timer editing behavior related to direction (add/subtract time), zero-crossing (chrono ↔ countdown type conversion), and auto-direction-flip when crossing zero. These tests support the auto-direction-flip feature defined in spec #22.

The test suite verifies:
1. **Type conversion**: When subtracting time past zero, the timer correctly converts between chrono and countdown modes (both directions)
2. **Auto-direction-flip**: When a zero-crossing occurs during editing, the direction automatically resets to forward (positive icons)
3. **Continued editing**: After an auto-flip, subsequent button presses work in the default (forward) direction

## Keywords
edit timer, direction, reverse, zero-crossing, chrono to countdown, countdown to chrono, auto-flip, direction flip, ControlModeNew, ControlModeEditSec, functional tests

## Requirements

### 1. Test Infrastructure Changes

#### 1a. Add `c` (chrono) field to TEST_STATE log
**File:** `src/utility.c`

The `test_log_state()` function must be updated to include a `c` field indicating whether the timer is in chrono mode:
- `c=1` — timer is chrono (counting up)
- `c=0` — timer is countdown (counting down)

This field should call `timer_is_chrono()` to determine the value.

Updated format:
```
TEST_STATE:<event>,t=M:SS,m=<mode>,r=<n>,p=<0|1>,v=<0|1>,d=<1|-1>,l=<0|1>,c=<0|1>
```

#### 1b. Add `assert_is_chrono` helper to conftest.py
**File:** `test/functional/conftest.py`

Add a new assertion helper:
```python
def assert_is_chrono(state: dict, is_chrono: bool = True):
    """Assert whether timer is in chrono mode.

    Note: State uses short field name 'c' for chrono.
    """
    expected = '1' if is_chrono else '0'
    actual = state.get('c', '')
    assert actual == expected, (
        f"Expected timer to be {'chrono' if is_chrono else 'countdown'}, "
        f"but timer is {'chrono' if actual == '1' else 'countdown'}"
    )
```

#### 1c. Update `test_stopwatch_subtraction.py` assertion messages
**File:** `test/functional/test_stopwatch_subtraction.py`

Update `test_chrono_subtraction_converts_to_countdown` to add an explicit chrono assertion:
```python
assert_is_chrono(state_sub, is_chrono=False)
```
This ensures the test fails with a clear message ("Expected timer to be countdown, but timer is chrono") if the chrono → countdown conversion breaks.

### 2. Test File
**File:** `test/functional/test_edit_timer_direction.py`

All new tests go in this file. Tests are organized into two classes:
- `TestZeroCrossingTypeConversion` — Tests that verify existing type conversion behavior (should pass)
- `TestAutoDirectionFlip` — Tests that verify the new auto-flip feature (marked `xfail` until spec #22 is implemented)

## Test Cases

### Test 1: Countdown to chrono via subtraction in ControlModeNew

**Class:** `TestZeroCrossingTypeConversion`

**Purpose:** Verify that subtracting enough time from a countdown timer to go past zero converts it to a chrono timer.

**Expected result:** Should pass (existing behavior).

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Press Down twice to set 2-minute timer | ControlModeNew, time 2:00 |
| 2 | Wait 4s for auto-start | ControlModeCounting, countdown ~1:56 |
| 3 | Press Up to enter edit mode | ControlModeNew, direction forward |
| 4 | Long press Up to toggle reverse direction | Direction reverse |
| 5 | Press Up (subtract 20 minutes) | Timer crosses zero → chrono ~18:04 |

**Verification:**
- Step 5: `assert_is_chrono(state, is_chrono=True)` — "Expected timer to convert from countdown to chrono after subtracting past zero"
- Step 5: `assert_time_approximately(state, minutes=18, seconds=4, tolerance=10)`

---

### Test 2: Countdown to chrono via subtraction in ControlModeEditSec

**Class:** `TestZeroCrossingTypeConversion`

**Purpose:** Verify countdown → chrono conversion works in ControlModeEditSec.

**Expected result:** Should pass (existing behavior).

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Wait 2.5s for chrono mode | ControlModeCounting, chrono at ~0:02 |
| 2 | Press Up to enter ControlModeNew | ControlModeNew |
| 3 | Long press Select to enter EditSec at 0:00 | ControlModeEditSec, paused at 0:00 |
| 4 | Press Down 5 times (+5 seconds) | Time shows 0:05 |
| 5 | Long press Up to toggle reverse | Direction reverse |
| 6 | Press Back (subtract 60 seconds) | Timer crosses zero → chrono ~0:55 |

**Verification:**
- Step 6: `assert_is_chrono(state, is_chrono=True)` — "Expected timer to convert from countdown to chrono after subtracting past zero in EditSec"
- Step 6: `assert_time_approximately(state, minutes=0, seconds=55, tolerance=5)`

---

### Test 3: Auto-flip after chrono → countdown in ControlModeNew

**Class:** `TestAutoDirectionFlip`

**Purpose:** Verify that when subtracting from a chrono timer causes it to cross zero and become a countdown, the direction automatically flips to forward.

**Expected result:** Fails until spec #22 is implemented. Mark with `@pytest.mark.xfail(reason="Auto-direction-flip not yet implemented (spec #22)")`.

**Preconditions:**
- App launches fresh (auto-enters chrono after ~3.5s).

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Wait 5s for chrono mode with elapsed time | Chrono ~0:02 |
| 2 | Press Up to enter ControlModeNew | ControlModeNew, direction forward |
| 3 | Long press Up to toggle reverse | Direction reverse |
| 4 | Press Down (subtract 1 minute) | Timer crosses zero → countdown ~0:58, direction auto-flips to forward |

**Verification:**
- Step 4: `assert_is_chrono(state, is_chrono=False)` — "Expected chrono to convert to countdown after subtracting past zero"
- Step 4: `assert_direction(state, forward=True)` — "Expected direction to auto-flip to forward after zero-crossing"
- Step 4: `assert_time_approximately(state, minutes=0, seconds=58, tolerance=10)`

---

### Test 4: Auto-flip after countdown → chrono in ControlModeNew

**Class:** `TestAutoDirectionFlip`

**Purpose:** Verify that when subtracting from a countdown timer causes it to cross zero and become a chrono, the direction automatically flips to forward.

**Expected result:** Fails until spec #22 is implemented. Mark with `@pytest.mark.xfail`.

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Press Down twice to set 2-minute timer | ControlModeNew, time 2:00 |
| 2 | Wait 4s for auto-start | ControlModeCounting, countdown ~1:56 |
| 3 | Press Up to enter edit mode | ControlModeNew, direction forward |
| 4 | Long press Up to toggle reverse | Direction reverse |
| 5 | Press Up (subtract 20 minutes) | Timer crosses zero → chrono ~18:04, direction auto-flips to forward |

**Verification:**
- Step 5: `assert_is_chrono(state, is_chrono=True)` — "Expected countdown to convert to chrono after subtracting past zero"
- Step 5: `assert_direction(state, forward=True)` — "Expected direction to auto-flip to forward after zero-crossing"
- Step 5: `assert_time_approximately(state, minutes=18, seconds=4, tolerance=10)`

---

### Test 5: Auto-flip after countdown → chrono in ControlModeEditSec

**Class:** `TestAutoDirectionFlip`

**Purpose:** Verify auto-direction-flip works in ControlModeEditSec.

**Expected result:** Fails until spec #22 is implemented. Mark with `@pytest.mark.xfail`.

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Wait 2.5s for chrono mode | ControlModeCounting |
| 2 | Press Up to enter ControlModeNew | ControlModeNew |
| 3 | Long press Select to enter EditSec at 0:00 | ControlModeEditSec, paused at 0:00 |
| 4 | Press Down 5 times (+5 seconds) | Time shows 0:05 (countdown) |
| 5 | Long press Up to toggle reverse | Direction reverse |
| 6 | Press Back (subtract 60 seconds) | Timer crosses zero → chrono ~0:55, direction auto-flips to forward |

**Verification:**
- Step 6: `assert_is_chrono(state, is_chrono=True)` — "Expected countdown to convert to chrono after subtracting past zero in EditSec"
- Step 6: `assert_direction(state, forward=True)` — "Expected direction to auto-flip to forward after zero-crossing in EditSec"
- Step 6: `assert_time_approximately(state, minutes=0, seconds=55, tolerance=5)`

---

### Test 6: Continued editing after auto-flip in ControlModeNew

**Class:** `TestAutoDirectionFlip`

**Purpose:** Verify that after an auto-direction-flip, subsequent button presses work in the new forward direction (adding time to the now-countdown timer).

**Expected result:** Fails until spec #22 is implemented. Mark with `@pytest.mark.xfail`.

**Preconditions:**
- App launches fresh (auto-enters chrono after ~3.5s).

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Wait 5s for chrono mode with elapsed time | Chrono ~0:02 |
| 2 | Press Up to enter ControlModeNew | ControlModeNew, direction forward |
| 3 | Long press Up to toggle reverse | Direction reverse |
| 4 | Press Down (subtract 1 minute) | Crosses zero → countdown ~0:58, direction forward (auto-flip) |
| 5 | Press Down (add 1 minute in forward direction) | Countdown ~1:58 |

**Verification:**
- Step 4: `assert_direction(state, forward=True)` — auto-flip occurred
- Step 4: `assert_is_chrono(state, is_chrono=False)` — now countdown
- Step 5: `assert_time_approximately(state, minutes=1, seconds=58, tolerance=10)` — "Expected adding 1 minute after auto-flip to increase countdown time"
- Step 5: `assert_direction(state, forward=True)` — still forward

---

### Test 7: Round-trip zero-crossing in ControlModeEditSec

**Class:** `TestAutoDirectionFlip`

**Purpose:** Verify that two consecutive zero-crossings (countdown → chrono → countdown) both trigger auto-direction-flip, and the timer returns to approximately its original value.

**Expected result:** Fails until spec #22 is implemented. Mark with `@pytest.mark.xfail`.

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected State |
|------|--------|----------------|
| 1 | Wait 2.5s, press Up, long press Select | ControlModeEditSec at 0:00 |
| 2 | Press Down 5 times (+5 seconds) | Time 0:05 (countdown) |
| 3 | Long press Up to toggle reverse | Direction reverse |
| 4 | Press Back (subtract 60 seconds) | Crosses zero → chrono ~0:55, direction forward (1st auto-flip) |
| 5 | Long press Up to toggle reverse | Direction reverse |
| 6 | Press Back (subtract 60 seconds) | Crosses zero → countdown ~0:05, direction forward (2nd auto-flip) |

**Verification:**
- Step 4: `assert_is_chrono(state, is_chrono=True)` — converted to chrono
- Step 4: `assert_direction(state, forward=True)` — 1st auto-flip
- Step 6: `assert_is_chrono(state, is_chrono=False)` — converted back to countdown
- Step 6: `assert_direction(state, forward=True)` — 2nd auto-flip
- Step 6: `assert_time_approximately(state, minutes=0, seconds=5, tolerance=3)` — approximately back to original value

## Dependencies
- **functional-tests-emulator.md** (spec #4): Test infrastructure and patterns
- **test-logging.md** (spec #14): Log-based test assertions
- **stopwatch-subtraction.md** (spec #11): Existing chrono ↔ countdown math
- **directional-icons.md** (spec #10): Direction toggle behavior

## File Structure
```
src/
├── utility.c                          # Add 'c' field to TEST_STATE
test/
├── functional/
│   ├── conftest.py                    # Add assert_is_chrono helper
│   ├── test_stopwatch_subtraction.py  # Update with assert_is_chrono
│   └── test_edit_timer_direction.py   # New test file
```

## Status
**Not Started**

## Tests
**NA**
