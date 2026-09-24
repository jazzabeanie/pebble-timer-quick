## Why

When the user opens the app just before a countdown ends, the Timer List opens and stays on screen when the alarm is due. The user does not see the alarm screen. Often the alarm does not ring at all. The cause has three parts:

- A user launch cancels all wakeups (`wakeup_cancel_all()` in `prv_initialize`), so the alarm cannot relaunch the app.
- The Timer List redraws its rows, but it never checks for an alarm.
- The main window under the list checks only the active slot. After `timer_persist_read()`, the active slot is slot 0, which is not always the timer that ends.

The same gap exists in the main window itself. It checks only the timer on screen. If another countdown ends while the user is on an alarm, on an edit screen, or on another running timer, it does not ring and does not show.

The gap also exists when the app is closed. On exit, the app schedules a wakeup only for the timer on screen. Any other countdown that ends while the app is closed never rings.

## What Changes

- While the Timer List is open, the app watches every countdown that was running with time left when the list opened. (The list cannot start or resume a timer, so no other countdown can end while it is open.) When one of them reaches zero, the app opens that timer, as if the user pressed Select on it: it becomes the active slot, the main window goes to Counting mode, and the list closes. The alarm screen shows, and the alarm vibrates.
- Unlike a Select on an existing timer, the implicit "New Timer" slot is **kept** as a running stopwatch (chrono). It is not discarded, and it shows in the list next time.
- When the list closes for an alarm, the input guard from `wakeup-input-guard` starts (`WAKEUP_INPUT_GUARD_MS`, now 250 ms). The user is often pressing buttons in the list at that moment, and such a press must not silence the alarm before the user has seen it.
- When the user opens the app (a user launch), and a saved held alarm exists, or a countdown ended in the last 5 s or ends in the next 5 s, the app opens straight to that timer in the main window. It does not show the Timer List. This covers the case in "Why" where the user opens the app just before a countdown ends.
- A countdown that ended more than 5 s before the app opened does not cause a takeover. The list opens as before.
- While the main window is open, the app also watches every other running countdown. When one ends while the main window shows a timer that is not alarming and not being edited (Counting mode), it takes over in the same way: it becomes the active timer, its alarm screen shows, and the input guard starts. The timer that was on screen keeps running.
- When one ends while the user is **busy** (the timer on screen is alarming, or the main window is in New mode or an edit mode), its alarm is **held**. The timer itself is not changed. The held alarm takes over as soon as the user is no longer busy (the alarm is silenced, snoozed, or stops by itself, or the edit ends). Up on an alarm silences it and opens the edit screen; the held alarm waits until that edit ends. The alarm screen then shows the real time since the timer ended. There is no vibration or other signal while an alarm is held.
- A held alarm vibrates for its full normal time (30 s) from the takeover. It does not auto-snooze because it waited.
- If several alarms are held, the one that ended first opens first. The others stay held until the user is free again.
- Back cannot exit while an alarm is held: during an alarm, Back silences it, and the held alarm then takes over. Hold Down (delete the timer and exit) also shows the held alarm instead of exiting.
- If the app closes by another path while an alarm is held (the system exit with hold Back, or another app opens), the app wakes up about 10 s later and shows the held alarm, the same as any alarm wakeup. Other held alarms are saved and stay held after that launch, so each one rings in turn.
- On every exit, the app schedules one wakeup for the next alarm event of **any** timer (a held alarm, or the countdown that ends first, active or not), and saves the others. It also schedules two backup wakeups, 2 min and 4 min later, in case the first one fails or is missed (for example, because another app has a wakeup within the same minute). A launch cancels the backups. After each launch, the app watches the other timers, and the next exit schedules the next event again.
- The app's 60 s auto-quit timer starts only when the time left is over 20 min (today it tests the timer's full length). It also never closes the app while an alarm vibrates or is held. Today it can close the app during the alarm of a long timer that had less than 60 s left when an edit ended; this change fixes that too.
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
- `list-alarm-takeover`: A countdown that reaches zero while it is not on screen opens its alarm screen and starts the input guard. From the Timer List, it closes the list and keeps the implicit new timer as a stopwatch. From the main window, it takes over at once, or it is held while the user is on an alarm or edit screen and takes over when the user is free.

### Modified Capabilities
<!-- none: the Select, Back, idle, and delete behavior of the Timer List does not change -->

## Impact

- `src/timer.c` / `timer.h`: a shared watch mask of countdown slots, kept correct by `timer_slot_delete()`; pure helpers that find an ended watched countdown and the soonest watched end time (unit-testable); a per-slot "alarm shown" offset so that a held alarm vibrates for its full time.
- `src/timer_list.c`: add running countdowns to the watch mask when the list opens, check it on each 500 ms refresh, and do the takeover.
- `src/main.c` / `main.h`: a new `main_show_alarm()` API. It sets Counting mode, stops the edit-expire timer, starts the input guard, and checks the alarm at once (the main refresh timer can be up to a minute away). A new main-window watch timer that fires at the soonest watched end time and does the takeover or the hold; the hold is re-checked at each event that ends "busy". The wakeup scheduling in `prv_terminate` changes to one primary (the next event of any timer) plus two backups. The auto-quit timer tests the time left, and its callback checks for alarms.
- Builds on the `wakeup-input-guard` capability (its guard state and helpers in `src/main.c`), archived 2026-09-24; see `openspec/specs/wakeup-input-guard/spec.md`.
- Aplite: compiled out with the `WAKEUP_GUARD_FEATURE` switch. The aplite heap is already below the ~1.6 KB floor. Aplite keeps today's behavior, except the auto-quit time-left test, which is on every platform.
- Tests: unit tests in `test/test_timer_multi.c` and `test/test_main_logic.c`; a functional test in `test/functional/`.
- `src/main.c` (`prv_terminate`, `prv_initialize`): on exit, schedule one wakeup for the next alarm event of any timer plus backups 2 min and 4 min later, and save the pending alarms in a new persist key; restore them on launch. No change to the saved timer data, so `PERSIST_VERSION` stays the same.
