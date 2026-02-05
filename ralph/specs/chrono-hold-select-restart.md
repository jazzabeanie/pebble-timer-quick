# Specification: Chrono Hold Select Restart

## Overview
This specification changes the behavior of long-pressing the Select button while in chrono (stopwatch) mode. Previously, if the chrono was paused, holding Select would reset and enter edit seconds mode. This behavior is removed—now holding Select on a chrono timer (whether paused or running) will always restart the chrono from 0:00.

This simplifies the interaction model since entering edit seconds mode is already available via long-press Select in `ControlModeNew` (edit mode).

## Requirements

### 1. Long Press Select in ControlModeCounting with Chrono
**Current behavior:**
- If chrono is **running**: Reset and restart chrono at 0:00 in `ControlModeCounting`
- If chrono is **paused**: Reset to 0:00 and enter `ControlModeEditSec`

**New behavior:**
- Whether paused or running: Reset and restart chrono at 0:00 in `ControlModeCounting`

### 2. No Change to Other Modes
The following existing behaviors remain unchanged:
- Long press Select in `ControlModeNew`: Reset to 0:00 in paused edit seconds mode
- Long press Select in `ControlModeEditSec`: No-op
- Long press Select in `ControlModeEditRepeat`: No-op
- Long press Select in `ControlModeCounting` with countdown timer: Restart timer

## Test Cases

### Test 1: Long press select on paused chrono restarts chrono

**Purpose:** Verify that long pressing Select on a paused chrono timer restarts it instead of entering edit seconds mode.

**Preconditions:**
- App is running with a chrono timer paused at some value.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start app fresh | Timer at 0:00, paused |
| 2 | Press Select to start chrono | Chrono counting up from 0:00 |
| 3 | Wait 3 seconds | Chrono shows ~0:03 |
| 4 | Press Select to pause | Chrono paused at ~0:03 |
| 5 | Long press Select | Chrono restarts at 0:00, running |

**Verification:**
- After step 5: Timer shows 0:00 (or very close), is running (not paused), and is in `ControlModeCounting` (not edit mode)

### Test 2: Long press select on running chrono still restarts (unchanged)

**Purpose:** Verify existing behavior for running chrono is preserved.

**Preconditions:**
- App is running with a chrono timer actively counting.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start app fresh | Timer at 0:00, paused |
| 2 | Press Select to start chrono | Chrono counting up |
| 3 | Wait 5 seconds | Chrono shows ~0:05 |
| 4 | Long press Select (while running) | Chrono restarts at 0:00, still running |

**Verification:**
- After step 4: Timer shows 0:00 (or very close), is running, in `ControlModeCounting`

### Test 3: Edit seconds mode still accessible via edit mode

**Purpose:** Verify users can still access edit seconds mode through the intended path.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start app fresh | Timer at 0:00, paused |
| 2 | Press Select to start chrono | Chrono counting up |
| 3 | Press Up to enter edit mode | Header shows "Edit", enters `ControlModeNew` |
| 4 | Long press Select | Timer resets to 0:00, enters `ControlModeEditSec` |
| 5 | Press Down to add 1 second | Timer shows 0:01 |

**Verification:**
- Step 4: Enters edit seconds mode (not counting mode)
- Step 5: Down adds seconds (confirming edit seconds mode)

## Dependencies
- edit-mode-reset.md (spec #9): Long press Select in `ControlModeNew` behavior

## Implementation Notes

### Code Changes Required (src/main.c)

**Modify `prv_select_long_click_handler`** (lines ~424-438):

Current code:
```c
if (main_data.control_mode == ControlModeCounting) {
  if (timer_is_chrono()) {
    if (timer_is_paused()) {
      // Paused Chrono -> Paused New Timer (0:00) -> Edit Seconds
      timer_reset();
      timer_data.start_ms = 0; // Pause at 0 elapsed
      timer_data.is_paused = true;
      main_data.control_mode = ControlModeEditSec;
      prv_stop_new_expire_timer();
    } else {
      // Running Chrono -> Counting New Timer (0:00)
      timer_reset();
      // timer_reset sets start_ms to epoch(), so it starts running
      main_data.control_mode = ControlModeCounting;
    }
  } else {
    timer_restart();
  }
}
```

New code:
```c
if (main_data.control_mode == ControlModeCounting) {
  if (timer_is_chrono()) {
    // Chrono (paused or running) -> Restart chrono at 0:00
    timer_reset();
    // timer_reset sets start_ms to epoch(), so it starts running
    main_data.control_mode = ControlModeCounting;
  } else {
    timer_restart();
  }
}
```

The change removes the `if (timer_is_paused())` branch, making both paused and running chrono behave the same way.

## Progress
- 2026-02-05: Spec created.

## Status
**Not Started**

## Tests
**NA**
