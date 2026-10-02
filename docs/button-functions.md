# Button Functions by Mode

This document describes what each physical button does in every control mode of QuickTimer.

## Modes Overview

| Mode | Description |
|------|-------------|
| **TimerList** | List of all active timers. Shown on app open when ≥1 existing timer is saved and the "Multiple Timers" setting is enabled. |
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

## Aplite limits

Aplite (the original Pebble and Pebble Steel) has a 24KB app region for the code, the data, and the heap. The alarm-delivery code has priority there: every part of it is in the aplite build (the alarm watch, the held alarm and its takeover, the bell icon and five pulses of the Timer List, the wakeups with their backups, the pending alarm). To make space for it, these parts are not in the aplite build:

| Not on aplite | What aplite does | Flag | Tests |
|---|---|---|---|
| More than 3 timer slots | **3 slots** (32 elsewhere). With 3 timers saved, the Timer List has no "New Timer" row. If more than 3 timers are saved by an older version, the first 3 are loaded and the others are dropped. | `MAX_TIMERS` in `src/timer.h` | `test_timer_aplite.c::test_max_timers_is_3`, `test_fourth_slot_is_refused`, `test_read_five_saved_slots_keeps_first_three`, `test_read_five_saved_slots_then_store` |
| Mnemonic names ("dry mouse") | A new timer gets the name **"Timer N"**, with the lowest N that no other timer's name uses. A saved mnemonic name stays. | `MNEMONIC_FEATURE` in `src/timer.h` | `test_timer_aplite.c::test_first_name_is_timer_1`, `test_lowest_free_number_after_delete`, `test_no_duplicate_names_after_delete_and_create`, `test_saved_mnemonic_name_is_kept_and_not_counted`; `test_mnemonic_names.py` (expects "Timer 1" on aplite) |
| Button hint icons | No icons at the screen edges and no icons during an alarm. The buttons do the same. The Timer List keeps its bell icon and its repeat glyph (stored for aplite in a format that needs no decode). | `BUTTON_ICONS_FEATURE` in `src/drawing.h` | `test_drawing.c::test_aplite_loads_and_draws_no_icons` |
| Settings sync with the phone | The default of every setting. | `SETTINGS_SYNC_FEATURE` in `src/settings.h` | `test/check_build.sh` |
| Test log output (`TEST_STATE` lines) in the release build | No test logs. A test build has them: `QT_TEST_BUILD=1 pebble build`. The functional tests make a test build. | `TEST_LOGS` in `src/utility.h` | `test/check_build.sh` |
| Lap stopwatch, "Delete all" row, slot-limit warnings | See "Lap Stopwatch". | `LAP_FEATURE` in `src/timer.h` | |
| Input guard | Presses act at once. See "Input Guard". | `WAKEUP_GUARD_FEATURE` in `src/main.h` | |

The alarm watch helpers are tested in the aplite configuration too: `test_timer_aplite.c::test_watch_ended_mask_three_slots`, `test_watch_mask_shift_on_delete`, `test_watch_alarm_of_loaded_slot_rings`.

**A full heap does not stop the app (every platform).** A new animation of a text field replaces the field's running animation, and an animation whose memory cannot be allocated sets its value to the end at once. Before this, a few quick screen changes on aplite filled the heap and the app stopped. Tests: `test_animation.c` (all tests), `test_drawing.c::test_text_layout_change_does_not_pile_up_animations`.

---

## Timer List Mode (TimerList)

Shown on app open when ≥1 existing timer is saved and the "Multiple Timers" setting is enabled. An implicit new stopwatch slot is created on entry; it becomes the active slot if the user selects "New Timer", and is discarded if the user selects an existing timer.

Up to **32 timer slots** are supported (3 on aplite, where the additions below are compiled out for RAM; see "Aplite limits"). The list **scrolls** to keep the selected row visible, and a **"Delete all"** entry is pinned to the very bottom of the list regardless of the Lap Stopwatch setting. Creating a timer that leaves **3 or fewer slots free** shows an approaching-limit message ("N slots left") for 3 seconds with three short vibrations (`test_stopwatch_laps.py::TestSlotLimit::test_new_timer_near_limit_shows_warning`).

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Scroll selection up (clamped at top row; viewport scrolls to keep selection visible) | `test_timer_list.py::TestTimerListNavigation::test_up_down_navigation` |
| Down | Short | Scroll selection down (clamped at the "Delete all" bottom row; viewport scrolls to keep selection visible) | `test_timer_list.py::TestTimerListNavigation::test_up_down_navigation`, `test_timer_list.py::TestListScrolling::test_scroll_reaches_delete_all` |
| Down | Long | If "New Timer" selected: discard implicit slot and exit app (with a **held alarm**: show that alarm instead of exiting, see below). If existing timer selected: delete that timer and select the **previous** timer entry (deleting the topmost timer keeps the position so the next timer shifts up; deleting the last timer selects "New Timer"; the selection never lands on "Delete all"). If "Delete all" selected: delete **every** timer and exit to the watchface | `test_timer_list.py::TestTimerListDelete::test_hold_down_deletes_timer`, `test_timer_list.py::TestPostDeleteSelection::test_delete_selects_previous_then_new_timer`, `test_timer_list.py::TestPostDeleteSelection::test_delete_topmost_keeps_position`, `test_timer_list.py::TestDeleteAllRow::test_hold_down_clears_all_and_exits` |
| Select | Short | If "New Timer" selected: set implicit slot as active, open main window in New mode, and give one short vibration to confirm the new timer. If existing timer selected: discard implicit slot, set selected slot as active, open main window in Counting mode (no vibration); with a **held alarm**, the held alarm opens instead of the selected timer (see below). If "Delete all" selected: show a brief "Hold Down to clear all timers" hint and delete nothing | `test_timer_list.py::TestTimerListSelect::test_select_new_timer`, `test_timer_list.py::TestTimerListSelect::test_select_existing_timer`, `test_timer_list.py::TestDeleteAllRow::test_select_shows_hint_and_deletes_nothing`, `test_timer_list.py::TestNewTimerVibration::test_select_new_timer_vibrates`, `test_timer_list.py::TestNewTimerVibration::test_select_existing_timer_does_not_vibrate`, `test_timer_list.py::TestNewTimerVibration::test_open_list_does_not_vibrate` |
| Back | Short | Exit app (implicit slot remains and is persisted on terminate). With a **held alarm**: show that alarm instead of exiting (see below) | `test_list_alarm_takeover.py::TestListHoldsAlarm::test_slot0_alarm_is_held_then_back_takes_over` |
| *(auto)* | — | 30-second idle timeout: save implicit slot and background the app. With a **held alarm**: show that alarm instead (see below) | `test_timer_list.py::TestTimerListIdle::test_idle_backgrounds_app`, `test_list_alarm_takeover.py::TestListTakeover::test_idle_timeout_takes_over` |

**Timer display format:**

| Timer type | Line 1 | Line 2 |
|------------|--------|--------|
| Countdown | Total duration (e.g. `05:00`) | Remaining time |
| Stopwatch / chrono | Total duration + ` -->` (e.g. `05:00 -->`) | Elapsed time |
| New Timer row | `New Timer` | Elapsed time of implicit slot |

