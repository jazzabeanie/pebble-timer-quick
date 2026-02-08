# Specification: Hold Select Restart (Pause-Preserving)

## Overview
This specification modifies the long-press Select behavior in `ControlModeCounting` to preserve the timer's paused/running state on restart. Previously, chrono restarts always paused the timer. Now both countdown and chrono restarts preserve whether the timer was running or paused.

Additionally, a `base_repeat_count` field is added so that restarting a repeating timer restores the full repeat count from the beginning.

## Requirements

### 1. Long Press Select in ControlModeCounting — Countdown Timer
**Current behavior (unchanged):**
- Calls `timer_restart()`, which preserves paused/running state
- Running countdown restarts running from `base_length_ms`
- Paused countdown restarts paused at `base_length_ms`

### 2. Long Press Select in ControlModeCounting — Chrono Timer
**Current behavior:**
- Calls `timer_reset()`, which always pauses and clears everything to 0:00
- Running chrono ends up paused at 0:00 (user must manually resume)

**New behavior:**
- Calls `timer_restart()`, which preserves paused/running state
- Running chrono restarts running from 0:00
- Paused chrono restarts paused at 0:00

### 3. Long Press Select During Alarm
**Current behavior (unchanged for countdown):**
- The raw handler (`prv_select_raw_click_handler`) cancels vibration on initial press-down
- The long-press handler then calls `timer_restart()`, restarting the countdown running
  - not sure if the above line is an error or if there is a bug, because it starts a paused chrono timer from zero.

**New behavior for chrono alarm:**
- Same as countdown: raw handler cancels vibration, long-press restarts via `timer_restart()`. It should do what holding the up button currently does.

### 4. Repeat Count Restoration on Restart
**Current behavior:**
- `timer_restart()` does not touch `repeat_count` or `is_repeating`
- If repeats have been partially consumed, the remaining count is whatever is left

**New behavior:**
- A new `base_repeat_count` field stores the original repeat count set by the user
- `timer_restart()` restores `repeat_count` from `base_repeat_count` when `is_repeating` is true
- This means restarting always starts the full repeat cycle from the beginning

### 5. No Change to Other Modes
The following existing behaviors remain unchanged:
- Long press Select in `ControlModeNew`: Reset to 0:00 in paused edit seconds mode
- Long press Select in `ControlModeEditSec`: No-op
- Long press Select in `ControlModeEditRepeat`: No-op

## Test Cases

### Test 1: Restart running countdown preserves running state
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create a 1-minute timer, let it start counting | Timer counting down from 1:00 |
| 2 | Wait a few seconds | Timer shows ~0:57 |
| 3 | Long press Select | Timer restarts at 1:00, still running |

**Verification:**
- After step 3: Timer shows 1:00 (or close), is running (not paused), in `ControlModeCounting`

### Test 2: Restart paused countdown preserves paused state
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create a 1-minute timer, let it start counting | Timer counting down from 1:00 |
| 2 | Press Select to pause | Timer paused at ~0:57 |
| 3 | Long press Select | Timer restarts at 1:00, still paused |

**Verification:**
- After step 3: Timer shows 1:00, is paused, in `ControlModeCounting`

### Test 3: Restart running chrono preserves running state
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start app fresh, press Select to start chrono | Chrono counting up from 0:00 |
| 2 | Wait a few seconds | Chrono shows ~0:03 |
| 3 | Long press Select | Chrono restarts at 0:00, still running |

**Verification:**
- After step 3: Timer shows 0:00 (or very close), is running, in `ControlModeCounting`

### Test 4: Restart paused chrono preserves paused state
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start app fresh, press Select to start chrono | Chrono counting up from 0:00 |
| 2 | Wait a few seconds, press Select to pause | Chrono paused at ~0:03 |
| 3 | Long press Select | Chrono restarts at 0:00, still paused |

**Verification:**
- After step 3: Timer shows 0:00, is paused, in `ControlModeCounting`

