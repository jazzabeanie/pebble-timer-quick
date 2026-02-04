# Specification: EditSec from ControlModeNew is a New Timer

## Overview
This specification addresses a bug where entering `ControlModeEditSec` from `ControlModeNew` via long press Select incorrectly sets `is_editing_existing_timer = true`. Since long press Select resets the timer to 0:00, this is creating a new timer, not editing an existing one. The flag should be `false`.

## Bug Description

### Current Behavior
When long pressing Select in `ControlModeNew`:
1. Timer is reset to 0:00 via `timer_reset()`
2. Timer is paused at 0 elapsed
3. Control mode changes to `ControlModeEditSec`
4. `is_editing_existing_timer` is set to `true`

### Expected Behavior
When long pressing Select in `ControlModeNew`:
1. Timer is reset to 0:00 via `timer_reset()`
2. Timer is paused at 0 elapsed
3. Control mode changes to `ControlModeEditSec`
4. `is_editing_existing_timer` should be set to `false` (this is a new timer, not editing existing)

### Rationale
The `is_editing_existing_timer` flag is used to determine whether `base_length_ms` should be updated when edit mode expires. The logic in `prv_new_expire_callback` is:

```c
if (!main_data.is_editing_existing_timer || main_data.timer_length_modified_in_edit_mode) {
  timer_data.base_length_ms = timer_data.length_ms;
}
```

The intent is:
- If creating a **new** timer (`is_editing_existing_timer = false`): always update `base_length_ms`
- If editing an **existing** timer (`is_editing_existing_timer = true`): only update `base_length_ms` if the user actually modified the length

When you long press Select in ControlModeNew, you're resetting to 0:00 and starting fresh. This is semantically creating a new timer, so `is_editing_existing_timer` should be `false` to ensure `base_length_ms` is always updated when edit mode expires.

### Impact
When `is_editing_existing_timer` is incorrectly set to `true`, and the user only uses buttons that don't set `timer_length_modified_in_edit_mode` (like Select in EditSec - see related spec), the `base_length_ms` is not updated. This causes "hold Up to repeat" during alarm to fail.

### Comparison with Similar Code Paths

| Entry Path to EditSec | `is_editing_existing_timer` | Correct? |
|----------------------|---------------------------|----------|
| Paused chrono + long press Select | Not set (stays `false`) | Yes |
| ControlModeNew + long press Select | Set to `true` | **No** - should be `false` |
| ControlModeCounting + press Up (existing timer) | Set to `true` | Yes |

## Requirements

### 1. Set `is_editing_existing_timer = false` When Entering EditSec from ControlModeNew

**Location:** `prv_select_long_click_handler` in `src/main.c`

**Change:** When handling long press Select in `ControlModeNew`, set `is_editing_existing_timer = false` instead of `true`.

## Test Cases

### Test 1: Timer set via long press Select from ControlModeNew can be repeated

**Purpose:** Verify that entering EditSec directly from ControlModeNew (without going through chrono mode first) produces a timer that can be repeated via hold Up during alarm.

**Preconditions:**
- App launches fresh in ControlModeNew.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Long press Select | Enter EditSec mode at 0:00 |
| 2 | Press Down 5 times to add 5 seconds | Timer shows 0:05 |
| 3 | Wait for edit mode to expire (~3.5s) | Timer in Counting mode, paused |
| 4 | Press Select to start timer | Timer counting down from 0:05 |
| 5 | Wait for alarm | Timer vibrating at 0:00 |
| 6 | Hold Up button | Alarm stops, timer restarts at 0:05 |

**Verification Details:**
- Step 6: Verify `alarm_stop` event is logged
- Step 6: Verify `long_press_up` event shows time ~0:05 and mode "Counting"

### Test 2: Both entry paths to EditSec behave identically

**Purpose:** Verify that timers created via direct EditSec entry (long press Select from ControlModeNew) behave identically to timers created via the chrono-pause-reset path.

**Test A - Direct path:**
1. App starts in ControlModeNew
2. Long press Select to enter EditSec
3. Add seconds, wait for expire, start, wait for alarm
4. Hold Up to repeat

**Test B - Chrono path:**
1. App starts in ControlModeNew
2. Wait for auto-transition to chrono mode
3. Pause chrono
4. Long press Select to enter EditSec
5. Add seconds, wait for expire, start, wait for alarm
6. Hold Up to repeat

Both paths should produce identical behavior - the timer should restart when holding Up during alarm.

## Dependencies
- **edit-mode-reset.md** (spec #9): Defines the long press Select behavior in ControlModeNew
- **select-editsec-modified-flag.md**: Related bug fix for Select button in EditSec mode

## Implementation Notes

### Code Changes Required (src/main.c)

**File:** `src/main.c`
**Function:** `prv_select_long_click_handler`
**Lines:** ~407-420

**Current code:**
```c
// In ControlModeNew: reset to 0:00 in paused edit seconds mode
if (main_get_control_mode() == ControlModeNew) {
  timer_reset();
  timer_data.start_ms = 0;  // Pause at 0 elapsed
  timer_data.is_paused = true;
  main_data.control_mode = ControlModeEditSec;
  prv_stop_new_expire_timer();
  main_data.is_editing_existing_timer = true;  // <-- BUG
  main_data.timer_length_modified_in_edit_mode = false;
  // ...
}
```

**Fixed code:**
```c
// In ControlModeNew: reset to 0:00 in paused edit seconds mode
if (main_get_control_mode() == ControlModeNew) {
  timer_reset();
  timer_data.start_ms = 0;  // Pause at 0 elapsed
  timer_data.is_paused = true;
  main_data.control_mode = ControlModeEditSec;
  prv_stop_new_expire_timer();
  main_data.is_editing_existing_timer = false;  // <-- FIXED: This is a new timer
  main_data.timer_length_modified_in_edit_mode = false;
  // ...
}
```

## Progress
- 2026-02-05: Spec created based on bug analysis.

## Status
**Not Started**

## Tests
**NA** - Tests will be added with implementation