**Repeat indicator:** A repeating timer's row shows the repeat glyph (the same icon the Counting-mode "enable repeat" button uses) at the right of the name line. The glyph is tinted to the row's text color — black on the light (unselected) background, white on the black (selected) row highlight — so it stays visible in both states. Test: `test_repeat_list_icon.py::TestRepeatListIcon::test_repeat_icon_contrasts_on_both_row_states`.

### Held alarm in the Timer List

The Timer List is **busy**: the user opened the app to choose or set a timer, so an alarm does not take the screen. While the list is open, the app watches every countdown that was running with time left when the list opened, and every saved held alarm (see "Alarms of timers that are not on screen"). When a watched countdown reaches zero, its alarm is **held**:

- The list stays open. Within one list refresh (500 ms), the timer's row shows a large **bell icon** at its left (black on a light row, white on the selected row), and the name and time move to its right.
- The watch vibrates **five short pulses** once for that alarm. This is different from the one pulse of "New Timer" and the three pulses of the slot-limit warning. Two alarms that end in the same refresh give one set of pulses.
- The alarm vibration itself does **not** start in the list, not for any slot.
- A countdown that had ended before the app opened (and is not a saved held alarm), or that is paused, is not held or marked.

The held alarm **takes over** when the user leaves the list: the list closes and the main window shows that timer in Counting mode with its alarm vibrating for its full time. If several alarms are held, the one that ended first opens, and the others take over in turn (see the main-window rules).

| List action with a held alarm | Result | Implicit "New Timer" slot | Tests |
|-------------------------------|--------|---------------------------|-------|
| Select on the held timer's row | That timer's alarm opens | Discarded (the Select rule) | `test_list_alarm_takeover.py::TestListTakeover::test_select_held_row_takes_over` |
| Select on another timer's row | The held alarm opens instead. The selected timer is not opened or changed | Discarded (the Select rule) | `test_list_alarm_takeover.py::TestListHoldsAlarm::test_slot1_alarm_is_held_then_select_other_timer_takes_over` |
| Select on "New Timer" | New mode opens, with one short pulse, as usual. New mode is busy, so the alarm stays held and takes over when the edit ends | Becomes the new timer | `test_list_alarm_takeover.py::TestListTakeover::test_select_new_timer_keeps_alarm_held_until_edit_ends` |
| Back | The held alarm opens. The app does not exit | Kept as a running stopwatch (the Back rule) | `test_list_alarm_takeover.py::TestListHoldsAlarm::test_slot0_alarm_is_held_then_back_takes_over`, `test_list_alarm_takeover.py::TestListTakeover::test_two_held_alarms_open_in_order` |
| 30 s idle timeout | The held alarm opens. The app does not go to the background, so the list hides an alarm for at most 30 s after the last press | Kept as a running stopwatch (the idle rule) | `test_list_alarm_takeover.py::TestListTakeover::test_idle_timeout_takes_over` |
| Hold Down on "New Timer" | The held alarm opens. The app does not exit. The release of that Down does nothing | Discarded (the hold Down rule) | `test_list_alarm_takeover.py::TestListTakeover::test_hold_down_on_new_timer_takes_over` |
| Select on "Delete all" | The hint shows and nothing is deleted. The list stays open and the alarm stays held and marked | Unchanged | `test_list_alarm_takeover.py::TestListDeleteWithHeldAlarm::test_select_delete_all_keeps_alarm_held` |
| Hold Down on the held timer's row | That timer and its alarm are deleted. The list stays open | Unchanged | `test_list_alarm_takeover.py::TestListDeleteWithHeldAlarm::test_hold_down_on_held_row_deletes_it` |
| Hold Down on another timer's row | That timer is deleted. The list stays open and the held alarm stays held and marked | Unchanged | `test_list_alarm_takeover.py::TestListDeleteWithHeldAlarm::test_hold_down_on_other_row_keeps_alarm_held`, `test_list_alarm_takeover.py::TestListHoldsAlarm::test_delete_moves_held_timer_to_lower_slot` |
| Hold Down on "Delete all" | Every timer is deleted, also the held ones, and the app exits. No alarm is left, so the app does not wake up | Deleted | `test_list_alarm_takeover.py::TestListDeleteWithHeldAlarm::test_hold_down_on_delete_all_exits_without_wakeup` |

When the held alarm takes over, the **input guard** starts (see "Input Guard"; not on aplite), so the press that left the list, or one just after it, does not silence the alarm.

Other tests: `test_list_alarm_takeover.py::TestListHoldsAlarm::test_deleted_countdown_is_not_held`, `test_overdue_countdown_at_open_is_not_held`, `test_paused_countdown_is_not_held`, `test_open_just_before_the_end_shows_the_list`; `test_main_logic.c::test_show_alarm_on_unchecked_slot`, `test_show_alarm_guards_presses`, `test_sim_no_alarm_behind_the_list`, `test_sim_list_exit_reruns_the_check`; `test_timer_multi.c::test_ended_mask`, `test_find_ended_*`, `test_watch_*`, `test_slot_delete_shifts_watch_mask`.

---

