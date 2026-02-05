# Specification: Backlight Control

## Overview
This specification adds automatic backlight control to improve usability. The backlight will turn on during alarm (when the timer is vibrating) and while in any edit mode, making the display easier to read in these important states. The backlight automatically turns off after 30 seconds or when transitioning to counting mode.

## Requirements

### 1. Backlight On During Alarm
When the timer starts vibrating (`timer_is_vibrating()` becomes true), the backlight should turn on.

### 2. Backlight On During Edit Modes
When entering any edit mode (`ControlModeNew`, `ControlModeEditSec`, `ControlModeEditRepeat`), the backlight should turn on.

### 3. Backlight Off in Counting Mode
When transitioning to `ControlModeCounting` (and not vibrating), the backlight should turn off.

### 4. 30-Second Timeout
Any time the backlight is turned on, a 30-second timeout timer starts. If the timeout expires, the backlight turns off. The timeout resets each time the backlight is explicitly turned on (e.g., button press in edit mode).

### 5. Button Handler Integration
At the end of each button handler, determine the final state and set the backlight accordingly:
- If in edit mode OR timer is vibrating → backlight on (with 30s timeout)
- Otherwise → backlight off

## Technical Design

### Helper Function
```c
static AppTimer *backlight_timer = NULL;

static void prv_backlight_timer_callback(void *data) {
  backlight_timer = NULL;
  light_enable(false);
}

static void prv_set_backlight(bool on) {
  // Cancel existing timer
  if (backlight_timer) {
    app_timer_cancel(backlight_timer);
    backlight_timer = NULL;
  }

  light_enable(on);

  if (on) {
    backlight_timer = app_timer_register(30000, prv_backlight_timer_callback, NULL);
  }
}
```

### State Check Helper
```c
static bool prv_is_edit_mode(void) {
  return main_data.control_mode == ControlModeNew ||
         main_data.control_mode == ControlModeEditSec ||
         main_data.control_mode == ControlModeEditRepeat;
}
```

### Usage Pattern
At the end of each button handler:
```c
prv_set_backlight(prv_is_edit_mode() || timer_is_vibrating());
```

### Alarm Start Detection
In `prv_app_timer_callback`, when alarm starts (detected at lines 576-584):
```c
if (!was_elapsed && is_elapsed) {
  test_log_state("alarm_start");
  prv_set_backlight(true);  // Add this line
}
```

## Test Cases

### Test 1: Backlight turns on when alarm starts

**Purpose:** Verify backlight activates when timer elapses and starts vibrating.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Set a 3-second timer | Timer shows 0:03 |
| 2 | Wait for timer to start | Timer counting down |
| 3 | Wait for alarm | Alarm vibrates, backlight turns on |

**Verification:**
- Backlight is on when alarm is vibrating

### Test 2: Backlight turns on in edit mode

**Purpose:** Verify backlight activates when entering edit mode.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Set a 1-minute timer and let it run | Timer counting down |
| 2 | Press Up to enter edit mode | Header shows "Edit", backlight turns on |

**Verification:**
- Backlight turns on when entering `ControlModeNew`

### Test 3: Backlight turns off when entering counting mode

**Purpose:** Verify backlight turns off when edit mode expires to counting mode.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Set a 1-minute timer | Timer in edit mode, backlight on |
| 2 | Wait for edit mode to expire (~3s) | Timer starts counting, backlight turns off |

**Verification:**
- Backlight turns off when transitioning from edit mode to counting mode

### Test 4: Backlight stays on when pressing buttons in edit mode

**Purpose:** Verify button presses in edit mode keep backlight on and reset timeout.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enter edit mode | Backlight on |
| 2 | Press Up to increment | Backlight stays on, timeout resets |
| 3 | Press Down to decrement | Backlight stays on, timeout resets |

**Verification:**
- Backlight remains on during edit mode interactions

### Test 5: Backlight turns off after 30-second timeout

**Purpose:** Verify the 30-second safety timeout works.

**Note:** This test requires the edit mode to somehow stay active for 30 seconds (which normally isn't possible due to the 3-second edit expiry). This is a safety net for edge cases. Manual testing may be needed, or the test could mock/disable the edit expiry timer.

### Test 6: Backlight off after silencing alarm (not entering edit)

**Purpose:** Verify backlight turns off when alarm is silenced without entering edit mode.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Let timer elapse and alarm | Backlight on, vibrating |
| 2 | Press Back to silence | Alarm stops, backlight turns off |

**Verification:**
- Backlight turns off when alarm is silenced (Back button doesn't enter edit mode)

### Test 7: Backlight stays on when silencing alarm into edit mode

**Purpose:** Verify backlight stays on when alarm is silenced by entering edit mode.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Let timer elapse and alarm | Backlight on, vibrating |
| 2 | Press Up to enter edit mode | Alarm stops, enters edit mode, backlight stays on |

**Verification:**
- Backlight remains on because we're now in edit mode

## Dependencies
- None (uses standard Pebble `light_enable()` API)

## Implementation Notes

### Files to Modify

**src/main.c:**
1. Add `static AppTimer *backlight_timer = NULL;` near other static variables
2. Add `prv_backlight_timer_callback()` function
3. Add `prv_set_backlight(bool on)` helper function
4. Add `prv_is_edit_mode()` helper function (or inline the check)
5. Add `prv_set_backlight(true)` in `prv_app_timer_callback` when alarm starts
6. Add `prv_set_backlight(prv_is_edit_mode() || timer_is_vibrating())` at end of each button handler:
   - `prv_back_click_handler`
   - `prv_up_click_handler`
   - `prv_up_long_click_handler`
   - `prv_select_click_handler`
   - `prv_select_long_click_handler`
   - `prv_down_click_handler`
   - `prv_down_long_click_handler`
7. Cancel `backlight_timer` in `prv_window_unload` if it exists

### Button Handlers Summary

| Handler | Final State Check Location |
|---------|---------------------------|
| `prv_back_click_handler` | Before `test_log_state` |
| `prv_up_click_handler` | Before `test_log_state` (multiple return points) |
| `prv_up_long_click_handler` | Before `test_log_state` |
| `prv_select_click_handler` | Before `test_log_state` |
| `prv_select_long_click_handler` | Before `test_log_state` (multiple return points) |
| `prv_down_click_handler` | Before `test_log_state` |
| `prv_down_long_click_handler` | Before `test_log_state` |

**Note:** For handlers with multiple return points, add the backlight call before each return or refactor to have a single exit point.

## Progress
- 2026-02-05: Spec created.

## Status
**Not Started**

## Tests
**NA**
