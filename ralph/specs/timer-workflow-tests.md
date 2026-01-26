# Specification: Timer Workflow Tests

## Overview
This specification defines functional tests for common user workflows that are not covered by the basic functional tests. These include editing a running timer, snoozing, repeating, and other interactions with a completed timer.

## Requirements

### 1. Test Infrastructure
- All requirements from `functional-tests-emulator.md` apply.
- A new test file `test/functional/test_timer_workflows.py` will be created.
- A pytest fixture `short_timer` will be created in `conftest.py` to simplify setting up short timers for testing.

### 2. New Fixture: `short_timer`
- **Purpose:** To create a timer with a specific short duration (e.g., 4 seconds) for tests that need a timer to run out quickly.
- **Implementation:** The fixture will take an optional duration parameter. It will perform the necessary button presses to set the timer to the desired value.

## Test Cases

### Test 1: Edit a running timer
**Purpose:** Verify that a running timer can be edited to add more time.
**Preconditions:**
- App is in `ControlModeCounting`.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Launch app and set a 2-minute timer | Header: "New", Main: "2:00" |
| 2 | Press Select to start the timer | Header: "Counting", Main: shows time decreasing from "2:00" |
| 3 | Wait 2 seconds | Main: shows time around "1:58" |
| 4 | Press Down button | Header: "Editing", Main: "2:58" (adds 1 minute) |
| 5 | Wait 2 seconds | Main: shows time decreasing from "2:58" |
**Verification Details:**
- Step 4: Verify the header changes to "Editing" and the time is increased by 1 minute.
- Step 5: Verify the timer continues counting down from the new time.

### Test 2: Set a 4-second timer
**Purpose:** Verify that a short timer can be set and requires a manual start.
**Preconditions:**
- App launches fresh.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` fixture to set a 4-second timer | Header: "New", Main: "0:04" |
| 2 | Wait 5 seconds | Header: "New", Main: "0:04" |
**Verification Details:**
- Step 2: Verify the timer has not started automatically and the display has not changed.

### Test 3: Snooze a completed timer
**Purpose:** Verify that a completed timer can be snoozed.
**Preconditions:**
- A timer is running.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` to set and start a 4-second timer | Header: "Counting", Main: "0:04" -> "0:00" |
| 2 | Wait for timer to complete | App vibrates, Header: "Alarming" or similar |
| 3 | Press Select button | Header: "Snoozed", Main: shows snooze countdown (e.g., "5:00") |
**Verification Details:**
- Step 2: Verify the device vibrates or the display indicates an alarm.
- Step 3: Verify the header changes to "Snoozed" and a new countdown has started. The default snooze time is 5 minutes.

### Test 4: Repeat a completed timer
**Purpose:** Verify that a completed timer can be repeated.
**Preconditions:**
- A timer is running.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` to set and start a 4-second timer | Header: "Counting", Main: "0:04" -> "0:00" |
| 2 | Wait for timer to complete | App vibrates, Header: "Alarming" or similar |
| 3 | Hold Up button | Header: "Counting", Main: "0:04" (restarted) |
**Verification Details:**
- Step 3: Verify the timer restarts with the original duration.

### Test 5: Quiet alarm with back button
**Purpose:** Verify the back button quiets the alarm, but the timer continues counting up.
**Preconditions:**
- A timer is running.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` to set and start a 4-second timer | Header: "Counting", Main: "0:04" -> "0:00" |
| 2 | Wait for timer to complete | App vibrates, Header: "Alarming" or similar |
| 3 | Press Back button | Alarm/vibration stops, Header: "Chrono", Main: starts counting up from "0:00" |
**Verification Details:**
- Step 3: Verify the alarm stops and the timer transitions to chrono mode, counting up.

### Test 6: Pause a completed timer
**Purpose:** Verify that a completed timer (in chrono mode) can be paused.
**Preconditions:**
- A timer has just completed.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` to set and start a 4-second timer | Header: "Counting", Main: "0:04" -> "0:00" |
| 2 | Wait for timer to complete and enter chrono mode | Header: "Chrono", Main: counting up from "0:00" |
| 3 | Wait 2 seconds | Main: shows "0:02" |
| 4 | Press Select button | Header: "Paused", Main: "0:02" (static) |
| 5 | Wait 2 seconds | Main: still "0:02" |
**Verification Details:**
- Step 4: Verify the header changes to "Paused" and the time stops counting.

### Test 7: Edit a completed timer to add a minute
**Purpose:** Verify a completed timer (in chrono mode) can be edited to add a minute.
**Preconditions:**
- A timer has just completed.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` to set and start a 4-second timer | Header: "Counting", Main: "0:04" -> "0:00" |
| 2 | Wait for timer to complete and enter chrono mode | Header: "Chrono", Main: counting up from "0:00" |
| 3 | Wait 2 seconds | Main: shows "0:02" |
| 4 | Press Up button | Header: "Editing", Main: "1:02" |
**Verification Details:**
- Step 4: Verify the header changes to "Editing" and 1 minute is added to the chrono time. The total time at the top should also be updated.

### Test 8: Enable repeating timer (Expected to Fail)
**Purpose:** Verify that holding the Up button while a timer is counting down enables a repeating timer.
**Preconditions:**
- A timer is counting down.
**Steps:**
| Step | Action | Expected Display State |
|---|---|---|
| 1 | Use `short_timer` to set and start a 4-second timer | Header: "Counting", Main: "0:04" |
| 2 | Hold Up button for 1 second | A repeat icon appears on the screen |
| 3 | Wait for timer to complete | App vibrates, then restarts the timer automatically |
**Verification Details:**
- Step 2: Verify a visual indicator for repeat mode appears.
- Step 3: Verify the timer restarts automatically after finishing.
**Status:** This test is expected to fail as there is a bug.

## Dependencies
- **functional-tests-emulator.md** (spec)

## Progress
- **Not Started**