## New Mode (ControlModeNew)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Add 20 minutes to timer | `test_create_timer.py::TestButtonPresses::test_up_button_increments_20_minutes`, `test_log_based.py::test_up_button_increments_20_minutes_log_based` |
| Up | Long | Toggle reverse direction (increment becomes decrement) | `test_directional_icons.py::TestNewModeReverseIcons::test_new_reverse_up_icon`, `test_stopwatch_subtraction.py::test_chrono_add_then_subtract`, `test_reverse_chrono_and_edit_pause.py::TestReverseChrono::test_reverse_direction_creates_chrono` |
| Select | Short | Add 5 minutes to timer | `test_create_timer.py::TestButtonPresses::test_select_button_increments_5_minutes` |
| Select | Long | Switch to EditSec mode (preserving current timer value and direction) | `test_edit_mode_reset.py::test_long_press_select_toggles_new_to_editsec`, `test_timer_workflows.py::TestEditModeToggle::test_long_press_select_toggles_new_to_editsec`, `test_edit_mode_reset.py::test_toggle_new_to_editsec_preserves_reverse_direction`, `test_hold_select_restart.py::TestEditModeToggle::test_toggle_new_editsec_preserves_value` |
| Down | Short | Add 1 minute to timer | `test_create_timer.py::TestCreateTimer::test_down_button_increments_minutes`, `test_create_timer.py::TestCreateTimer::test_create_2_minute_timer`, `test_log_based.py::test_multiple_button_presses_log_sequence`, `test_create_timer.py::TestTimerStartsImmediately::test_timer_counts_down_during_setup`, `test_stopwatch_subtraction.py::TestStopwatchSubtraction::test_chrono_subtraction_multiple_minutes` |
| Down | Long | Quit app (sets reset flag and closes) | `test_button_icons.py::TestNewModeIcons::test_new_long_down_icon` (icon only) |
| Back | Short | Add 60 minutes (1 hour) to timer | *(no dedicated test)* |
| Up + Back | Chord (Up first) | **Emery only, `Voice Naming` enabled:** launch voice dictation to rename the active timer. There is no confirmation screen: a successful transcription is applied immediately with **one short vibration**. A failure that ends on its own gives **three short vibrations** and leaves the name unchanged; backing out of the dictation UI yourself is silent. If the phone is disconnected, shows a no-phone icon (~1s) with three short vibrations instead and leaves the name unchanged. Suppresses the normal Back action. Compiled out (`#ifdef PBL_MICROPHONE`) on non-microphone platforms. | `test_main_logic.c::test_dictation_success_vibrates_and_sets_name`, `test_main_logic.c::test_dictation_no_speech_buzzes`, `test_main_logic.c::test_dictation_transcription_rejected_is_silent`, `test_main_logic.c::test_dictation_confirmation_disabled`, `test_timer.c::test_timer_set_name_word_boundary`, `test_timer.c::test_timer_set_name_hard_truncate`, `test_timer.c::test_timer_set_name_trims_and_preserves`, `test_timer.c::test_timer_set_name_trims_punctuation`, `test_voice_rename_offline.py` |

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
| Select | Long | Switch to New mode (preserving current timer value and direction) | `test_edit_mode_reset.py::test_long_press_select_toggles_editsec_to_new`, `test_timer_workflows.py::TestEditModeToggle::test_long_press_select_toggles_editsec_to_new`, `test_edit_mode_reset.py::test_toggle_editsec_to_new_preserves_reverse_direction`, `test_hold_select_restart.py::TestEditModeToggle::test_toggle_new_editsec_preserves_value` |
| Down | Short | Add 1 second to timer | `test_timer_workflows.py::TestSetShortTimer::test_set_4_second_timer` (used to build timer) |
| Down | Long | Quit app | *(no dedicated test)* |
| Back | Short | Add 60 seconds (1 minute) to timer | `test_directional_icons.py::TestEditSecModeForwardIcons::test_editsec_forward_back_icon_plus60` |
| Up + Back | Chord (Up first) | **Emery only, `Voice Naming` enabled:** launch voice dictation to rename the active timer. There is no confirmation screen: a successful transcription is applied immediately with **one short vibration**. A failure that ends on its own gives **three short vibrations** and leaves the name unchanged; backing out of the dictation UI yourself is silent. If the phone is disconnected, shows a no-phone icon (~1s) with three short vibrations instead and leaves the name unchanged. Suppresses the normal Back action. Compiled out (`#ifdef PBL_MICROPHONE`) on non-microphone platforms. | `test_main_logic.c::test_dictation_success_vibrates_and_sets_name`, `test_main_logic.c::test_dictation_no_speech_buzzes`, `test_main_logic.c::test_dictation_transcription_rejected_is_silent`, `test_main_logic.c::test_dictation_confirmation_disabled`, `test_timer.c::test_timer_set_name_word_boundary`, `test_timer.c::test_timer_set_name_hard_truncate`, `test_timer.c::test_timer_set_name_trims_and_preserves`, `test_timer.c::test_timer_set_name_trims_punctuation`, `test_voice_rename_offline.py` |

**Voice rename gesture (emery only):**
- Requires the `Voice Naming` setting enabled and a microphone-capable platform (Pebble 2 / emery).
- Up must be pressed **first**, then Back, while Up is still held (only Up has a raw click handler that tracks `s_up_held`).
- The phone connection is checked up front via `connection_service_peek_pebble_app_connection()`. If the phone is **disconnected** (e.g. airplane mode), no dictation session is started; instead a full-screen no-phone-connected icon is shown for ~1 second with three short vibration pulses, then the app auto-returns to `ControlModeEditSec` with the timer's name unchanged. Functional tests: `test_voice_rename_offline.py` (require BT-toggle + button input in the emulator; see file header).
- When the phone **is connected**, a successful transcription is trimmed of leading/trailing non-alphanumeric characters (whitespace, punctuation, symbols), truncated to 19 chars (at a word boundary where possible), and saved as the timer's name, replacing the mnemonic default. Trimming tests: `test_timer.c::test_timer_set_name_trims_punctuation`, `test_timer.c::test_timer_set_name_punctuation_only_empty`.
- **No confirmation screen.** `dictation_session_enable_confirmation` is set to `false`, so the result callback fires as soon as the transcription is ready. A wrong transcription is corrected by simply repeating the gesture.
- **Vibration feedback** tells success from failure without looking at the watch:
  - **One short pulse** - transcription applied, timer renamed.
  - **Three short pulses** - nothing changed, for failures that ended on their own (`FailureSystemAborted`, `FailureNoSpeechDetected`, `FailureConnectivityError`, `FailureDisabled`, `FailureInternalError`, `FailureRecognizerError`). Same pattern the disconnected-phone feedback uses.
  - **Silence** - the user exited the dictation UI themselves (`FailureTranscriptionRejected`, `FailureTranscriptionRejectedWithError`); they are already looking at the watch, so a buzz would add nothing.
  - Tests: `test_main_logic.c::test_dictation_*` (the unit build defines `-DPBL_MICROPHONE` so this path compiles in).
- A failed/cancelled dictation leaves the existing name unchanged.

**Reverse direction icons:**

