# Button Functions by Mode

This document describes what each physical button does in every control mode of Timer++.

## Modes Overview

| Mode | Description |
|------|-------------|
| **New** | Setting a new timer in minute granularity. Entered on app launch or after pressing Up from Counting. |
| **EditSec** | Setting a timer in second granularity. Entered via long-press Select from New mode. |
| **EditRepeat** | Configuring repeat count for a timer. Entered via long-press Up from Counting mode. |
| **Counting** | Timer actively running or paused. Entered after 3 seconds of inactivity in an edit mode. |
| **Alarm** | Timer has expired and is vibrating. A transient state overlaid on Counting mode. |

## Button Increment Values

| Button | New Mode (minutes) | EditSec Mode (seconds) |
|--------|-------------------|----------------------|
| Up     | +20 min           | +20 sec              |
| Select | +5 min            | +5 sec               |
| Down   | +1 min            | +1 sec               |
| Back   | +60 min (1 hr)    | +60 sec (1 min)      |

When reverse direction is active (toggled via long-press Up), all increments become decrements.

---

## New Mode (ControlModeNew)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Add 20 minutes to timer | `test_create_timer.py::TestButtonPresses::test_up_button_increments_20_minutes`, `test_log_based.py::test_up_button_increments_20_minutes_log_based` |
| Up | Long | Toggle reverse direction (increment becomes decrement) | `test_directional_icons.py::TestNewModeReverseIcons::test_new_reverse_up_icon`, `test_stopwatch_subtraction.py::test_chrono_add_then_subtract` |
| Select | Short | Add 5 minutes to timer | `test_create_timer.py::TestButtonPresses::test_select_button_increments_5_minutes` |
| Select | Long | Switch to EditSec mode (preserving current timer value and direction) | `test_edit_mode_reset.py::test_long_press_select_toggles_new_to_editsec`, `test_timer_workflows.py::TestEditModeToggle::test_long_press_select_toggles_new_to_editsec`, `test_edit_mode_reset.py::test_toggle_new_to_editsec_preserves_reverse_direction` |
| Down | Short | Add 1 minute to timer | `test_create_timer.py::TestCreateTimer::test_down_button_increments_minutes`, `test_create_timer.py::TestCreateTimer::test_create_2_minute_timer`, `test_log_based.py::test_multiple_button_presses_log_sequence` |
| Down | Long | Quit app (sets reset flag and closes) | `test_button_icons.py::TestNewModeIcons::test_new_long_down_icon` (icon only) |
| Back | Short | Add 60 minutes (1 hour) to timer | `test_edit_mode_reset.py::test_long_press_select_resets_in_control_mode_new` (used after reset) |

**Mode transitions:**
- After 3 seconds of inactivity: auto-transitions to Counting mode (`test_create_timer.py::TestTimerCountdown::test_timer_transitions_to_counting_mode`, `test_log_based.py::test_mode_transition_via_logs`)
- Long-press Select: toggles to EditSec mode (preserving value and direction)

**Reverse direction icons:**

| Button | Forward Icon | Reverse Icon | Test |
|--------|-------------|-------------|------|
| Up | +20min | -20min | `test_directional_icons.py::TestNewModeReverseIcons::test_new_reverse_up_icon` |
| Select | +5min | -5min | `test_directional_icons.py::TestNewModeReverseIcons::test_new_reverse_select_icon` |
| Down | +1min | -1min | `test_directional_icons.py::TestNewModeReverseIcons::test_new_reverse_down_icon` |
| Back | +1hr | -1hr | `test_directional_icons.py::TestNewModeReverseIcons::test_new_reverse_back_icon` |

---

