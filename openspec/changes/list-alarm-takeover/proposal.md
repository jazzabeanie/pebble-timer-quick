## Why

When the user opens the app just before a countdown ends, the Timer List opens and stays on screen when the alarm is due. The user does not see the alarm screen. Often the alarm does not ring at all. The cause has three parts:

- A user launch cancels all wakeups (`wakeup_cancel_all()` in `prv_initialize`), so the alarm cannot relaunch the app.
- The Timer List redraws its rows, but it never checks for an alarm.
- The main window under the list checks only the active slot. After `timer_persist_read()`, the active slot is slot 0, which is not always the timer that ends.

The same gap exists in the main window itself. It checks only the timer on screen. If another countdown ends while the user is on an alarm, on an edit screen, or on another running timer, it does not ring and does not show.

The gap also exists when the app is closed. On exit, the app schedules a wakeup only for the timer on screen. Any other countdown that ends while the app is closed never rings.

## What Changes

- While the Timer List is open, the app watches every countdown that was running with time left when the list opened, and every saved held alarm. (The list cannot start or resume a timer, so no other countdown can end while it is open.) The Timer List counts as **busy**, so the user is not interrupted while choosing or setting a timer. When a watched countdown reaches zero, its alarm is **held**: the list stays open, the timer's row is marked with a large, clear alarm icon, and the watch vibrates **five short pulses** once for that alarm. This pattern is different from the single pulse for a new timer. The alarm vibration itself does not start in the list, not even for slot 0.
- The held alarm takes over when the user leaves the list: Select on any existing timer (the held alarm opens instead of the selected one), Back, the 30 s idle timeout, or hold Down on "New Timer" (these three no longer exit or background the app while an alarm is held). Select on "New Timer" opens New mode as before; the alarm stays held until the new timer is set. The list can therefore never hide an alarm for long: it shows at most 30 s after the last button press.
- The implicit "New Timer" slot follows the usual rule of the button that left the list: Back and idle keep it as a running stopwatch; Select on an existing timer and hold Down discard it.
- When a held alarm takes over, the input guard from `wakeup-input-guard` starts (`WAKEUP_INPUT_GUARD_MS`, now 400 ms), so the press that left the list, or one just after it, does not silence the alarm before the user has seen it.
- When the user opens the app (a user launch), and a saved held alarm exists (for example, a countdown that ended while the app was closed and whose wakeup was missed), the app does **not** open straight to a takeover of it. It opens as usual, and the alarm is held: its row is marked and the watch vibrates five short pulses when the list opens. When the alarm takes over, it vibrates for its full normal time. If the list does not show ("Multiple Timers" off), the only countdown is the timer on screen, so its alarm starts at launch and vibrates for its full normal time. A countdown that has not ended yet is watched in the same way. This covers the case in "Why" where the user opens the app just before a countdown ends.
- A countdown that ended before the app opened and is not a saved held alarm (for example, its alarm was silenced) is not held or marked. The list opens as before.
- While the main window is open, the app also watches every other running countdown. When one ends while the main window shows a timer that is not alarming and not being edited (Counting mode), it takes over in the same way: it becomes the active timer, its alarm screen shows, and the input guard starts. The timer that was on screen keeps running.
- When one ends while the user is **busy** (the Timer List is open, the timer on screen is alarming, or the main window is in New mode or an edit mode), its alarm is **held**. The timer itself is not changed. The held alarm takes over as soon as the user is no longer busy (the alarm is silenced, snoozed, or stops by itself, or the edit ends). Up on an alarm silences it and opens the edit screen; the held alarm waits until that edit ends. The alarm screen then shows the real time since the timer ended. In the main window, there is no vibration or other signal while an alarm is held; in the Timer List, the row mark and the five pulses are the signal.
- A held alarm vibrates for its full normal time (30 s) from the takeover. It does not auto-snooze because it waited.
- If several alarms are held, the one that ended first opens first. The others stay held until the user is free again.
- Back cannot exit while an alarm is held: during an alarm, Back silences it, and the held alarm then takes over. Hold Down (delete the timer and exit) also shows the held alarm instead of exiting.
- If the app closes by another path while an alarm is held (the system exit with hold Back, or another app opens), the app wakes up about 10 s later and shows the held alarm, the same as any alarm wakeup. Other held alarms are saved and stay held after that launch, so each one rings in turn.
- An alarm stays pending until it has rung and stopped (the user silences or snoozes it, or it stops on its own). A takeover or a launch that shows the alarm does not end this. If the app closes while the alarm on screen is still pending (for example, another app opens before the user presses a button), the app treats it as a held alarm and wakes up about 10 s later. This applies to the active timer's own alarm too. Today, that alarm is lost.
- On every exit, the app schedules one wakeup for the next alarm event of **any** timer (a held alarm, or the countdown that ends first, active or not), and saves the others. It also schedules two backup wakeups, 2 min and 4 min later, in case the first one fails or is missed (for example, because another app has a wakeup within the same minute). A launch cancels the backups. After each launch, the app watches the other timers, and the next exit schedules the next event again.
- The app's 60 s auto-quit timer starts only when the time left is over 20 min (today it tests the timer's full length). It also never closes the app while an alarm vibrates or is held. Today it can close the app during the alarm of a long timer that had less than 60 s left when an edit ended; this change fixes that too.
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
- `list-alarm-takeover`: A countdown that reaches zero while it is not on screen opens its alarm screen and starts the input guard. In the Timer List, it is held: its row is marked with an alarm icon, the watch vibrates five short pulses, and the alarm takes over when the user leaves the list. From the main window, it takes over at once, or it is held while the user is on an alarm or edit screen and takes over when the user is free.