### Test 5: Restart repeating timer restores full repeat count
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create a short timer (e.g., 5 seconds) | Timer set |
| 2 | Enable repeating with count of 3 | `is_repeating = true`, `repeat_count = 3` |
| 3 | Let timer expire once (repeat fires) | `repeat_count` decremented to 2 |
| 4 | Long press Select to restart | Timer restarts, `repeat_count` restored to 3 |

**Verification:**
- After step 4: `repeat_count == 3`, `base_repeat_count == 3`, timer is running

### Test 6: Restart during alarm
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create a short countdown timer, let it expire | Timer alarming (vibrating) |
| 2 | Long press Select | Vibration cancelled, timer restarts running from base_length |

**Verification:**
- After step 2: Timer shows original duration, is running, no vibration

### Test 7: Other modes unchanged
**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enter ControlModeNew (press Up from Counting) | In edit mode |
| 2 | Long press Select | Resets to 0:00 in ControlModeEditSec (unchanged) |
| 3 | Long press Select again (in EditSec) | No-op (unchanged) |

## Dependencies
- chrono-hold-select-restart.md (spec #18): Previous chrono restart behavior being modified
- edit-mode-reset.md (spec #9): Long press Select in ControlModeNew behavior (unchanged)
- repeating-timer.md (spec #6): Repeat count mechanics

## Implementation Notes

### Code Changes Required

#### 1. `src/timer.h` — Add `base_repeat_count` field

Add to the `Timer` struct:
```c
uint8_t     base_repeat_count; //< The original repeat count set by the user (for restart)
```

#### 2. `src/timer.c` — Bump persist version

Change `PERSIST_VERSION` from 4 to 5.

#### 3. `src/timer.c` — Update `timer_restart()`

Add repeat count restoration:
```c
void timer_restart(void) {
  if (timer_data.base_length_ms > 0) {
      timer_data.length_ms = timer_data.base_length_ms;
  } else {
      timer_data.length_ms = 0;
  }

  if (timer_data.is_paused) {
      timer_data.start_ms = 0;
  } else {
      timer_data.start_ms = epoch();
  }

  if (timer_data.length_ms > 0) {
    timer_data.can_vibrate = true;
  } else {
    timer_data.can_vibrate = false;
  }

  // Restore repeat count from base
  if (timer_data.is_repeating) {
    timer_data.repeat_count = timer_data.base_repeat_count;
  }

  timer_data.auto_snooze_count = 0;
  timer_data.elapsed = false;
}
```

#### 4. `src/timer.c` — Update `timer_reset()`

Clear `base_repeat_count`:
```c
timer_data.base_repeat_count = 0;
```

#### 5. `src/main.c` — Simplify `prv_select_long_click_handler` ControlModeCounting branch

Replace the chrono/countdown split with a single `timer_restart()` call:

Current code (lines ~424-432):
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

New code:
```c
if (main_data.control_mode == ControlModeCounting) {
    timer_restart();
  }
```

Both chrono and countdown are now handled uniformly by `timer_restart()`, which checks `base_length_ms` to determine the mode and preserves the paused/running state.

#### 6. `src/main.c` — Save `base_repeat_count` in `prv_new_expire_callback`

When transitioning from `ControlModeEditRepeat` to `ControlModeCounting`, save the base:
```c
if (main_data.control_mode == ControlModeEditRepeat) {
  timer_data.base_repeat_count = timer_data.repeat_count;
}
```

Add this before the `main_data.control_mode = ControlModeCounting;` line.

#### 7. `src/main.c` — Clear `base_repeat_count` when toggling repeat off

In `prv_up_long_click_handler`, when `is_repeating` is toggled off:
```c
} else {
    timer_data.repeat_count = 0;
    timer_data.base_repeat_count = 0;  // Add this line
    main_data.control_mode = ControlModeCounting;
}
```

## Progress
- 2026-02-08: Spec created.

## Status
**Not Started**

## Tests
**NA**
