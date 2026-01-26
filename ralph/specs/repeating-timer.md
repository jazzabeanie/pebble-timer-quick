# Specification: Repeating Timer

## 1. Overview
This specification defines the functionality for a repeating timer. Users can enable this feature to have a timer automatically restart a set number of times after it completes.

**Keywords:** repeating timer, timer, repeat, loop, countdown, alarm

## 2. Requirements

### 2.1. Activation
- When a timer is actively counting down, a long press (hold) of the **Up button** for at least 750ms shall enable "repeat edit mode."
- This action should only be available while the timer is in `ControlModeCounting`. The timer may or may not be paused.

### 2.2. Repeat Edit Mode
- Upon entering "repeat edit mode," a flashing indicator shall appear in the top-right corner of the display.
- A "2x", for example, indicates the timer will run a total of two times (the initial run + one repeat).
- The UI shall exit "repeat edit mode" automatically after 3 seconds of inactivity, saving the selected repeat count.

### 2.3. Visual Indicator
- When a repeating timer is active and counting down, a static indicator (e.g., "2x", "3x") shall be displayed in the top-right corner.
- This indicator should be visible throughout the countdown.

### 2.4. Deactivation
- When a repeating timer is active (either counting down or paused), a long press of the **Up button** for at least 750ms shall disable the repeating functionality.
- The repeat indicator ("Nx") shall be removed from the display.

### 2.5. Timer Completion and Restart
- When a repeating timer completes its countdown, it will vibrate briefly before starting the next timer.
- After the first completion, if there are repeats remaining, the timer will automatically restart with its original duration.
- The repeat indicator will decrement (e.g., from "3x" to "2x").
- When the final timer in the sequence completes, it will behave as a normal timer, entering chrono mode (counting up).

### 2.6. Interaction with Other Features
- **Snooze:** If the user presses the **Down button** (snooze) after the *final* alarm of a repeating sequence, the timer will add 5 minutes and behave like a normal snoozed timer. Snoozing during an intermediate alarm should not be possible, and the timer should just restart.
- **Repeat:** If the user holds the **Up button** while a *completed* repeating timer is in its alarm state, it shall repeat the original timer value *one* time, regardless of the original repeat count.
- **Pause:** A repeating timer can be paused and resumed like a normal timer. The repeat setting is retained.
- **Edit:** Editing a running repeating timer (e.g., adding time with a single Up press) shall preserve the repeat setting.
- **Chrono Mode:** A long press of the **Up button** while in chrono mode (after a timer has fully completed) shall have no effect.

## 3. Technical Details
- This functionality was removed by commit 6c1eaee9055b135e9aa62f6773fe46d7f4543e5a. Please look at that to see the working code and integrate apply it onto of the current HEAD. That code should align with the other technical details below.
- A new persistent storage key should be used to store the repeat count for a timer.
- The `prv_handle_alarm()` function in `main.c` will need to be modified to check for and handle the repeat logic.
- The `up_long_click_handler` in `main.c` will need to be updated to handle enabling/disabling the repeat feature.

## 4. Dependencies
- Relies on the existing timer functionality defined in `timer.c`.
- Relies on functional tests defined in `functional-tests-emulator.md`.

## 5. Status
- **Status:** Completed
- **Tests:** Passing (21 unit tests, functional test `test_enable_repeating_timer` passing on basalt)

## 6. Progress

### 2026-01-26: Implementation Complete
- **main.c - `prv_up_long_click_handler`**: Modified to toggle repeat mode on/off when in `ControlModeCounting`. Long press Up enables repeat with `repeat_count = 2` (minimum useful value) and enters `ControlModeEditRepeat`. No effect in chrono mode (spec 2.6). When vibrating, long press Up now clears repeat state before extending timer.
- **main.c - `prv_down_click_handler`**: Modified to handle intermediate alarm snooze (spec 2.6). When vibrating and `is_repeating && repeat_count > 1`, pressing Down restarts the timer (decrements count, adds base_length_ms) instead of normal 5-minute snooze.
- **drawing.c - repeat indicator format**: Changed from "x2" to "2x" format to match spec (e.g., "2x", "3x").
- **timer.c - `timer_check_elapsed()`**: Already handles repeat logic correctly (decrements count, calls `timer_increment(base_length_ms)`, vibrates with `vibes_long_pulse()`). No changes needed.
- **timer.c - `timer_reset()`**: Already clears `is_repeating` and `repeat_count`. Verified with unit test.
- **Unit tests**: Added 3 new tests (tests 19-21): `test_timer_check_elapsed_repeat_final` (final repeat doesn't restart), `test_timer_reset_clears_repeat`, `test_timer_check_elapsed_repeat_decrements_to_final` (2→1 decrement and restart).
- **Functional test**: Removed `@pytest.mark.xfail` marker from `test_enable_repeating_timer`. Updated test to handle flashing indicator in `ControlModeEditRepeat` (takes 4 screenshots to catch flash), and verify restart via header "00:20" pattern.
- **has_time_pattern()**: Added `seconds` parameter to support sub-minute time assertions.

### Key Decisions
- **Initial repeat_count = 2**: When entering repeat edit mode, `repeat_count` starts at 2 (the minimum useful value) rather than 0 as in the removed code. This means "long press Up" immediately sets up a "run twice" timer.
- **Indicator hidden at count=1**: The "Nx" indicator is only shown when `repeat_count > 1`. When count is 1 (final run), no indicator is shown since "1x" is equivalent to a normal timer.
- **Flashing indicator**: In `ControlModeEditRepeat`, the indicator flashes (500ms on, 500ms off). In `ControlModeCounting`, it's static.
