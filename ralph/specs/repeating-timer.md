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
- The initial display shall show "_x", which is equivalent to 1x (no actual repeat). This means enabling repeat mode alone does not cause the timer to repeat.
- To repeat the timer, the user must increase the count by pressing the Down button. Each press increments the count by 1. Two Down presses are needed to reach "2x" (the minimum useful repeat count).
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
- **Tests:** Passing (22 unit tests including 4 repeat tests; functional test `test_enable_repeating_timer` uses pixel-based indicator detection)

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

### 2026-01-26: Initial display changed from 2x to _x
- **main.c - `prv_up_long_click_handler`**: Changed initial `repeat_count` from 2 to 0 when enabling repeat mode. Now displays "_x" (equivalent to 1x / no repeat). User must press Down twice to reach "2x" for actual repeating.
- **drawing.c**: Already handled `repeat_count == 0` as "_x" display. No changes needed.
- **Unit tests**: Added test 22 (`test_timer_check_elapsed_repeat_zero_count`) verifying that `repeat_count = 0` does not trigger repeat restart, behaves as normal timer vibration.
- **Functional test**: Updated `test_enable_repeating_timer` to verify "_x" initial display, then press Down twice to reach "2x" before verifying repeat restart behavior.

### Key Decisions
- **Initial repeat_count = 0 (displayed as "_x")**: When entering repeat edit mode, `repeat_count` starts at 0 (displayed as "_x"). This is equivalent to 1x (no actual repeat). The user must press Down twice to reach "2x" (the minimum useful repeat count). This gives the user explicit control over enabling actual repeating behavior.
- **Indicator hidden at count ≤ 1**: The "Nx" indicator is only shown when `repeat_count > 1`. When count is 0 or 1, no indicator is shown outside of EditRepeat mode since these are equivalent to a normal timer.
- **Flashing indicator**: In `ControlModeEditRepeat`, the indicator flashes (500ms on, 500ms off). In `ControlModeCounting`, it's static.

### 2026-01-26: Functional test rewritten with pixel-based indicator detection
- **Problem**: OCR (EasyOCR) could not reliably detect the small "_x" and "2x" indicator text in the top-right corner. Additionally, the `pebble screenshot` command takes ~1.0s, creating perfect aliasing with the 1000ms flash cycle — every screenshot landed at phase=550ms (OFF).
- **Solution**: Replaced OCR-based indicator assertions with pixel-based detection. The indicator text is rendered in pure white (255,255,255) against the green background. Detection is done by counting white pixels in the crop region `(94, 0, 144, 30)` for basalt. The "2x" indicator is verified by comparing the white pixel mask against a stored reference (`ref_basalt_2x_mask.png`).
- **Timing fix**: Added a 0.5s delay before the first screenshot to shift the flash phase into the ON window. Reduced initial screenshots to 1 (from 4) to stay within the 3-second `new_expire_timer` before pressing Down.
- **New helpers**: `has_repeat_indicator()`, `matches_indicator_reference()`, `load_indicator_reference()` in `test_create_timer.py`.
- **Reference image**: `test/functional/screenshots/ref_basalt_2x_mask.png` — 50x30 grayscale image with the white pixel positions of the "2x" indicator (104 white pixels).