## EditSec Mode (ControlModeEditSec)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Add 20 seconds to timer | `test_timer_workflows.py::TestSetShortTimer::test_set_4_second_timer` (used to build timer) |
| Up | Long | Toggle reverse direction | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_up_icon` |
| Select | Short | Add 5 seconds to timer | `test_timer_workflows.py::TestSetShortTimer::test_set_4_second_timer` (used to build timer) |
| Select | Long | Switch to New mode (preserving current timer value and direction) | `test_edit_mode_reset.py::test_long_press_select_toggles_editsec_to_new`, `test_timer_workflows.py::TestEditModeToggle::test_long_press_select_toggles_editsec_to_new`, `test_edit_mode_reset.py::test_toggle_editsec_to_new_preserves_reverse_direction` |
| Down | Short | Add 1 second to timer | `test_timer_workflows.py::TestSetShortTimer::test_set_4_second_timer` (used to build timer) |
| Down | Long | Quit app | *(no dedicated test)* |
| Back | Short | Add 60 seconds (1 minute) to timer | `test_directional_icons.py::TestEditSecModeForwardIcons::test_editsec_forward_back_icon_plus60` |

**Reverse direction icons:**

| Button | Forward Icon | Reverse Icon | Test |
|--------|-------------|-------------|------|
| Up | +20s | -20s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_up_icon` |
| Select | +5s | -5s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_select_icon` |
| Down | +1s | -1s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_down_icon` |
| Back | +60s | -60s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_back_icon` |

**Zero-crossing tests (EditSec):**

| Test | Description |
|------|-------------|
| `test_edit_timer_direction.py::TestZeroCrossingTypeConversion::test_countdown_to_chrono_via_subtraction_editsec` | Subtracting past zero converts countdown to chrono |
| `test_edit_timer_direction.py::TestAutoDirectionFlip::test_auto_flip_countdown_to_chrono_editsec` | Direction automatically flips after zero-crossing |
| `test_edit_timer_direction.py::TestAutoDirectionFlip::test_round_trip_zero_crossing_editsec` | Two consecutive zero-crossings both trigger auto-flip |

---

## EditRepeat Mode (ControlModeEditRepeat)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Add 20 to repeat count | `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_editrepeat_shows_repeat_counter` |
| Up | Long | Toggle reverse direction | *(no dedicated test)* |
| Select | Short | Add 5 to repeat count | *(no dedicated test)* |
| Select | Long | No-op (stays in EditRepeat) | `test_edit_mode_reset.py::test_long_press_select_no_op_in_edit_repeat` (skipped), `test_timer_workflows.py::TestEditRepeatModeNoOp::test_long_press_select_in_edit_repeat_mode_does_nothing` |
| Down | Short | Add 1 to repeat count | `test_timer_workflows.py::TestEnableRepeatingTimer::test_enable_repeating_timer`, `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_editrepeat_shows_repeat_counter` |
| Down | Long | Quit app | *(no dedicated test)* |
| Back | Short | Reset repeat count to 0 | `test_timer_workflows.py::TestEditRepeatBackButton::test_back_button_resets_repeat_count_to_zero` |

---

## Counting Mode (ControlModeCounting)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Enter edit mode (New if timer > 0:00, EditSec if at 0:00) | `test_timer_workflows.py::TestEditRunningTimer::test_edit_running_timer`, `test_timer_workflows.py::TestEditCompletedTimer::test_edit_completed_timer_add_minute` |
| Up | Long | Toggle repeat mode on/off (countdown only; no-op for chrono) | `test_timer_workflows.py::TestEnableRepeatingTimer::test_enable_repeating_timer` |
| Select | Short | Toggle play/pause | `test_create_timer.py::TestPlayPause::test_select_toggles_play_pause_in_counting_mode`, `test_timer_workflows.py::TestPauseCompletedTimer::test_pause_completed_timer` |
| Select | Long (running) | Restart timer to original base_length_ms (preserves running state) | `test_hold_select_restart.py::test_restart_running_countdown_preserves_running`, `test_hold_select_restart.py::test_restart_running_chrono_preserves_running`, `test_hold_select_restart.py::test_restart_repeating_timer_restores_count`, `test_create_timer.py::TestLongPressReset::test_long_press_select_resets_timer` |
| Select | Long (paused) | Reset to 0:00 and enter EditSec mode | `test_hold_select_restart.py::test_long_press_select_paused_countdown_resets_to_editsec`, `test_hold_select_restart.py::test_long_press_select_paused_chrono_resets_to_editsec` |
| Down | Short | Extend high-refresh display rate (cosmetic, no timer change) | *(no dedicated behavioral test)* |
| Down | Long | Quit app | *(no dedicated test)* |
| Back | Short | Quit app (pop window) | *(no dedicated test)* |

**Paused state icon tests:**

| Test | Description |
|------|-------------|
| `test_button_icons.py::TestPausedIcons::test_paused_select_icon_play` | Play icon shown on Select when paused |
| `test_button_icons.py::TestCountingIcons::test_counting_select_icon` | Pause icon shown on Select when running |

---

## Alarm State (vibrating, overlaid on Counting)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Silence alarm and enter edit mode | `test_backlight.py::test_backlight_stays_on_when_silencing_to_edit_mode` |
| Up | Long | Repeat timer (add base_length_ms and restart; countdown only) | `test_timer_workflows.py::TestRepeatCompletedTimer::test_repeat_completed_timer`, `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_alarm_repeats_timer`, `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_longer_alarm_repeats_timer`, `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_longer_alarm_repeats_timer_old_method` |
| Select | Short | Silence alarm and toggle play/pause | `test_backlight.py::test_backlight_on_during_alarm` |
| Select | Long | Restart timer from base_length_ms (running) | `test_hold_select_restart.py::test_restart_during_alarm` |
| Down | Short | Snooze: if repeating with count > 1, advance repeat; otherwise add 5 minutes | `test_timer_workflows.py::TestSnoozeCompletedTimer::test_snooze_completed_timer` |
| Down | Long | Quit app | *(no dedicated test)* |
| Back | Short | Silence alarm (timer continues as chrono) | `test_timer_workflows.py::TestQuietAlarmBackButton::test_quiet_alarm_with_back_button` |

---

## Sub-minute Timer Behavior

Timers with only seconds (no minutes) stay paused after edit mode expires, rather than auto-starting.

| Test | Description |
|------|-------------|
| `test_timer_workflows.py::TestSubMinuteTimerStaysPaused::test_sub_minute_timer_stays_paused_after_edit_expires` | Sub-minute timer stays paused when edit expires |
| `test_timer_workflows.py::TestMinuteAndSecondsTimerStaysPaused::test_minute_and_seconds_timer_stays_paused` | Timer with both minutes and seconds stays paused |

---

## Chrono (Stopwatch) Mode

Chrono mode is a variant of Counting mode where the timer counts up from 0:00 instead of counting down.

| Test | Description |
|------|-------------|
| `test_create_timer.py::TestChronoMode::test_chrono_mode_counts_up` | Stopwatch counts up when no timer is set |
| `test_create_timer.py::TestTimerStartsImmediately::test_chrono_has_elapsed_time_when_mode_expires` | Chrono has ~3s elapsed when New mode auto-expires |
| `test_stopwatch_subtraction.py::test_chrono_subtraction_converts_to_countdown` | Subtracting from chrono converts to countdown |
| `test_stopwatch_subtraction.py::test_chrono_subtraction_multiple_minutes` | Subtracting 3 minutes from chrono |
| `test_stopwatch_subtraction.py::test_chrono_add_then_subtract` | Add time then toggle direction and subtract |

---

## Zero-Crossing (Auto Direction Flip)

When editing crosses from positive to negative (or vice versa), the timer type automatically converts between countdown and chrono, and the editing direction resets to forward. The countdown value after a chrono-to-countdown zero-crossing equals the button increment amount (chrono elapsed time is not subtracted).

| Test | Description |
|------|-------------|
| `test_edit_timer_direction.py::TestZeroCrossingTypeConversion::test_countdown_to_chrono_via_subtraction_new_mode` | Countdown converts to chrono when crossing zero in New mode |
| `test_edit_timer_direction.py::TestZeroCrossingTypeConversion::test_countdown_to_chrono_via_subtraction_editsec` | Same conversion in EditSec mode |
| `test_edit_timer_direction.py::TestAutoDirectionFlip::test_auto_flip_countdown_to_chrono_new_mode` | Direction auto-flips after zero-crossing in New mode |
| `test_edit_timer_direction.py::TestAutoDirectionFlip::test_auto_flip_countdown_to_chrono_editsec` | Direction auto-flips in EditSec mode |
| `test_edit_timer_direction.py::TestAutoDirectionFlip::test_continued_editing_after_auto_flip_new_mode` | Subsequent presses work in forward direction after auto-flip |
| `test_edit_timer_direction.py::TestAutoDirectionFlip::test_round_trip_zero_crossing_editsec` | Two consecutive zero-crossings both trigger auto-flip; countdown equals button increment |
| `test_base_length.py::TestBaseLength::test_chrono_edit_then_countdown_ignores_chrono_elapsed` | Chrono elapsed time does not reduce countdown value on zero-crossing |

---

## Button Icon Tests

These tests verify the correct icons are displayed beside each button in each mode.

### New Mode Icons

| Button | Icon | Test |
|--------|------|------|
| Up | +20min | `test_button_icons.py::TestNewModeIcons::test_new_up_icon` |
| Select | +5min | `test_button_icons.py::TestNewModeIcons::test_new_select_icon` |
| Down | +1min | `test_button_icons.py::TestNewModeIcons::test_new_down_icon` |
| Back | +1hr | `test_button_icons.py::TestNewModeIcons::test_new_back_icon` |
| Long Up | Direction toggle | `test_button_icons.py::TestNewModeIcons::test_new_long_up_direction_toggle` |
| Long Select | Reset | `test_button_icons.py::TestNewModeIcons::test_new_long_select_icon` (skipped) |
| Long Down | Quit | `test_button_icons.py::TestNewModeIcons::test_new_long_down_icon` |

### EditSec Mode Icons

| Button | Icon | Test |
|--------|------|------|
| Up | +20s | `test_button_icons.py::TestEditSecIcons::test_editsec_up_icon` |
| Select | +5s | `test_button_icons.py::TestEditSecIcons::test_editsec_select_icon` |
| Down | +1s | `test_button_icons.py::TestEditSecIcons::test_editsec_down_icon` |
| Back | +60s | `test_button_icons.py::TestEditSecIcons::test_editsec_back_icon` |
| Long Up | Direction toggle | `test_button_icons.py::TestEditSecIcons::test_editsec_long_up_direction_toggle` |

### Counting Mode Icons

| Button | Icon | Test |
|--------|------|------|
| Up | Edit | `test_button_icons.py::TestCountingIcons::test_counting_up_icon` |
| Select (running) | Pause | `test_button_icons.py::TestCountingIcons::test_counting_select_icon` |
| Select (paused) | Play | `test_button_icons.py::TestPausedIcons::test_paused_select_icon_play` |
| Down | Details | `test_button_icons.py::TestCountingIcons::test_counting_down_icon` |
| Back | Exit | `test_button_icons.py::TestCountingIcons::test_counting_back_icon` |
| Long Up | Enable repeat | `test_button_icons.py::TestCountingIcons::test_counting_long_up_icon` |
| Long Select | Restart | `test_button_icons.py::TestCountingIcons::test_counting_long_select_icon` (skipped) |
| Long Down | Quit | `test_button_icons.py::TestCountingIcons::test_counting_long_down_icon` |

### Chrono Mode Icons

| Button | Icon | Test |
|--------|------|------|
| Select | Pause | `test_button_icons.py::TestChronoIcons::test_chrono_select_icon` |
| Long Select | Reset | `test_button_icons.py::TestChronoIcons::test_chrono_long_select_icon` (skipped) |

### EditRepeat Mode Icons

| Button | Icon | Test |
|--------|------|------|
| Up | Hidden | `test_button_icons.py::TestEditRepeatIcons::test_editrepeat_up_icon` |
| Select | +5 repeats | `test_button_icons.py::TestEditRepeatIcons::test_editrepeat_select_icon` |
| Down | +1 repeat | `test_button_icons.py::TestEditRepeatIcons::test_editrepeat_down_icon` |
| Back | Reset count | `test_button_icons.py::TestEditRepeatIcons::test_editrepeat_back_icon` |

### Alarm Icons

| Button | Icon | Test |
|--------|------|------|
| Up | Edit | `test_button_icons.py::TestAlarmIcons::test_alarm_up_icon_edit` |
| Long Up | Reset | `test_button_icons.py::TestAlarmIcons::test_alarm_long_up_icon_reset` |
| Select | Pause | `test_button_icons.py::TestAlarmIcons::test_alarm_select_icon_pause` |
| Down | Snooze | `test_button_icons.py::TestAlarmIcons::test_alarm_down_icon_snooze` |
| Back | Silence | `test_button_icons.py::TestAlarmIcons::test_alarm_back_icon_silence` |

---

## Repeat Counter Visibility Tests

| Test | Description |
|------|-------------|
| `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_editrepeat_shows_repeat_counter` | Counter visible in EditRepeat |
| `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_counting_mode_up_region_with_repeats` | Counter visible in Counting with repeats, edit icon hidden |
| `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_new_mode_baseline_has_plus_20_icon` | +20min icon visible in New mode baseline |
| `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_new_mode_with_repeats_hides_plus_20_icon` | +20min icon hidden when editing repeating timer |
| `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_editsec_mode_with_repeats_hides_plus_20_icon` | +20s icon hidden when editing repeating timer |
| `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_new_mode_reverse_with_repeats_hides_minus_20_icon` | -20min icon hidden when editing repeating timer in reverse |
| `test_repeat_counter_visibility.py::TestIconOverlapPrevention::test_editrepeat_up_region_empty_during_flash_off` | Up region empty during flash OFF in EditRepeat |

---

## Backlight Tests

| Test | Description |
|------|-------------|
| `test_backlight.py::test_backlight_on_in_edit_mode` | Backlight on in New mode |
| `test_backlight.py::test_backlight_off_in_counting_mode` | Backlight off in Counting mode |
| `test_backlight.py::test_backlight_on_during_alarm` | Backlight on during alarm |
| `test_backlight.py::test_backlight_on_in_edit_sec_mode` | Backlight on in EditSec mode |
| `test_backlight.py::test_backlight_on_in_edit_repeat_mode` | Backlight on in EditRepeat mode |
| `test_backlight.py::test_backlight_stays_on_when_silencing_to_edit_mode` | Backlight stays on when silencing alarm to edit |