| Button | Forward Icon | Reverse Icon | Test |
|--------|-------------|-------------|------|
| Up | +20s | -20s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_up_icon` |
| Select | +5s | -5s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_select_icon` |
| Down | +1s | -1s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_down_icon` |
| Back | +60s | -60s | `test_directional_icons.py::TestEditSecModeReverseIcons::test_editsec_reverse_back_icon` |

**Entering EditSec while the New timer still runs:** a fresh New timer runs as a stopwatch from launch, so holding Select within the first 3 s enters EditSec with that stopwatch still running, and each added second is subtracted from it. If the added time is still less than the stopwatch (the result is still a stopwatch), no alarm is armed: an alarm on a stopwatch would ring at once and turn the next Down into a snooze (+5 min). Only a result that is a countdown arms the alarm (`timer_increment`). Tests: `test_main_logic.c::test_sim_no_alarm_on_stopwatch_after_edit_increment`, `test_main_logic.c::test_sim_countdown_never_counts_up_sweep` (timing sweep of this path; no alarm while editing, result at most the entered time).

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
| Down | Short | Add 1 to repeat count | `test_timer_workflows.py::TestEnableRepeatingTimer::test_enable_repeating_timer`, `test_repeat_counter_visibility.py::TestRepeatCounterVisibility::test_editrepeat_shows_repeat_counter`, `test_hold_select_restart.py::TestRestartRepeatingTimerRestoresCount::test_restart_repeating_timer_restores_repeat_count` |
| Down | Long | Quit app | *(no dedicated test)* |
| Back | Short | Reset repeat count to 0 | `test_timer_workflows.py::TestEditRepeatBackButton::test_back_button_resets_repeat_count_to_zero` |

---

## Counting Mode (ControlModeCounting)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Enter edit mode (New if timer > 0:00, EditSec if at 0:00) | `test_timer_workflows.py::TestEditRunningTimer::test_edit_running_timer`, `test_timer_workflows.py::TestEditCompletedTimer::test_edit_completed_timer_add_minute` |
| Up | Long | Toggle repeat mode on/off (countdown only; no-op for chrono). Repeats never inflate the timer length: each repeat restarts the cycle at base_length_ms, so toggling repeats off leaves the original timer length. | `test_timer_workflows.py::TestEnableRepeatingTimer::test_enable_repeating_timer`, `test_main_logic.c::test_toggle_repeat_off_after_repeat_keeps_original_length`, `test_timer.c::test_timer_check_elapsed_repeat_keeps_base_length` |
| Select | Short | Toggle play/pause. **Exception:** with `Lap Stopwatch` enabled, Select on a running **stopwatch** records a lap instead (see the Lap Stopwatch section); a running countdown still toggles play/pause. | `test_create_timer.py::TestPlayPause::test_select_toggles_play_pause_in_counting_mode`, `test_timer_workflows.py::TestPauseCompletedTimer::test_pause_completed_timer`, `test_main_logic.c::test_lap_setting_countdown_select_pauses_not_lap` |
| Select | Double (two presses within ~300 ms) | Only with `Lap Stopwatch` enabled, on a running **stopwatch**: pause it at the time of the first press, with no lap recorded. In every other state there is no double press: two fast presses are two single presses (see the Lap Stopwatch section). | `test_stopwatch_laps.py::TestDoublePressPause::test_double_press_pauses_without_lap`, `test_stopwatch_laps.py::TestDoublePressPause::test_edit_mode_double_tap_adds_two_increments`, `test_main_logic.c::test_double_press_pauses_at_first_press_down` |
| Select | Long (running) | Restart timer to original base_length_ms (preserves running state) | `test_hold_select_restart.py::test_restart_running_countdown_preserves_running`, `test_hold_select_restart.py::test_restart_running_chrono_preserves_running`, `test_hold_select_restart.py::test_restart_repeating_timer_restores_count`, `test_create_timer.py::TestLongPressReset::test_long_press_select_resets_timer` |
| Select | Long (paused) | Reset to 0:00 and enter EditSec mode | `test_hold_select_restart.py::test_long_press_select_paused_countdown_resets_to_editsec`, `test_hold_select_restart.py::test_long_press_select_paused_chrono_resets_to_editsec` |
| Down | Short | Extend the high-refresh display (live seconds) for a fixed window (cosmetic, no timer change). The window length is the **Down Button Extra** setting (seconds, default 60; 0 disables). While the app is paused the press does not extend the window (nothing to refresh). | `test_main_logic.c::test_down_extension_honors_down_extra_setting`, `test_main_logic.c::test_down_press_records_extension_window` |
| Down | Long | Delete this timer and exit app. If multiple timers are enabled, remaining timers stay persisted; re-launching shows the Timer List with the remaining slots. **Exception:** if another timer's alarm is held, that alarm shows instead of the app exiting (`test_main_logic.c::test_hold_down_shows_held_alarm`, `test_hold_down_in_edit_mode_shows_held_alarm`). | `test_hold_down_delete.py::TestHoldDownDelete::test_hold_down_in_main_window_deletes_only_active_timer`, `test_hold_down_delete.py::TestHoldDownDelete::test_hold_down_single_timer_exits_cleanly` |
| Back | Short | Exit app (timer persisted; re-launching shows Timer List if any timers remain). **Exception:** within the ~5 s lap flash window, opens the lap just recorded instead — see the Lap Stopwatch section. | `test_stopwatch_laps.py::TestLapFlash::test_back_during_flash_views_lap` |

**Paused state icon tests:**

| Test | Description |
|------|-------------|
| `test_button_icons.py::TestPausedIcons::test_paused_select_icon_play` | Play icon shown on Select when paused |
| `test_button_icons.py::TestCountingIcons::test_counting_select_icon` | Pause icon shown on Select when running |

---

## Alarm State (vibrating, overlaid on Counting)

| Button | Press | Action | Tests |
|--------|-------|--------|-------|
| Up | Short | Silence alarm and enter edit mode. A held alarm of another timer waits until that edit ends | `test_backlight.py::test_backlight_stays_on_when_silencing_to_edit_mode`, `test_main_logic.c::test_sim_up_on_alarm_keeps_held_alarm_waiting` |
| Up | Long | Restart the original timer (length back to base_length_ms; if repeating, repeat count restored to base_repeat_count; countdown only) | `test_timer_workflows.py::TestRepeatCompletedTimer::test_repeat_completed_timer`, `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_alarm_repeats_timer`, `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_longer_alarm_repeats_timer`, `test_timer_workflows.py::TestRepeatTimerDuringAlarm::test_hold_up_during_longer_alarm_repeats_timer_old_method`, `test_main_logic.c::test_up_long_restarts_repeating_timer_after_final_alarm`, `test_main_logic.c::test_up_long_restarts_nonrepeating_timer_at_base_length` |
| Select | Short | Silence alarm and toggle play/pause | `test_backlight.py::test_backlight_on_during_alarm`, `test_timer_workflows.py::TestPauseCompletedTimer::test_pause_completed_timer` |
| Select | Long | Restart timer from base_length_ms (running) | `test_hold_select_restart.py::test_restart_during_alarm` |
| Down | Short | Snooze: if repeating with count > 1, advance repeat (cycle restarts at base_length_ms); otherwise add 5 minutes | `test_timer_workflows.py::TestSnoozeCompletedTimer::test_snooze_completed_timer`, `test_main_logic.c::test_down_click_intermediate_repeat_keeps_base_length` |
| Down | Long | Delete this timer and quit app; if another timer's alarm is held, show that alarm instead of quitting | `test_main_logic.c::test_hold_down_shows_held_alarm`, `test_main_logic.c::test_hold_down_exits_without_held_alarm` |
| Back | Short | Silence alarm (timer continues as chrono). If another timer's alarm is held, it takes over at once, so Back cannot exit while an alarm is held | `test_timer_workflows.py::TestQuietAlarmBackButton::test_quiet_alarm_with_back_button`, `test_main_logic.c::test_sim_held_takes_over_on_back` |

### Input Guard (when an alarm shows)

When an alarm shows, a press that **starts** within `WAKEUP_INPUT_GUARD_MS` (400 ms) is ignored on all four buttons until it is released, and so is a press that was already held down. This stops a press already in progress, or one meant for the screen that was there a moment before, from silencing, snoozing, restarting, or exiting the alarm before the user has seen it. The alarm keeps vibrating; the user presses again to act. The guard starts at:

- a **wakeup launch** (`APP_LAUNCH_WAKEUP`);
- an **alarm takeover**, from the Timer List or from the main window, including a held alarm that takes over when the user leaves the list;
- every **alarm start**: the alarm of the countdown already on screen, an alarm that starts just after a wakeup launch, and a snoozed or repeated timer that reaches zero again.

A launch or event with no alarm to show is not guarded: after a user launch (the Timer List, with or without a marked held alarm, or the main window), presses act at once. Active on every platform except aplite, where it is compiled out for RAM (`WAKEUP_GUARD_FEATURE` in `src/main.h`) and presses act immediately.

| Case | Behavior | Tests |
|------|----------|-------|
| Up, Select, or Down press-down within 400 ms | Raw-down, single, and long actions are all ignored for that press | `test_main_logic.c::test_wakeup_guard_select_press_in_window_ignored`, `test_main_logic.c::test_wakeup_guard_up_press_in_window_ignored`, `test_main_logic.c::test_wakeup_guard_down_press_in_window_ignored`, `test_main_logic.c::test_wakeup_guard_press_late_in_window_ignored` |
| Back press within 400 ms | Ignored (Back's single click fires on press-down, so it is checked there) | `test_main_logic.c::test_wakeup_guard_back_press_in_window_ignored` |
| Press starts within 400 ms and is held past the long-press threshold | Long action is ignored, even though it fires after the window | `test_main_logic.c::test_wakeup_guard_long_press_started_in_window_ignored` |
| Button held down from before the launch, the takeover, or the alarm start | Its release (single or long click) is ignored | `test_main_logic.c::test_wakeup_guard_press_held_before_launch_ignored`, `test_main_logic.c::test_show_alarm_guards_presses`, `test_main_logic.c::test_sim_press_held_across_alarm_start_ignored`, `test_list_alarm_takeover.py::TestListTakeover::test_hold_down_on_new_timer_takes_over` |
| Press-down after 400 ms | Acts normally (for example, Down snoozes, Back silences) | `test_main_logic.c::test_wakeup_guard_down_press_after_window_snoozes`, `test_main_logic.c::test_wakeup_guard_back_press_after_window_silences`, `test_wakeup_guard.py::TestWakeupInputGuard::test_press_after_guard_window_snoozes` |
| New press after an ignored press | Acts normally | `test_main_logic.c::test_wakeup_guard_new_press_after_ignored_press_acts` |
| User launch with no alarm start | No guard; a press at 100 ms acts | `test_main_logic.c::test_wakeup_guard_not_applied_on_user_launch`, `test_main_logic.c::test_user_launch_with_held_alarm_shows_list` |
| Alarm takeover (Timer List or main window) | The window starts at the takeover. A press 100 ms later, a Back 200 ms later, and the release of a button held at the takeover are ignored; a Down at 600 ms snoozes | `test_main_logic.c::test_show_alarm_guards_presses`, `test_main_logic.c::test_show_alarm_on_vibrating_slot`, `test_main_logic.c::test_sim_takeover_when_not_busy` |
| Alarm starts after a wakeup launch | The window starts **again** when the alarm starts. The wakeup time is rounded down to whole seconds, so the app can open up to 1 s before the alarm; a press 100 ms after the alarm appears is ignored however early the app opened | `test_main_logic.c::test_sim_guard_covers_alarm_start_after_early_wakeup` |
| The on-screen countdown's own alarm starts (any launch) | Guarded: a Down 100 ms after the alarm starts is ignored, and a Down at 500 ms snoozes | `test_main_logic.c::test_sim_alarm_start_on_user_launch_guarded`, `test_main_logic.c::test_user_launch_held_slot0_no_list` |
| A snoozed timer reaches zero again | Guarded: a Back 100 ms after the alarm starts is ignored | `test_main_logic.c::test_sim_snoozed_alarm_is_guarded` |
| aplite | No guard: a Down pressed at once after a takeover snoozes | `test_list_alarm_takeover.py::TestListTakeover::test_no_guard_on_aplite_after_takeover` |

An ignored press logs `TEST_STATE:input_blocked`; a wakeup launch logs `TEST_STATE:wakeup_launch`; each alarm start logs `TEST_STATE:guard_restart`. Any new click handler on the main window must start with the `prv_press_blocked()` check (or `prv_press_down_blocked()` for a handler that fires on press-down). Functional tests that press a button after an alarm start call `wait_past_input_guard()` (`test/functional/conftest.py`) first.

### Alarms of timers that are not on screen

The main window shows one timer. The app watches every other countdown that it saw running with time left, so that no alarm is missed.

**Takeover (the user is free).** When a watched countdown reaches zero while the main window shows a timer in Counting mode that is not alarming, it takes over at its end time: it becomes the active timer, its alarm screen shows and vibrates, and the input guard starts. The timer that was on screen keeps running, and it is watched too. Tests: `test_main_logic.c::test_sim_takeover_when_not_busy`.

**Held alarm (the user is busy).** The user is busy when the Timer List is open, the timer on screen is alarming, or the main window is in New mode or an edit mode. A countdown that ends then is **held**: no vibration, no screen change, and the held timer itself is not changed. In the main window there is no signal for a held alarm (the Timer List marks its row and vibrates five pulses). The held alarm takes over as soon as the user is free:

| Event that ends "busy" | Result | Tests |
|------------------------|--------|-------|
| Select, Back, or Down on the alarm (pause, silence, snooze) | The held alarm takes over at once | `test_main_logic.c::test_sim_held_takes_over_on_select`, `test_sim_held_takes_over_on_back`, `test_sim_held_takes_over_on_down`, `test_list_alarm_takeover.py::TestMainWindowTakeover::test_second_alarm_is_held_behind_the_first` |
| The 30 s vibration ends on its own | The held alarm takes over | `test_main_logic.c::test_sim_held_takes_over_when_vibration_ends` |
| Up on the alarm | The alarm is silenced and its edit screen opens. The held alarm waits, and takes over when that edit ends | `test_main_logic.c::test_sim_up_on_alarm_keeps_held_alarm_waiting` |
| An edit (New, EditSec, EditRepeat) expires to Counting | The held alarm takes over | `test_main_logic.c::test_sim_held_behind_new_mode`, `test_sim_held_behind_edit_sec`, `test_sim_held_behind_edit_repeat`, `test_list_alarm_takeover.py::TestListTakeover::test_select_new_timer_keeps_alarm_held_until_edit_ends` |
| Hold Down (delete the timer on screen) | The held alarm shows instead of the app exiting | `test_main_logic.c::test_hold_down_shows_held_alarm`, `test_hold_down_in_edit_mode_shows_held_alarm` |

- The alarm screen shows the **real time** since the held timer ended, and the alarm vibrates for its **full normal time** (30 s, one vibration each second), counted from when it is shown. It does not auto-snooze because it waited. Tests: `test_main_logic.c::test_sim_held_45s_vibrates_for_full_time`, `test_timer_multi.c::test_alarm_shown_late_vibrates_for_full_time`.
- If several alarms are held, the one that ended first opens first; the others stay held until the user is free again. Tests: `test_main_logic.c::test_sim_two_held_open_in_order`.
- A countdown that had ended before the app opened and is not a saved held alarm (for example, its alarm was silenced) never takes over. Tests: `test_main_logic.c::test_sim_overdue_at_launch_never_takes_over`.

**An alarm stays pending until it has rung and stopped.** The user silences or snoozes it with a press that the input guard allows (on aplite, any press), or it stops on its own after 30 s. A takeover or a launch that only shows the alarm does not end this. If the app closes while an alarm is pending (for example, another app opens, or the system exit closes the app during the guard window), it is saved as a held alarm and rings again about 10 s after the app closed. This applies to the timer on screen too. Tests: `test_main_logic.c::test_exit_during_takeover_alarm_rings_again`, `test_exit_during_own_alarm_rings_again`, `test_exit_after_guarded_press_rings_again`, `test_exit_before_alarm_vibrates_keeps_it_pending`, `test_exit_after_silenced_alarm_is_not_pending`, `test_alarm_that_stops_on_its_own_is_not_pending`, `test_silence_clears_bit_and_held_takes_over`.

**Wakeups when the app is closed.** On every exit, the app schedules one wakeup for the next alarm event of **any** timer: a held alarm (about 10 s after the exit), or the countdown that ends first, whether it was on screen or not. It saves the other pending alarms, and the next launch watches them. It also schedules two **backup** wakeups, 2 min and 4 min after the first, for the same timer, in case the first cannot be scheduled or is missed (another app's wakeup within one minute blocks ours). Any launch cancels the backups. A late alarm shows the real time since its end and vibrates for its full time. Tests: `test_main_logic.c::test_exit_one_held`, `test_exit_two_held`, `test_exit_held_and_active_ending_later`, `test_exit_held_and_active_ending_sooner`, `test_exit_active_only`, `test_exit_non_active_ends_first`, `test_exit_two_non_active`, `test_exit_primary_blocked_by_other_app`, `test_exit_primary_and_backup_blocked`, `test_exit_no_pending_alarm`, `test_primary_wakeup_cancels_backups`, `test_backup_wakeup_two_minutes_late`, `test_second_backup_wakeup_four_minutes_late`, `test_backup_launch_holds_second_ended_countdown`, `test_wakeup_launch_for_held_alarm`, `test_list_alarm_takeover.py::TestWakeupForAnyTimer::test_non_active_countdown_wakes_the_app`.

**Launch rule.** A wakeup launch opens the alarm it was scheduled for. A **user launch never opens straight to a takeover**: the app opens as usual, and a saved held alarm (for example, one whose wakeup was missed) is held. With the Timer List, its row is marked and the five pulses vibrate when the list opens. With no list ("Multiple Timers" off), the main window shows slot 0; a saved held alarm on slot 0 is that timer's own alarm, so it starts at launch and vibrates for its full time, and a held alarm on another slot takes over at once. Tests: `test_main_logic.c::test_user_launch_with_held_alarm_shows_list`, `test_user_launch_held_slot0_no_list`, `test_user_launch_leftover_held_slot_takes_over`, `test_list_alarm_takeover.py::TestListHoldsAlarm::test_open_just_before_the_end_shows_the_list`.

**Auto-quit.** After an edit, the app quits by itself after 60 s only if the countdown has more than 20 min **left** (not if its full length is over 20 min), so its own alarm cannot start before the app quits. A takeover cancels this timer, and the app never quits this way while an alarm vibrates or is held. Tests: `test_main_logic.c::test_no_auto_quit_with_little_time_left`, `test_auto_quit_with_over_20_min_left`, `test_no_auto_quit_with_19_min_left`, `test_takeover_cancels_auto_quit`, `test_quit_callback_with_held_alarm_takes_over`, `test_quit_callback_during_alarm_does_not_quit`.

Log markers: `TEST_STATE:main_alarm_takeover,slot=<n>`, `TEST_STATE:alarm_held,slot=<n>` (once per hold), `TEST_STATE:list_alarm_held,slot=<n>,row=<r>`, `TEST_STATE:vibe,src=list_alarm`, `TEST_STATE:list_alarm_takeover,slot=<n>`, `TEST_STATE:timer_list_hide`, and `TEST_STATE:wakeup_sched,slot=<n>,in=<s>,r=<result>` (one line for each wakeup scheduled at exit).

---

## Sub-minute Timer Behavior

Timers with only seconds (no minutes) stay paused after edit mode expires, rather than auto-starting.

| Test | Description |
|------|-------------|
| `test_timer_workflows.py::TestSubMinuteTimerStaysPaused::test_sub_minute_timer_stays_paused_after_edit_expires` | Sub-minute timer stays paused when edit expires |
| `test_timer_workflows.py::TestMinuteAndSecondsTimerStaysPaused::test_minute_and_seconds_timer_stays_paused` | Timer with both minutes and seconds stays paused |
| `test_reverse_chrono_and_edit_pause.py::TestPausedTimerStaysPausedAfterEdit::test_paused_timer_stays_paused_after_edit_expires` | Paused timer remains paused after editing and letting edit mode expire |
| `test_select_ten_second_timer.py::TestSelectTenSecondTimer::test_ten_second_timer_counts_down_on_time` | **Suspected bug, watch closely** (`suspected_bug` marker): a 10 s timer set with Select x2 after a hold-Select reset shows the expected time left at ~2, 5, and 8 s and rings at ~10 s |

---

## Chrono (Stopwatch) Mode

Chrono mode is a variant of Counting mode where the timer counts up from 0:00 instead of counting down.

**Display format — paused milliseconds:** When a stopwatch is **paused** and its elapsed time is **under one hour**, the main display shows milliseconds (e.g. `1:23.456`). Milliseconds are hidden while running, hidden at one hour or more (the display keeps `H:MM:SS`), and never shown for countdown timers. This is a display-only behavior and does not change any button function.

| Test | Description |
|------|-------------|
| `test_create_timer.py::TestChronoMode::test_chrono_mode_counts_up` | Stopwatch counts up when no timer is set |
| `test_create_timer.py::TestTimerStartsImmediately::test_chrono_has_elapsed_time_when_mode_expires` | Chrono has ~3s elapsed when New mode auto-expires |
| `test_stopwatch_subtraction.py::test_chrono_subtraction_converts_to_countdown` | Subtracting from chrono converts to countdown |
| `test_stopwatch_subtraction.py::test_chrono_subtraction_multiple_minutes` | Subtracting 3 minutes from chrono |
| `test_stopwatch_subtraction.py::test_chrono_add_then_subtract` | Add time then toggle direction and subtract |
| `test_reverse_chrono_and_edit_pause.py::TestReverseChrono::test_reverse_direction_creates_chrono` | Reverse direction chrono runs without spurious vibration |
| `test_stopwatch_milliseconds.py::TestStopwatchMilliseconds::test_paused_stopwatch_under_hour_shows_ms` | Paused stopwatch under 1h shows milliseconds |
| `test_stopwatch_milliseconds.py::TestStopwatchMilliseconds::test_running_stopwatch_hides_ms` | Running stopwatch shows no milliseconds |
| `test_stopwatch_milliseconds.py::TestStopwatchMilliseconds::test_paused_countdown_hides_ms` | Paused countdown shows no milliseconds |
| `test_stopwatch_milliseconds.py::TestStopwatchMilliseconds::test_running_countdown_hides_ms` | Running countdown shows no milliseconds |
| `test/test_drawing.c::test_paused_chrono_under_hour_shows_ms` | Unit: paused chrono renders `M:SS.mmm` |
| `test/test_drawing.c::test_paused_chrono_ms_zero_padded` | Unit: millisecond field is zero-padded (`.007`) |
| `test/test_drawing.c::test_paused_chrono_over_hour_hides_ms` | Unit: paused chrono ≥ 1h hides milliseconds |

---

## Lap Stopwatch (`Lap Stopwatch` setting, default off)

When the `Lap Stopwatch` setting is enabled, a running **stopwatch's** Select button records **laps** instead of pausing. This applies only to stopwatches (chrono, counting up); a running **countdown** timer's Select button still toggles play/pause regardless of the setting (`test_main_logic.c::test_lap_setting_countdown_select_pauses_not_lap`). Compiled out on aplite (the original Pebble / Pebble Steel; 24KB app region); available on all other platforms. The settings page labels the row `Lap Stopwatch (not on original Pebble)` to make this clear.

**Recording a lap (Select, Counting mode, stopwatch running):**
- A paused copy of the timer is created in a new slot, frozen at the value **at the moment Select was pressed down**, named `Lap [n]: <name>` with `n` starting at 1 and incrementing per originating timer. If the prefixed name would overflow the name field, the END of the original name is trimmed — the prefix is never dropped.
- The original timer keeps running, stays the active/on-screen timer, and all buttons except Back keep acting on it.
- The display then **flashes** for ~5 seconds: 1 s showing the paused lap, 1 s showing the original. Pressing Select during the flash cancels it and records the next lap.
- The lap is confirmed only after the double-press window (~300 ms after the button is released), because a second press would make it a pause (see below). So the lap flash starts ~0.3 s later than the press. The lap value is not affected: it is the value at press-down.
- Pressing **Back** during the flash cancels it and makes the lap just recorded the active timer, so you stay in Counting mode viewing the paused lap instead of exiting the app. After the flash window ends, Back exits as usual.
- At capacity (no free slot) nothing is recorded: a "No free slots" message is shown with three short vibrations and the original keeps running with its play/pause state unchanged.
- When a lap (or new timer) leaves **3 or fewer slots free**, an approaching-limit "N slots left" message is shown with three short vibrations — for laps it replaces the original-timer phase of the flash; for new timers it is a 3-second overlay.

**Pausing (double-press Select, Counting mode, stopwatch running):**
- Pressing Select **twice within ~300 ms** pauses the stopwatch. The paused value is the value at the **first** press-down, and no lap is recorded for either press. A double press during the lap flash also cancels the flash.
- A paused lap stopwatch resumes with a **single** Select press, at once (no delay, no lap).
- The double press is only "armed" for a running stopwatch in Counting mode with `Lap Stopwatch` on. In every other state (New, EditSec, EditRepeat, a countdown, a paused stopwatch, an alarm, the setting off, aplite) Select has no added delay, and two fast presses are two single presses. An alarm takeover ends the armed state, so Select acts on the alarm at once.
- The wakeup input guard also covers the double press: a press that begins inside the guard window does nothing.
- Long-press Select still restarts the stopwatch.

**Display freeze at press-down (while the double press is armed):**
- Pressing Select down **freezes the display** at the value of that instant: the split with milliseconds (e.g. `0:42.310`) and the header total. The stopwatch itself keeps running, and the button icons stay those of a running stopwatch. There is no vibration.
- The freeze ends when the press resolves: the lap flash starts (single press; the lap has the frozen value), the stopwatch pauses at the frozen value (double press), or the stopwatch restarts (long press; the display stays frozen while the button is held).
- The freeze also ends when the "No free slots" warning shows, when the armed state ends (an alarm takeover, the Timer List, a mode change), or after a safety timeout of about 1 s. In these cases the display goes back to the live value.
- A press-down during the lap flash cancels the flash first, so the frozen frame shows the running stopwatch and not the lap. A single press then starts a new flash for the new lap; in every other case the old flash does not continue.

**Split/total display (lapping enabled):**
- The **main value** always shows the current **split** (time since the last lap; equals the total until the first lap).
- The **header** shows the **total** elapsed since first start, prefixed with the count-up arrow (e.g. `-->12:34`), instead of the `00:00-->` base-length header.
- A recorded lap slot shows its own split as the main value and its cumulative time in the header (`-->` prefixed).

**Restart (long-press Select, Counting mode, stopwatch running):**
- Restarting a running stopwatch resets the lap session (next lap is `Lap 1`) and assigns a fresh mnemonic name based on the new start time.
- **Exception:** if the user has renamed the stopwatch (e.g. via voice dictation — see the Up + Back rename gesture), the custom name is preserved across the restart instead of being replaced by a new mnemonic. A slot is considered user-renamed once `timer_set_name` runs (`has_custom_name`); assigning a mnemonic name clears the flag.

**Header when lapping is disabled (default):**
- A genuine stopwatch (started at 0:00, no original countdown length) shows the time of day it was started, prefixed with `@` and followed by the count-up arrow, e.g. `@12:45-->` — replacing the old `00:00-->` placeholder. Formatted per the watch's 12/24-hour clock style. A paused stopwatch's shown start time drifts forward for however long it stays paused (a known, accepted trade-off).
- An **overtime countdown** (an ordinary countdown that ran past zero) keeps its unchanged base-length header (e.g. `05:00-->`) regardless of the `Lap Stopwatch` setting — it was never a genuine stopwatch, so it never gets the `@`-prefixed header. The `@` prefix exists specifically so a stopwatch's start-time header can't be mistaken for an overtime countdown's original length, since both would otherwise be a bare `NN:NN-->`.
- On aplite, where the feature is compiled out, the header stays `00:00-->` unconditionally.

| Test | Description |
|------|-------------|
| `test_stopwatch_laps.py::TestLapRecording::test_lap_creates_paused_copy_and_original_keeps_running` | Lap creates a paused copy; original keeps running and stays active |
| `test_stopwatch_laps.py::TestLapRecording::test_lap_numbering_increments` | `Lap 1:` / `Lap 2:` / `Lap 3:` naming |
| `test_stopwatch_laps.py::TestLapRecording::test_select_toggles_pause_when_setting_off` | Setting off: Select still toggles play/pause |
| `test_stopwatch_laps.py::TestLapFlash::test_flash_alternates_then_ends` | Flash alternates lap/original and ends after ~5 s |
| `test_stopwatch_laps.py::TestLapFlash::test_select_during_flash_records_next_lap` | Re-lap during the flash window |
| `test_stopwatch_laps.py::TestLapFlash::test_back_during_flash_views_lap` | Back during the flash opens the recorded lap instead of exiting |
| `test_stopwatch_laps.py::TestSplitTotalDisplay::test_header_shows_total_after_lap` | Main = split, header = `-->` total; lap slot shows split + cumulative |
| `test_stopwatch_laps.py::TestSplitTotalDisplay::test_header_shows_start_time_when_lapping_disabled` | Setting off shows the `@`-prefixed start-time header for a genuine stopwatch |
| `test_stopwatch_laps.py::TestSplitTotalDisplay::test_overtime_countdown_header_unchanged_when_lapping_disabled` | An overtime countdown keeps its base-length header, no `@` prefix |
| `test_stopwatch_laps.py::TestSlotLimit::test_fill_to_capacity_warns_and_persists` | Warnings at ≤3 free, "no free slots" guard at capacity, 32 slots persist |
| `test_stopwatch_laps.py::TestSlotLimit::test_new_timer_near_limit_shows_warning` | New-timer approaching-limit overlay (3 s) |
| `test_stopwatch_laps.py::TestLongPressRestart::test_restart_resets_lap_numbering` | Long-press Select restarts and resets lap numbering |
| `test_main_logic.c::test_restart_stopwatch_preserves_custom_name` | Restarting a renamed stopwatch keeps its custom name |
| `test_main_logic.c::test_restart_unnamed_stopwatch_reassigns_name` | Restarting an un-renamed stopwatch reassigns a fresh mnemonic name |
| `test/test_timer_multi.c::test_lap_*` | Unit tests: lap copy state, split/cumulative math, naming, trimming, capacity |
| `test_stopwatch_laps.py::TestDoublePressPause::test_double_press_pauses_without_lap` | Double press pauses a running lap stopwatch; no lap is recorded |
| `test_stopwatch_laps.py::TestDoublePressPause::test_double_press_during_flash_pauses` | Double press during the lap flash cancels the flash and pauses |
| `test_stopwatch_laps.py::TestDoublePressPause::test_single_select_resumes_after_double_press` | A single press resumes with no lap; laps work again after the resume |
| `test_stopwatch_laps.py::TestDoublePressPause::test_edit_mode_double_tap_adds_two_increments` | In New mode two fast presses are two +5 min presses |
| `test_stopwatch_laps.py::TestDoublePressPause::test_long_press_restarts_after_arm_and_disarm` | Long-press Select still restarts after a pause (disarm) and a resume (arm) |
| `test_stopwatch_laps.py::TestPressDownFreeze::test_frozen_value_equals_recorded_lap` | The display freezes with milliseconds at press-down; the lap has the same value |
| `test_main_logic.c::test_double_press_pauses_at_first_press_down`, `test_double_press_during_flash_pauses` | The pause uses the first press-down time; no lap slot is made |
| `test_main_logic.c::test_single_press_lap_uses_press_down_time` | The lap value is the value at press-down, not at the delayed single click |
| `test_main_logic.c::test_multi_click_subscribed_only_while_armed`, `test_handlers_refresh_the_click_config` | The double press is subscribed only for a running lap stopwatch in Counting mode |
| `test_main_logic.c::test_alarm_takeover_disarms_double_press`, `test_alarm_takeover_clears_the_freeze` | An alarm takeover ends the armed state and the freeze |
| `test_main_logic.c::test_double_press_blocked_by_input_guard` | The wakeup input guard blocks the double press |
| `test_main_logic.c::test_press_down_while_armed_freezes_display`, `test_press_down_when_not_armed_does_not_freeze`, `test_click_handlers_clear_the_freeze`, `test_lap_full_clears_the_freeze`, `test_freeze_safety_timeout`, `test_press_down_during_flash_freezes_running_stopwatch` | When the freeze starts and each event that ends it |
| `test/test_timer_multi.c::test_lap_at_uses_given_time`, `test_pause_at_*` | Unit tests: lap and pause at a given time |
| `test/test_drawing.c::test_freeze_shows_running_slot_paused_at_freeze_time`, `test_freeze_keeps_running_icons` | The frozen frame shows the value at the freeze time and does not change the timer |

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

**Not on aplite:** aplite has no button hint icons (`BUTTON_ICONS_FEATURE` in `src/drawing.h`; see "Aplite limits"). The buttons do the same there. The tests in this section skip on aplite. Unit test: `test_drawing.c::test_aplite_loads_and_draws_no_icons` (in `run_test_drawing_aplite`).

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

The repeat counter (e.g. `6x`) is drawn in **black** on color displays to match
the other (black) button icons, and **white** on black-and-white displays where
the corner background is dark. Color test: `test/test_drawing.c::test_repeat_counter_drawn_black`.

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

## Settings

Settings are configured via the Pebble mobile app (tap the gear icon next to the app). Changes are sent to the watch via AppMessage and persisted across launches.

**Not on aplite:** the settings page has no effect on aplite. The watch cannot open the message inbox there (it needs about 8KB of heap), so the code is compiled out (`SETTINGS_SYNC_FEATURE` in `src/settings.h`) and aplite uses the default of every setting ("Multiple Timers" is on).

| Setting | Default | Description |
|---------|---------|-------------|
| Increment Icons | On | Shows/hides the +1, +5, +20 button indicator icons in edit modes |
| Screen On (seconds) | 10 | How long the running-timer display keeps showing live seconds after any button press before dropping to a lower refresh rate (blanking the seconds digits). Clamped 1–3600 s. Drives `main_is_interaction_active()`. |
| Down Button Extra (seconds) | 60 | Length of the high-refresh window opened by a **Down** press in Counting mode, measured from the press (effectively `max(Screen On, this)` for a Down press, so with the default it keeps live seconds visible for a full 60 s instead of the usual 10 s). `0` disables the extension. Clamped 0–3600 s. Drives `main_is_last_interaction_down()`. |
| Swap Back / Select-Hold Buttons | Off | When on, swaps the functions of Back (short press) and Select (long press) in New and EditSec modes only. Back becomes the New↔EditSec mode toggle; Select long press becomes the +1hr / +1min time increment. The back button icon is replaced with an **m/s** indicator: **m** bold in New mode, **s** bold in EditSec mode. |
| Voice Naming (Pebble 2 only) | Off | When on (and running on an emery / microphone-capable watch), the Up + Back chord (Up pressed first) in New or EditSec mode launches voice dictation to rename the active timer. No effect on non-microphone platforms, where the feature is compiled out. |
| Lap Stopwatch (not on original Pebble) | Off | When on, pressing Select on a running **stopwatch** in Counting mode records a lap (paused copy in a new slot named `Lap [n]: <name>`) instead of toggling play/pause (a running countdown still toggles play/pause), a **double press** of Select pauses the running stopwatch (the lap is thus confirmed ~0.3 s after the press, and the display freezes at press-down), the main value shows the current split while the header shows the total (`-->12:34`), and long-press Select restarts the stopwatch with the lap session reset and a new mnemonic name (unless the user renamed it, in which case the custom name is kept). When off, a genuine stopwatch's header shows its `@`-prefixed start time instead of the total. See the Lap Stopwatch section. Compiled out on aplite (the original Pebble / Pebble Steel); the settings row is labelled accordingly. |

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
| `test_main_logic.c::test_down_click_in_new_mode_updates_backlight` | Down in New mode leaves the backlight consistent with edit mode (on) |
| `test_main_logic.c::test_down_click_in_edit_sec_mode_updates_backlight` | Down in EditSec mode leaves the backlight consistent with edit mode (on) |
| `test_main_logic.c::test_sim_light_stays_on_after_select_starts_timer` | Select that starts a timer right after its edit expires (during the 1 s edit linger) does not turn the light off |
| `test_main_logic.c::test_sim_light_stays_on_after_select_silences_alarm` | Select that silences an alarm does not turn the light off |

When a button press ends the app's forced backlight (edit mode or alarm), the app hands the light back to the system (`light_enable(false)`, which turns it off at once) and then calls `light_enable_interaction()`, so the light stays on for the system's normal timeout as after any press. Light changes from timers (edit linger, 30 s backlight timeout, alarm end) do not relight the screen.
