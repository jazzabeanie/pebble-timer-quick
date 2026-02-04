# Specification: Fix setup_short_timer Helper Function

## Overview
This specification addresses failing functional tests caused by the `setup_short_timer` helper function not starting the timer after setting it up. Sub-minute timers from EditSec mode intentionally stay paused after edit mode expires (per spec behavior), but the helper function was not updated to manually start the timer.

## Bug Description

### Root Cause
A previous change made sub-minute timers (set via EditSec mode) stay paused after edit mode expires. This is intentional behavior verified by `TestSubMinuteTimerStaysPaused`. However, the `setup_short_timer` helper functions in the test files were not updated to account for this.

### Current Behavior
The `setup_short_timer` function:
1. Enters EditSec mode via long press Select
2. Adds seconds via Down button presses
3. Waits for edit mode to expire
4. Returns with timer in Counting mode but **PAUSED**

The docstring even documents step 7 ("Press Select to unpause") but this was never implemented.

### Expected Behavior
The `setup_short_timer` function should:
1. Enter EditSec mode via long press Select
2. Add seconds via Down button presses
3. Wait for edit mode to expire
4. **Press Select to start the timer**
5. Return with timer in Counting mode and **RUNNING**

### Affected Tests
The following 12 tests fail because they expect the timer to be running after `setup_short_timer`:

**test_button_icons.py (7 tests):**
- TestAlarmIcons::test_alarm_back_icon_silence
- TestAlarmIcons::test_alarm_up_icon_repeat
- TestAlarmIcons::test_alarm_long_up_icon_reset
- TestAlarmIcons::test_alarm_select_icon_pause
- TestAlarmIcons::test_alarm_down_icon_snooze
- TestChronoIcons::test_chrono_select_icon
- TestEditRepeatIcons::test_editrepeat_back_icon

**test_timer_workflows.py (5 tests):**
- TestSnoozeCompletedTimer::test_snooze_completed_timer
- TestRepeatCompletedTimer::test_repeat_completed_timer
- TestQuietAlarmBackButton::test_quiet_alarm_with_back_button
- TestPauseCompletedTimer::test_pause_completed_timer
- TestEditCompletedTimer::test_edit_completed_timer_add_minute

## Requirements

### 1. Update setup_short_timer in test_timer_workflows.py
Add `emulator.press_select()` after waiting for edit mode to expire to start the timer.

### 2. Update setup_short_timer in test_button_icons.py
Add `emulator.press_select()` after waiting for edit mode to expire to start the timer.

### 3. Update Comments
Fix the outdated comment that says "The app automatically unpauses when transitioning to Counting mode" - this is no longer true for sub-minute timers.

## Implementation Notes

### Code Changes Required

**File:** `test/functional/test_timer_workflows.py`
**Function:** `setup_short_timer` (lines 93-143)

Add after line 141 (after `time.sleep(3.5)`):
```python
# Step 7: Press Select to start the timer (sub-minute timers stay paused after edit expires)
emulator.press_select()
time.sleep(0.3)
```

Also update the comment on line 140 from:
```python
# The app automatically unpauses when transitioning to Counting mode.
```
to:
```python
# Sub-minute timers stay paused after edit expires, so we need to start manually.
```

**File:** `test/functional/test_button_icons.py`
**Function:** `setup_short_timer` (lines 195-227)

Add after line 225 (after `time.sleep(3.5)`):
```python
# Press Select to start the timer (sub-minute timers stay paused after edit expires)
emulator.press_select()
time.sleep(0.3)
```

Also update the comment on line 224.

## Test Cases

After the fix, all 12 previously failing tests should pass.

## Dependencies
- Sub-minute timer pause behavior (intentional, tested by `TestSubMinuteTimerStaysPaused`)

## Progress
- 2026-02-05: Spec created based on test failure analysis.

## Status
**Not Started**

## Tests
**Failing** - 12 tests currently fail due to this issue
