# Specification: Select Button in EditSec Mode Missing Modified Flag

## Overview
This specification addresses a bug where pressing the Select button in `ControlModeEditSec` does not set the `timer_length_modified_in_edit_mode` flag, even though it modifies the timer's length. This causes `base_length_ms` to not be updated when the edit mode expires, which in turn causes the "hold Up to repeat" feature to fail during alarm.

## Bug Description

### Current Behavior
When pressing Select in `ControlModeEditSec`:
1. The timer length is incremented by 5 seconds via `prv_update_timer(SELECT_BUTTON_INCREMENT_SEC_MS)`
2. The `timer_length_modified_in_edit_mode` flag is **NOT** set to `true`

This is inconsistent with the Down and Up button handlers in EditSec mode, which DO set this flag when modifying the timer.

### Expected Behavior
When pressing Select in `ControlModeEditSec`:
1. The timer length is incremented by 5 seconds
2. The `timer_length_modified_in_edit_mode` flag **IS** set to `true`

### Impact
When `timer_length_modified_in_edit_mode` is not set, and `is_editing_existing_timer` is `true`, the condition in `prv_new_expire_callback` evaluates to `false`:

```c
if (!main_data.is_editing_existing_timer || main_data.timer_length_modified_in_edit_mode) {
  timer_data.base_length_ms = timer_data.length_ms;
}
```

This means `base_length_ms` is not updated, and when the user holds Up during alarm to repeat the timer, the check `if (timer_data.base_length_ms > 0)` fails and the timer does not restart.

## Requirements

### 1. Set Modified Flag in Select Handler for EditSec Mode
**Location:** `prv_select_click_handler` in `src/main.c`

**Change:** Add `main_data.timer_length_modified_in_edit_mode = true;` after the `prv_update_timer()` call for `ControlModeEditSec`.

### 2. Consistency Check
Verify that all button handlers that modify timer length in edit modes set the `timer_length_modified_in_edit_mode` flag:
- Up button in EditSec: Sets flag (line 271)
- Down button in EditSec: Sets flag (line 525)
- Select button in EditSec: **Missing** - needs fix
- Back button in EditSec: Sets flag (line 213)

## Test Cases

### Test 1: Hold Up during alarm repeats timer (Select button setup)

**Purpose:** Verify that a timer set using the Select button in EditSec mode can be repeated by holding Up during alarm.

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Long press Select to enter EditSec mode | Timer at 0:00 in EditSec mode |
| 2 | Press Select twice to add 10 seconds | Timer shows 0:10 |
| 3 | Wait for edit mode to expire (~3.5s) | Timer in Counting mode, paused |
| 4 | Press Select to start timer | Timer counting down from 0:10 |
| 5 | Wait for alarm | Timer vibrating at 0:00 |
| 6 | Hold Up button | Alarm stops, timer restarts at 0:10 |

**Verification Details:**
- Step 6: Verify `alarm_stop` event is logged
- Step 6: Verify `long_press_up` event shows time ~0:10 and mode "Counting"

### Test 2: Consistency between Select and Down button setup

**Purpose:** Verify that timers set via Select button behave identically to timers set via Down button.

**Preconditions:**
- App launches fresh.

**Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Long press Select to enter EditSec mode | Timer at 0:00 in EditSec mode |
| 2 | Press Select twice (adds 10 seconds) | Timer shows 0:10 |
| 3 | Wait for expire, start timer, wait for alarm | Timer alarming |
| 4 | Hold Up to repeat | Timer restarts at 0:10 |

This should behave identically to using Down button 10 times to add 10 seconds.

## Dependencies
- **edit-mode-reset.md** (spec #9): Defines EditSec mode entry via long press Select
- **timer-workflow-tests.md** (spec #5): Related workflow tests

## Implementation Notes

### Code Changes Required (src/main.c)

**File:** `src/main.c`
**Function:** `prv_select_click_handler`
**Lines:** ~356-358

**Current code:**
```c
case ControlModeEditSec:
  prv_update_timer(SELECT_BUTTON_INCREMENT_SEC_MS);
  break;
```

**Fixed code:**
```c
case ControlModeEditSec:
  prv_update_timer(SELECT_BUTTON_INCREMENT_SEC_MS);
  main_data.timer_length_modified_in_edit_mode = true;
  break;
```

## Progress
- 2026-02-05: Spec created based on bug analysis.
- 2026-02-05: Implementation completed. Added `main_data.timer_length_modified_in_edit_mode = true;` to EditSec case in `prv_select_click_handler` (line 358).
- 2026-02-05: Tests verified. Before: 13 failed, 69 passed. After: 12 failed, 70 passed. The test `test_hold_up_during_longer_alarm_repeats_timer[basalt]` now passes.

## Status
**Completed**

## Tests
**Passing** - The existing test `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_longer_alarm_repeats_timer[basalt]` validates this fix.

## Pre-existing Failing Tests (Unrelated)
The following tests were failing before this fix and remain failing after (unrelated to this change):
- test_button_icons.py::TestAlarmIcons::test_alarm_back_icon_silence[basalt]
- test_button_icons.py::TestAlarmIcons::test_alarm_up_icon_repeat[basalt]
- test_button_icons.py::TestAlarmIcons::test_alarm_long_up_icon_reset[basalt]
- test_button_icons.py::TestAlarmIcons::test_alarm_select_icon_pause[basalt]
- test_button_icons.py::TestAlarmIcons::test_alarm_down_icon_snooze[basalt]
- test_button_icons.py::TestChronoIcons::test_chrono_select_icon[basalt]
- test_button_icons.py::TestEditRepeatIcons::test_editrepeat_back_icon[basalt]
- test_timer_workflows.py::TestSnoozeCompletedTimer::test_snooze_completed_timer[basalt]
- test_timer_workflows.py::TestRepeatCompletedTimer::test_repeat_completed_timer[basalt]
- test_timer_workflows.py::TestQuietAlarmBackButton::test_quiet_alarm_with_back_button[basalt]
- test_timer_workflows.py::TestPauseCompletedTimer::test_pause_completed_timer[basalt]
- test_timer_workflows.py::TestEditCompletedTimer::test_edit_completed_timer_add_minute[basalt]