### Modified Capabilities
- `wakeup-input-guard`: The guard no longer applies only to wakeup launches. It starts whenever an alarm shows: at a wakeup launch, at an alarm takeover (from the Timer List or the main window, including a held alarm that takes over when the user leaves the list), and at every alarm start, including the alarm of the countdown already on screen and a snoozed timer that rings again. `WAKEUP_INPUT_GUARD_MS` goes from 250 ms to 400 ms. It stays off on aplite. The Timer List's Select, Back, idle, and hold Down behavior changes only while an alarm is held (see `list-alarm-takeover`).

## Impact

- `src/timer.c` / `timer.h`:
  - a shared watch mask of countdown slots (`timer_watch_add_running()`, `timer_watch_clear()`, `timer_watch_mask()`), with a compile-time check that `MAX_TIMERS <= 32`;
  - pure helpers that the unit tests can call: `timer_running_countdown_mask()`, `timer_find_ended_countdown()`, `timer_ended_mask()`, and `timer_next_watched_end_ms()`;
  - a per-slot "alarm shown" offset (`s_alarm_shown_slot`, `s_alarm_shown_ms`), so that a held alarm vibrates for its full time (D11);
  - `s_alarm_rang_slot`, so that an alarm stays pending until it has rung and stopped (D16);
  - `timer_slot_delete()` shifts the watch mask and moves the two per-slot values (D3).
- `src/timer_list.c`:
  - add running countdowns to the watch mask when the list opens;
  - `prv_update_alarm_marks()`, called at window load and on each 500 ms refresh: find ended watched slots, mark their rows with the new alarm icon, and vibrate five short pulses once per alarm;
  - on Select on an existing timer, Back, idle, and hold Down on "New Timer", pop the list and let a held alarm take over;
  - log `timer_list_hide` in the window unload.
- `resources/` and `package.json`: a new alarm icon image (`IMAGE_ICON_LIST_ALARM`) for the list rows.
- `src/main.h`: `WAKEUP_INPUT_GUARD_MS` goes from 250 to 400 (D17).
- `src/main.c` / `main.h`:
  - a new `main_show_alarm()` API. It sets Counting mode, stops the edit-expire and auto-quit timers, starts the input guard, marks the alarm as shown, checks the alarm at once (the main refresh timer can be up to a minute away), and then re-arms the main-window watch (D5);
  - a new `main_watch_arm()` API, which the list calls when it returns to the main window;
  - while the Timer List is on top, the main window does not check or vibrate the active slot's alarm;
  - a new main-window watch timer (`prv_watch_arm()`) that fires at the soonest watched end time and does the takeover or the hold. It runs at each event that ends "busy", and it clears the pending state of an alarm that has rung and stopped (D8, D9, D16);
  - hold Down shows a held alarm instead of exiting (D14);
  - the auto-quit timer tests the time left, and its callback checks for alarms (D15);
  - the guard starts at every alarm start, and `s_restart_guard_on_alarm` is removed (D17).
- `src/main.c` (`prv_terminate`, `prv_initialize`): on exit, schedule one wakeup for the next alarm event of any timer, plus backups 2 min and 4 min later, and save the pending alarms in a new persist key (`PERSIST_PENDING_MASK_KEY`). Restore them on every launch. A user launch never opens straight to a takeover (D13). No change to the saved timer data, so `PERSIST_VERSION` stays the same.
- Builds on the `wakeup-input-guard` capability (its guard state and helpers in `src/main.c`), archived 2026-09-24; see `openspec/specs/wakeup-input-guard/spec.md`.
- Aplite: every part of this change is on aplite too, so no timer fails to ring there. The one exception is the input guard, which stays compiled out on aplite (`WAKEUP_GUARD_FEATURE`), as today. Without it, a stray press can silence or snooze an alarm, but the alarm has still rung. The aplite heap is already below the ~1.6 KB floor, so the change is measured and tested on aplite. If it does not fit, a follow-up change trims it (see design D6).
- Tests: unit tests in `test/test_timer_multi.c` and `test/test_main_logic.c`; a new functional test file, `test/functional/test_list_alarm_takeover.py`; and existing tests that press a button within 400 ms of an alarm start or a wakeup launch get a wait past the guard window.
- `docs/button-functions.md` is updated.
