## Context

On a user launch with saved timers (and "Multiple Timers" on, the default), `prv_initialize` does three things:

1. It calls `wakeup_cancel_all()`.
2. It loads all slots with `timer_persist_read()`, which sets the active slot to 0.
3. It pushes the Timer List on top of the main window.

The list (`src/timer_list.c`) has a 500 ms refresh timer (`REFRESH_MS`) that only redraws. It creates an implicit "New Timer" slot as a running chrono (`timer_slot_create()`: `start_ms = epoch()`, not paused). The main window's `prv_app_timer_callback` runs `timer_check_elapsed()` for the active slot only. The main timer can be up to a minute away, because `REDUCE_SCREEN_UPDATES` sets its interval from the active slot's value.

So a countdown that ends while the list is open either vibrates unseen behind the list (slot 0) or does not ring at all (any other slot).

The main window has the same gap. It checks only the active slot, so a non-active countdown that ends while the main window is open does not ring at all. The main window has no window appear or disappear handlers. The active slot can also change in the main window: the lap view (`prv_flash_view_lap`) switches to a lap slot. `drawing.c` swaps the active slot for a moment during each render (`prv_apply_slot_override`), so `timer_set_active_slot()` is not a safe place to clear per-slot state. The only main-window delete (hold Down) exits the app.

`timer_check_elapsed()` stops the vibration when the overtime passes `VIBRATION_LENGTH_MS` (30 s), and then it auto-snoozes by `SNOOZE_INCREMENT_MS` (5 min). So a timer that is opened more than 30 s after its end does not vibrate; it snoozes at once.

The wakeup input guard (`wakeup-input-guard` capability) is in `src/main.c`: `s_wakeup_launch_ms` (low 32 bits of `epoch()`), the `s_blocked_buttons` bitmask with the `WAKEUP_GUARD_OPEN` bit, `prv_press_down_blocked()`, and `prv_press_blocked()`. `prv_start_input_guard()` records the time and sets `s_blocked_buttons = 0xFF`. On a wakeup launch, `prv_initialize` calls it and sets `s_restart_guard_on_alarm`, and `prv_app_timer_callback` restarts the guard at the first alarm start. The Timer List shows only on user launches, so that flag is always false while the list is open. The code is compiled out on aplite (`WAKEUP_GUARD_FEATURE`), and it stays out there (D6). `WAKEUP_INPUT_GUARD_MS` is 250; this change makes it 400 and starts the guard at every alarm start (D17).

## Goals / Non-Goals

**Goals:**
- The Timer List is busy: a countdown that ends while it is open is held, its row is marked with a clear alarm icon, and the watch vibrates five short pulses, within one refresh (500 ms). The held alarm takes over when the user leaves the list (D4).
- The implicit new timer follows the usual rule of the button that leaves the list.
- The input guard protects the alarm at the takeover, as it does on a wakeup launch (not on aplite, D6).
- Keep the detection logic in a pure helper that the unit tests can call.
- In the main window, a non-active countdown that ends takes over at its end time when the user is not busy.
- When the user is busy (an alarm or an edit screen), the alarm is held without changing the timer, and it takes over as soon as the user is free, with its full vibration.
- A held alarm still rings if the app closes: hold Down shows it instead of exiting (D14), and other exits wake the app about 10 s later (D12).
- On every exit, the app schedules one wakeup for the next alarm event of any timer (a held alarm or the soonest countdown end), plus two backups 2 min and 4 min later in case the first is missed (D12).
- The auto-quit timer starts only when the time left is over 20 min, and it never closes the app while an alarm vibrates or is held (D15).
- Every part of this change is on every platform, including aplite, so no timer fails to ring there. The one exception is the input guard, which stays off on aplite (D6).
- A user launch never opens straight to an alarm. A saved held alarm is held, as if it ended while the app was open (D13).
- An alarm stays pending until it has rung and stopped. If the app closes first, the alarm is held and rings again about 10 s later (D16).

**Non-Goals:**
- Taking over for countdowns that were already overdue or paused when the list opened.
- A signal while an alarm is held in the main window (behind an alarm or an edit screen). Only the Timer List signals a held alarm (D4).

## Decisions

### D1. A shared watch mask of countdowns that were seen running with time left

`src/timer.c` keeps `static uint32_t s_watch_mask`. Bit *i* means "slot *i* was seen running with time left, and its alarm is still pending" (it has not rung and stopped yet, D16). `MAX_TIMERS` is at most 32, so a `uint32_t` fits. Add a compile-time check for this.

- `timer_running_countdown_mask()` returns the slots that are running (not paused) and have time left (`length_ms - elapsed > 0`).
- `timer_watch_add_running()` does `s_watch_mask |= timer_running_countdown_mask()`. It only adds bits. A bit stays set after its countdown ends, until the alarm is shown, so an ended (held) slot stays watched.
- `timer_watch_clear(slot)` clears one bit. D16 calls it when the active slot's alarm has rung and stopped.
- `timer_watch_mask()` returns the mask.

The list calls `timer_watch_add_running()` in `prv_window_load`, before the implicit slot is created. The main-window watch (D8) calls it each time it re-evaluates, so a countdown that stops being the active slot (after a takeover) is added while it still has time left.

A countdown that is overdue or paused when it is first seen is not added, so it can never take over. Only the active slot can be started or resumed, and it is excluded from the check (D2), so no countdown is missed.

*Alternative:* Treat any running countdown that ended in the last *N* ms as "just ended". Rejected. After a delayed refresh it cannot tell "ended just now" from "was overdue at open", and it depends on refresh timing.

### D2. Detect the end in a pure helper in `timer.c`

Add `int8_t timer_find_ended_countdown(uint32_t mask)` to `src/timer.c`. It returns the slot, among the mask's bits, whose countdown has reached zero (`remaining <= 0`) and has the lowest remaining value (the one that ended first), or -1 if none has ended. It reads `timer_slots` and `epoch()` only, so `test/test_timer_multi.c` can test it directly.

The list uses `timer_ended_mask()` (D4) every 500 ms, and `timer_find_ended_countdown()` to pick the held alarm that ended first when the user leaves the list. That gives a delay of at most one refresh. The main-window watch (D8) calls it with `timer_watch_mask() & ~(1 << active)`, because the main window already checks the active slot.

Add `uint32_t timer_ended_mask(uint32_t mask)`. It returns the mask's slots whose countdown has reached zero. The list uses it to find the rows to mark (D4).

Add `int64_t timer_next_watched_end_ms(uint32_t mask)`. It returns the time in ms until the soonest end among the mask's slots that still have time left, or -1 if none. D8 uses it to schedule its timer.

*Alternative:* Register an `AppTimer` for the soonest end time in the list. Rejected for the list. The list already has a 500 ms refresh, and 500 ms is fine for an alarm. The main window has no such refresh (its refresh can be up to a minute away), so D8 does use a timer at the soonest end time.

### D3. Keep the mask in step with slot deletes

`timer_slot_delete(i)` moves every slot above *i* down by one. It applies the same move to `s_watch_mask`: it drops bit *i* and shifts the higher bits down by one. Because this is inside `timer_slot_delete()`, every delete path keeps the mask correct (the list's hold Down, the list's implicit-slot deletes, and the main window's hold Down, which then exits). `test/test_timer_multi.c` can test it directly.

### D4. The Timer List holds, marks, and signals alarms; they take over when the user leaves

The Timer List is busy (D9). The user opened the app to choose or set a timer, and an alarm must not take the screen while they do that. So an alarm that ends in the list is held, but the user is told at once.

**Hold, mark, and signal.** `src/timer_list.c` keeps `static uint32_t s_alerted_mask` (not saved; cleared in `prv_window_load`). In `prv_window_load` (after `timer_watch_add_running()`) and in each `prv_refresh_callback` (500 ms):

1. `ended = timer_ended_mask(timer_watch_mask())`. This includes saved held alarms (D12) and countdowns that ended while the list is open.
2. `new = ended & ~s_alerted_mask`. If `new` is not 0: vibrate five short pulses once (`vibes_enqueue_custom_pattern`, 5 × 100 ms on with 100 ms off; `LIST_ALARM_PULSES`), log `TEST_STATE:vibe,src=list_alarm` and `TEST_STATE:list_alarm_held,slot=<n>` for each new slot, and set `s_alerted_mask |= new`. Two alarms that end in the same refresh give one pattern.
3. Mark the row of every slot in `ended` with the alarm icon, and redraw.

The five pulses are different from the single `vibes_short_pulse()` of "New Timer" (`src=list_new`) and the three vibrations of the slot-limit warning.

`timer_slot_delete()` shifts the watch mask (D3). The list shifts `s_alerted_mask` in the same way in its delete paths, so a delete never re-signals or loses a mark.

**The alarm icon.** Add a new image resource, `IMAGE_ICON_LIST_ALARM`: a bell, large and bold, sized to the full height of the row's name line or more, so it is very clear. Draw it at the left edge of the row, before the name, and shift the name and time to its right. Tint it to the row's text color, as the repeat glyph is (`prv_create_tinted_repeat_icon()`): black on light rows, white on the black selected row. Load the two tinted copies only while at least one row is marked, and free them in the window unload, so they cost no heap when no alarm is held.

**No vibration behind the list.** The main window under the list checks the active slot (slot 0 after `timer_persist_read()`). While the list is on top, `prv_app_timer_callback()` does not call `timer_check_elapsed()`, so slot 0's alarm does not start behind the list. It only reschedules itself. Every list exit that returns to the main window runs the check again: `main_show_alarm()` (D5) does it, and the existing Select path calls `main_watch_arm()` and the main refresh.

**Take over when the user leaves.** When a list handler below leaves the list and `timer_ended_mask(timer_watch_mask())` is not 0, the held alarm takes over:

| Action | Held alarm to show | Implicit slot |
|---|---|---|
| Select on a held timer's row | that timer | discarded (the Select rule) |
| Select on another existing timer's row | the first to end (`timer_find_ended_countdown()`); the selected timer is not opened or changed | discarded (the Select rule) |
| Back | the first to end, instead of exiting | kept as a stopwatch (the Back rule) |
| 30 s idle (`prv_idle_callback`) | the first to end, instead of `window_stack_pop_all()` | kept as a stopwatch (the idle rule) |
| Hold Down on "New Timer" | the first to end, instead of exiting | discarded (the hold Down rule) |

For each takeover: delete the implicit slot first if the rule says so (this shifts the masks, so read the held slot after it), `timer_set_active_slot(slot)` (do not clear its watch bit, D16), log `TEST_STATE:list_alarm_takeover,slot=<n>`, call `main_show_alarm()` (D5), and `window_stack_pop(true)`. The window unload cancels the list's idle and refresh timers.

The other list actions do not change:

- Select on "New Timer": New mode, one short pulse, as today. New mode is busy, so D8/D9 hold the alarm and take it over when the edit ends.
- Select on "Delete all": the hint, as today.
- Hold Down on a timer row: delete it, as today. If it was a held timer, its alarm goes with it.
- Hold Down on "Delete all": delete every timer and exit, as today. No alarm is left.

The idle timer restarts at every press, so the list hides a held alarm for at most 30 s after the last press. If the app still closes (the system exit, or another app opens), the held alarm gets a wakeup 10 s later (D12, D16).

*Alternatives:*
- Close the list and show the alarm at once (the first plan). Rejected by the user: it interrupts a user who is about to set a timer.
- Hold only the alarms that were already held at launch, and take over at once for an alarm that ends in the list. Rejected by the user in favor of one rule for the list.
- Show the timer the user selected, then let the held alarm take over from the main window. Rejected. The selected timer would flash on screen first.

### D5. `main_show_alarm()` in `main.c`

Add a new public API that the list takeover (D4) and the main-window takeover (D10) call:

- `main_set_control_mode(ControlModeCounting)` (this also cancels any lap flash), clear `is_reverse_direction`, and stop the edit-expire timer.
- Cancel the auto-quit timer (`prv_cancel_quit_timer()`). An edit that expires on a long timer starts a 60 s quit timer (`QUIT_DELAY_MS`); without this, the app would quit while the new alarm shows.
- Start the input guard: call the existing `prv_start_input_guard()` directly. Do not rely on the alarm-start guard (D17) instead: the slot can already be `elapsed` (for example, a held alarm that the main window checked before it was held), so there may be no not-elapsed to elapsed change, and the alarm-start guard would not fire.
- Mark the alarm as shown now (D11), so that it vibrates for its full time.
- `prv_record_interaction()` (screen-on window and fast refresh).
- Re-arm the main-window watch (D8).
- Cancel `main_data.app_timer` and call `prv_app_timer_callback(NULL)` at once. It runs `timer_check_elapsed()` on the new active slot. That starts the vibration, logs `alarm_start`, turns on the backlight, and reschedules the refresh for the new slot.

A button held in the list at the takeover (for example, the hold Down on "New Timer" that caused it) has no press-down in the main window. The 0xFF mask blocks its release, as it blocks a press held across a wakeup launch.

### D8. Main-window watch timer

`src/main.c` gets one `AppTimer *s_watch_timer` and `prv_watch_arm()`:

1. Cancel `s_watch_timer`.
2. If the main window is not the top window (the Timer List is open), stop. The list does its own takeover, and every list exit path that returns to the main window calls `main_watch_arm()`.
3. Run the D16 check for the active slot. Then `timer_watch_add_running()`. Let `mask = timer_watch_mask() & ~(1 << active)`.
4. If `timer_find_ended_countdown(mask)` returns a slot: if the user is busy (D9), hold it (no timer is scheduled for it; D9 re-runs the check when the user is free); otherwise take over (D10).
5. Otherwise, if `timer_next_watched_end_ms(mask)` returns a time, schedule the timer for that time. Otherwise leave it off.

The timer callback calls `prv_watch_arm()`. `prv_watch_arm()` also runs at the end of `prv_initialize` when no list is shown, from `main_watch_arm()` when the list closes, after the main takeover, after the lap view switches the active slot, and at each event that can end "busy" (D9).

*Alternatives:*
- Check the other slots in `prv_app_timer_callback`. Rejected. With `REDUCE_SCREEN_UPDATES`, that refresh can be up to a minute away.
- Poll every second. Rejected. It wakes the watch every second only to find nothing.

### D9. Busy means an alarm or an edit screen

The user is busy when the Timer List is on top (D4 does the hold there), the active timer is alarming (`timer_is_vibrating()`), or the control mode is not `ControlModeCounting` (New, EditHr, EditMin, EditSec, EditRepeat). A held alarm does not change its timer: its end time, length, and base length stay the same, and its watch bit stays set.

There is no periodic re-check. The held alarm takes over at the first event that ends "busy". `prv_watch_arm()` runs after each such event:

- the end of every main-window click handler, after the handler has made all its changes. This covers Select, Back, and Down on an alarm (silence, pause, snooze) and every button that leaves an edit mode;
- the edit-expire callback, after an edit expires to Counting;
- `prv_app_timer_callback()` when the active timer stops vibrating on its own (the 30 s vibration ends and it auto-snoozes).

The check never runs in the middle of a handler, only at its end, so it always sees the final state. This matters for Up on an alarm: Up silences the alarm and enters edit mode. At the end of the handler the main window is in an edit mode, so the user is still busy, and the held alarm stays held. It does not replace the edit screen. It takes over when that edit ends. The same is true for any other button that goes from an alarm into an edit mode.

A unit test covers each of these exits from "busy", and the Up case (D7), because a missed hook would leave the alarm held until the next event.

*Alternatives:*
- Re-check every few seconds while an alarm is held. Rejected. The event hooks cover every way out of "busy", so a timer only adds wakeups.
- Add a few seconds to the held timer's `length_ms` at each check. Rejected. The list and the alarm screen would show a later end than the real one, and the overtime would be understated.

### D10. Main-window takeover

When D8 finds an ended slot and the user is not busy:

1. `timer_set_active_slot(slot)`. Do not clear its watch bit (D16).
2. Log `TEST_STATE:main_alarm_takeover,slot=<n>`.
3. Call `main_show_alarm()` (D5).

The timer that was on screen stays saved and keeps running. If it is a countdown with time left, the next `prv_watch_arm()` adds it to the mask, so its own alarm is also watched.

### D11. A held alarm vibrates for its full time

`src/timer.c` keeps two values that are not saved: `s_alarm_shown_slot` (-1 when unset) and `s_alarm_shown_ms` (the overtime when the alarm was shown). `main_show_alarm()` sets them for the active slot. In `timer_check_elapsed()`, the 30 s vibration limit compares `overtime - s_alarm_shown_ms` when the active slot is `s_alarm_shown_slot`, and the plain overtime otherwise. `timer_increment()`, `timer_reset()`, and `timer_repeat_restart()` clear the values for that slot.

The values are keyed by slot, not cleared in `timer_set_active_slot()`, because `drawing.c` swaps the active slot during each render. The display still shows the real overtime.

### D12. One wakeup for the next alarm event of any timer, plus two backups

The SDK sets three limits on `wakeup_schedule()`: at most 8 wakeups per app, no wakeup within 1 minute of any other scheduled wakeup (from any app; this returns `E_RANGE`), and no time in the past (`E_INVALID_ARGUMENT`). The app already calls `wakeup_cancel_all()` at the start of every launch.

Today, `prv_terminate` schedules a wakeup only for the active countdown. A non-active countdown that ends while the app is closed never rings. This change fixes that: in `prv_terminate`, the app schedules only the **next** alarm event of **any** timer, and saves the rest:

1. The candidates are:
   - the held alarms: the ended slots in `timer_watch_mask()`. This includes the active slot when its alarm is still pending (D16). Their event time is the current whole second + `HELD_WAKEUP_DELAY_S` (10 s). This gives the user time to deal with the screen that closed the app (for example, another app).
   - every countdown that is running with time left, active or not (`timer_running_countdown_mask()`). Its event time is its end.
2. Save the pending mask (the held bits, plus every running countdown's bit) with `persist_write_int(PERSIST_PENDING_MASK_KEY, mask)`.
3. Schedule one primary wakeup at the earliest event time. The cookie is its slot (for held alarms, the one that ended first; for countdowns, the one that ends first).
4. Schedule a first backup at the primary time + `BACKUP_WAKEUP_DELAY_S` (2 min), and a second backup at the primary time + 2 × `BACKUP_WAKEUP_DELAY_S` (4 min), both with the same cookie. They are 2 min apart, outside each other's 1-minute window. Each one is scheduled even if an earlier one failed.

There are never more than 3 of our wakeups at a time, 2 min apart, so the 1-minute rule cannot fail between our own wakeups, and the 8-wakeup limit is never close.

The chain covers the other timers: each launch reads the saved mask, and the app watches the other countdowns while it is open (D8). At the next exit, `prv_terminate` schedules the next event again.

- **The primary fires:** the launch calls `wakeup_cancel_all()`, which cancels both backups. No other code is needed.
- **The primary fails or is missed** (for example, another app has a wakeup within 1 minute of it, so `wakeup_schedule` returns `E_RANGE`): the first backup fires 2 min late. If it also fails, the second backup fires 4 min late. Late is better than never. The alarm shows the real overtime and vibrates for its full time (D11).
- **All three fail:** log the results. The pending mask is still saved, so the alarm is held at the next open (D13).
- **A second countdown ends within the 2 or 4 min before a backup fires:** it is in the saved mask, so after that launch it is a held alarm and takes over in turn.

In `prv_initialize`, on every launch, read `PERSIST_PENDING_MASK_KEY` and OR it into the watch mask (then delete the key):

- Saved bits whose countdown has ended are held alarms, not "overdue at open" countdowns. Saved bits that still have time left are watched as usual.
- On a wakeup launch, the cookie slot becomes active as today. If it has already ended, its alarm is marked as shown at launch (D11), so it vibrates for its full time. Its watch bit stays set until the alarm has rung and stopped (D16). The other saved bits stay, and D8 takes them over in turn.
- On a user launch before the wakeup, the held alarm is held (D13): marked in the list, or taken over by the main window when the user is free.

This also closes a gap in the old two-wakeup plan: a countdown whose own wakeup failed and that ended before the relaunch was not watched. Now its bit is saved, so it becomes a held alarm. The same is true for a countdown that ends between the primary and a later launch.

Back and hold Down cannot close the app while an alarm is held (D9, D14). So the 10 s held delay applies only to exits that the app cannot stop: the system exit (hold Back) and another app that opens.

The saved mask uses slot indices. The slots are saved in the same order, and slots are deleted only while the app is open, so the indices stay valid. The key is new, and the saved timer data does not change, so `PERSIST_VERSION` stays the same. A missing key reads as 0.

*Alternatives:*
- Schedule a wakeup for each alarm event. Rejected. The 1-minute rule makes any two events within a minute fail, and the 8-wakeup limit caps the count.
- Schedule the held alarm and the active countdown separately. Rejected. They can be within 1 minute of each other, and one then fails.
- No backup. Rejected. A wakeup from another app within 1 minute of ours would make our alarm never ring.
- A separate change for the non-active countdowns. Rejected. The next-event wakeup covers them with no extra code.

### D13. A user launch holds a saved held alarm; it never opens straight to it

On a user launch (not a wakeup), `prv_initialize` restores the saved pending mask into the watch mask (D12), as on every launch. It does not look for a due slot, and it opens as usual: the Timer List if it shows, or the main window.

Each saved bit whose countdown has ended is a held alarm, the same as one that ended while the app was open:

- If the Timer List shows, D4 marks its row and vibrates the five pulses when the list opens. It takes over when the user leaves the list.
- If the list does not show ("Multiple Timers" off), the main window shows slot 0. With the setting off, the app cannot make a new countdown slot (the list makes them; laps are stopwatches), so slot 0 is the only countdown in normal use, and a held bit on it is the **active timer's own alarm**, not a takeover. Mark it as shown at launch (D11), the same as on a wakeup launch. Without this, `timer_check_elapsed()` counts the 30 s vibration from the timer's end, so an alarm that ended 2 min ago would auto-snooze at once and never vibrate. Its first `prv_app_timer_callback()` starts the vibration, and the alarm-start guard starts (D17). A held bit on another slot (a countdown left from when the setting was on) follows the main-window rules through `prv_watch_arm()` at the end of `prv_initialize` (D8).

When a held alarm takes over, `main_show_alarm()` marks it as shown (D11), so it vibrates for its full time, and starts the guard (D5). Its watch bit stays set until the alarm has rung and stopped (D16).

A countdown that has not ended at the launch is watched as usual: D4 holds it in the list, and D8 to D10 take it over or hold it in the main window. A countdown that ended before the launch and has no saved bit is not watched ("overdue at open"). This is a countdown whose alarm the user already stopped (its bit was cleared, D16), or one from a run where `prv_terminate` did not run (a crash, a battery pull, or a reboot). The list opens as before.

*Alternatives:*
- Open straight to a saved held alarm and skip the list (the earlier plan). Rejected by the user. A user who opens the app to set a timer must not be taken away from that task. The most common case (the user reopens the app during the 10 s after another app closed it) still gets a clear signal: the marked row and the five pulses.
- Also open straight to a countdown that ends in the next 5 s, or that ended in the last 5 s. Rejected for the same reason. The 5 s-after case was also covered by the saved mask in all but a crash.

### D14. Hold Down shows a held alarm instead of exiting

In the main window, hold Down deletes the active timer and exits (`prv_down_long_click_handler`). After `timer_slot_delete()` (which shifts the watch mask, D3), if the watch mask has an ended slot, take it over (D10) and do not pop the window. Otherwise, exit as today.

### D15. The auto-quit timer never closes the app during an alarm

After an edit expires on a timer longer than 20 min (`AUTO_BACKGROUND_TIMER_LENGTH_MS`), the app starts a 60 s quit timer (`QUIT_DELAY_MS`). The test is on the timer's length (`length_ms`), not its time left. So a long timer with less than 60 s left can start its alarm before the quit timer fires, and the quit then closes the app during the alarm. This can happen today, without this change.

- Test the time left: start the quit timer only for a countdown whose time left (`timer_get_value_ms()`) is over 20 min. Then the active timer's own alarm cannot start within the 60 s. The chrono rule (`AUTO_BACKGROUND_CHRONO`, off) does not change.
- Another timer can still end within the 60 s. So also cancel the quit timer in `main_show_alarm()` (D5), and in `prv_quit_callback()`, do not quit if the active timer is vibrating or if the watch mask has a held alarm (an ended slot that is not the active slot). In that case, run `prv_watch_arm()` instead, so a held alarm takes over.

*Alternative:* keep the length test and cancel the quit timer at every alarm start. Rejected. The time-left test stops the quit timer from starting at all in that case, which is simpler.

### D16. An alarm stays pending until it has rung and stopped

A takeover or a launch clears nothing. The slot's watch bit stays set until its alarm has rung and stopped. Before this, D4, D10, D12, and D13 cleared the bit when the alarm was shown. If the app then closed before the user acted (another app opened, or a system exit during the guard window), the timer was active and ended, but it had no bit. So `prv_terminate` saved nothing and scheduled nothing for it, and at the next open it was "overdue at open". The user never saw that alarm.

`src/timer.c` keeps `s_alarm_rang_slot` (-1 when unset, not saved). `prv_app_timer_callback()` sets it to the active slot where it logs `alarm_start`. It is cleared in the same places as the D11 values.

The D16 check runs at the start of `prv_watch_arm()` (D8). So it runs at the end of every main-window click handler, when the vibration stops on its own, and at every other D8 re-check:

- If the active slot's watch bit is set, `s_alarm_rang_slot` is the active slot, and `timer_is_vibrating()` is false, call `timer_watch_clear(active)`.

This covers every way an alarm stops: Select, Back, Down, and Up on the alarm (they set `can_vibrate = false` or snooze), and the 30 s vibration ending on its own. A press that the input guard ignores does not run its handler, so the alarm stays pending. Aplite has no guard, so there every press counts (D6). Before the vibration starts, `s_alarm_rang_slot` is not the active slot, so the bit stays set.

The check runs before the takeover step, so a held alarm takes over in the same call in which the first alarm is cleared. After a snooze or a repeat restart, the slot has time left again, so it is an ordinary watched countdown.

In `prv_terminate`, an ended slot whose bit is set is a held alarm (D12), even if it is the active slot. So the app wakes up about 10 s later and shows it again, with its full vibration (D11). This also covers the active timer's own alarm, not only a takeover: today, if another app opens during an alarm, the alarm is lost.

*Alternatives:*
- Clear the bit when the vibration starts. Rejected. The vibration can start and the app can close a moment later, before the user sees the screen.
- Clear the bit in each silence and snooze path. Rejected. There are many paths, and a missed one leaves a stale held alarm. One check in `prv_watch_arm()`, which already runs after every such event (D9), covers them all.

### D17. The guard starts at every alarm start, and it is 400 ms

The user wants the guard every time an alarm shows, including the alarm of the countdown already on screen. A press meant for the running timer (for example, a Down to add time just before it ends) must not snooze the alarm that has just started.

- `WAKEUP_INPUT_GUARD_MS` in `src/main.h` goes from 250 to 400.
- In `prv_app_timer_callback()`, on every not-elapsed to elapsed change, call `prv_start_input_guard()` (inside `#if WAKEUP_GUARD_FEATURE`). This covers the on-screen timer's own alarm, the early-wakeup case, and a snoozed or repeated timer that reaches zero again. Keep the `guard_restart` log there, so the functional tests can see it.
- Remove `s_restart_guard_on_alarm`. The alarm-start guard does its job for every launch, so the flag is not needed.
- The guard at a wakeup launch (at `prv_initialize`) and in `main_show_alarm()` (D5) stays. In those cases the alarm can already be vibrating, so there is no alarm start.
- The guard is the same `s_blocked_buttons = 0xFF` state, so a button held at the alarm start is ignored on release.

*Alternative:* guard only when the screen changes (takeovers and launches). Rejected by the user: the on-screen timer's alarm is guarded too.

### D6. Aplite

No timer may fail to ring on any platform, so every part of this change is on aplite too, **except the input guard**. The guard only decides what a press does after the alarm has rung. Without it, a stray press can silence, snooze, or edit the alarm, but the screen has already changed and the watch has buzzed, so the alarm is not missed. The guard costs about 336 bytes, and on aplite that RAM is better spent on the code that makes alarms ring.

- `WAKEUP_GUARD_FEATURE` stays 0 on aplite, as today. The aplite rule of the `wakeup-input-guard` capability does not change. That capability's "only wakeup launches" rule is widened to every time an alarm shows (D17 and its delta spec).
- Only the guard calls are inside `#if WAKEUP_GUARD_FEATURE`: `prv_start_input_guard()` in `main_show_alarm()` (D5) and at the alarm start (D17). All other new code is on every platform, including the list's alarm icon and five-pulse signal (D4), because in the list they are how the user learns that an alarm is due.
- On aplite, every press counts for D16, so a stray press ends the pending state.
- On aplite, nothing blocks the release of a button that was held down in the list at the takeover (D5), for example the hold Down on "New Timer" that makes a held alarm take over. The press-down was in the list window, so the main window should get only the release, and no click. A functional test on aplite checks that this release does not delete, snooze, or exit.
- The alarm icon's two tinted bitmaps use heap only while a row is marked (D4). Include a marked list in the aplite measurement.

The aplite 24 KB app region holds the code and the heap. The heap was 1365 bytes before this change, below the ~1.6 KB floor. So the fit is not known yet. Measure it:

- Build aplite and record the heap (`Total footprint in RAM`) and the code size (`arm-none-eabi-size build/aplite/pebble-app.elf`), before and after.
- Run the unit tests and the full functional suite on aplite, including the new tests. Check the logs for `App fault` and for failed allocations in text rendering.

If aplite does not work well, trim in a follow-up change. Trim what costs RAM but does not stop a timer from ringing, in this order:

1. RAM use that has nothing to do with alarms: the mnemonic tables (`s_nouns` 240 bytes, `s_adjectives` 96 bytes), long `TEST_LOG` format strings (use `test_log_state()`), and 64-bit time math that can be 32-bit.
2. Fewer slots on aplite (`MAX_TIMERS`, 56 bytes each).
3. The second backup wakeup (keep the primary and the first backup).

Keep these on aplite in every case, because without them a timer can fail to ring: the next-event wakeup and the saved mask (D12), the pending alarm (D16), the launch rule (D13), the main-window watch and held alarms (D8 to D10, D14), the list hold, icon, pulses, and takeover (D4), the full vibration of a held alarm (D11), and the auto-quit fix (D15).

### D7. Tests

The two failures in the Context are the core of this change, so each one has its own test at each level. Slot 0 "vibrates unseen" and "any other slot does not ring at all" need different tests, because the main window already checks slot 0 but never checks the other slots.

- `test/test_timer_multi.c`: `timer_running_countdown_mask()` (running countdown, paused countdown, overdue countdown, chrono) and `timer_find_ended_countdown()`:
  - none ended returns -1;
  - slot 0 ended returns 0 (not taken as "none");
  - slot 1 ended while slot 0 still runs returns 1;
  - two ended picks the first;
  - ended slots outside the mask are ignored.
- `test/test_main_logic.c`, `main_show_alarm()` with the two starting states:
  - a slot that is already elapsed and vibrating (`timer_data.elapsed` already true): the mode becomes Counting, it keeps vibrating, the guard starts, and `alarm_start` is not logged a second time;
  - a non-zero slot that the main window has never checked (`elapsed` false): the vibration starts, the backlight turns on, and the refresh is rescheduled for that slot.
- `test/test_main_logic.c`: `main_show_alarm()` switches to Counting on the new slot and starts the guard. A press at +100 ms and a release with no press-down are ignored, and a press at +600 ms acts. Use the existing sim helpers (fake AppTimer scheduler, `prv_sim_press`).
- `test/test_timer_multi.c`, the watch mask: `timer_watch_add_running()` only adds running countdowns with time left; a bit stays set after its countdown ends; `timer_watch_clear()`; `timer_slot_delete()` drops the deleted bit and shifts the higher bits (delete below, at, and above a watched slot); `timer_next_watched_end_ms()` returns the soonest end, ignores ended slots, and returns -1 for an empty mask.
- `test/test_timer_multi.c`, D11: an alarm shown 2 min after its end vibrates, and it stops and auto-snoozes 30 s after it was shown, not at once; the offset for one slot does not change another slot.
- `test/test_main_logic.c`, the main-window watch, with the sim helpers (fake AppTimer scheduler, `prv_sim_press`). Slot 0 is active, slot 1 is a countdown:
  - not busy (slot 0 counting down): slot 1 takes over at its end time (within the sim's step), vibrates, and the guard starts; slot 0 keeps running and is then watched;
  - slot 0 alarming: slot 1's end is held (no mode change, no active-slot change, slot 1's `length_ms` unchanged, no watch timer scheduled for it);
  - each exit from "busy" takes over at once: Select, Back, and Down on the alarm; the 30 s vibration ending on its own; an edit that expires; a button that leaves an edit mode;
  - Up on the alarm: the alarm is silenced and the edit screen shows; the held alarm does **not** take over (the mode is still the edit mode and the active slot is unchanged); it takes over when that edit expires;
  - slot 0 in New, EditSec, and EditRepeat: held; when the edit expires to Counting, slot 1 takes over;
  - two held: the first to end opens first, the second stays held until the first is silenced, then opens;
  - a held alarm shown after 45 s vibrates (it does not auto-snooze at once), and its screen shows the real overtime (about 0:45);
  - the Timer List on top: the main watch does nothing, and `prv_app_timer_callback()` does not start slot 0's alarm when slot 0 ends behind the list (no vibration, no `alarm_start`); after `main_show_alarm()` on slot 0, it vibrates.
- `test/test_main_logic.c`, D12 (mock `wakeup_schedule` records the time, cookie, and result; it returns `E_RANGE` for a time within 1 minute of an already scheduled one, including one that the test marks as "another app's"):
  - exit with one held alarm: a primary at +10 s and backups at +130 s and +250 s, all with the held slot as the cookie; the pending mask is saved;
  - exit with two held alarms: the cookie is the one that ended first; both bits are saved;
  - exit with a held alarm and an active countdown ending 30 s later: the primary is the held alarm at +10 s; the active bit is saved; after the relaunch, the countdown is watched and rings at its end;
  - exit with a held alarm and an active countdown that ends 5 s later (before the held time): the primary is the active countdown; the held bit is saved and it takes over after the first alarm;
  - exit with an active countdown only: the primary is its end, the backups 2 min and 4 min later;
  - exit with the active countdown ending in 10 min and a **non-active** countdown ending in 3 min: the primary is the non-active one at 3 min, with its slot as the cookie; both bits are saved; that wakeup launch opens it, and the active one is watched;
  - exit with two non-active countdowns 20 s apart: the primary is the first; after that launch, the second is watched and takes over (or is held) at its end;
  - "another app's" wakeup within 1 minute of the primary: the primary gets `E_RANGE`, and both backups are scheduled;
  - "another app's" wakeups within 1 minute of the primary and the first backup: both get `E_RANGE`, and the second backup is scheduled;
  - a backup wakeup launch 2 min late: it vibrates for its full time and shows about 2:00; a second-backup launch 4 min late shows about 4:00;
  - a second countdown that ended while waiting for a backup: after that launch it is a held alarm and takes over after the first;
  - wakeup launch for a held alarm that ended 45 s ago: it vibrates for its full time and shows about 0:45; the second saved alarm takes over after the first is silenced;
  - user launch before the wakeup: the held alarm is not taken over at launch while the list shows (D13);
  - exit with no pending alarm: no wakeup, the mask is 0.
- Functional: two countdowns about 20 s apart; let the first ring, and let the second end while it rings (held); exit with the system exit (hold Back); expect a `wakeup_launch` about 10 s later with the second timer active, `alarm_start` with `v=1`, and `t` near its real overtime. If the emulator cannot do the system exit, rely on the sim tests.
- `test/test_main_logic.c`, D13 (stub `timer_list_show()` counts calls):
  - user launch with a saved held alarm in slot 1 and a 5 min countdown in slot 0, "Multiple Timers" on: the list shows, no takeover, no vibration, and no guard;
  - "Multiple Timers" off, a saved held alarm on slot 0 that ended 2 min ago: no list, no takeover log; slot 0 vibrates for its full time (it does not auto-snooze at once), shows about 2:00, and a press at +100 ms after `alarm_start` is ignored;
  - "Multiple Timers" off, a leftover held countdown in slot 1 and slot 0 counting down: slot 1 takes over at once (`main_alarm_takeover`).
- `test/test_timer_multi.c`: `timer_ended_mask()` returns only the ended slots of the mask (none, slot 0, slot 1, both; paused and chrono slots are not included).
- `test/test_main_logic.c`, D16 (sim, with the D12 `wakeup_schedule` mock):
  - a takeover (`main_show_alarm()`), then exit 2 s into the vibration with no press: a primary wakeup at +10 s with that slot as the cookie, its bit saved; the wakeup launch vibrates for its full time and shows the real overtime;
  - a wakeup launch for an ended slot, then exit before the first `prv_app_timer_callback`: the bit is saved and a wakeup is scheduled at +10 s;
  - one countdown only, the active timer's own alarm vibrates, exit with no press: a wakeup at +10 s;
  - a takeover, a Back press at +100 ms (ignored by the guard), then exit: a wakeup at +10 s;
  - Select silences the alarm, then exit: no wakeup for that slot, its bit is not saved;
  - the 30 s vibration ends on its own: the bit is cleared, the timer auto-snoozes, and it is watched as a countdown with time left;
  - Select silences slot 0 with slot 1 held: slot 0's bit is cleared and slot 1 takes over in the same `prv_watch_arm()` call; slot 1's bit stays set.
- `test/test_main_logic.c`, D14: slot 0 alarms with slot 1 held; hold Down deletes slot 0, the held timer (now slot 0) takes over, and the window is not popped; with no held alarm, hold Down exits as today.
- `test/test_main_logic.c`, D5 and D15:
  - a 21 min countdown with 45 s left: an edit expires; no quit timer starts; its alarm starts at 45 s; at 60 s the app has not quit and the alarm still vibrates (this fails today);
  - a 25 min countdown with 21 min left: an edit expires, and the quit timer starts (as today);
  - a 25 min countdown with 19 min left: an edit expires, and no quit timer starts;
  - an edit expires on a countdown with over 20 min left (quit timer started); another timer takes over 10 s later; at 60 s the app has not quit;
  - the quit timer fires while an alarm is held: the app does not quit, and the held alarm takes over.
- Functional (`test/functional/test_list_alarm_takeover.py`). The list logs `list_alarm_held,slot=<n>` when it marks a row, `vibe,src=list_alarm` for the five pulses, and `list_alarm_takeover,slot=<n>` when a held alarm takes over. The list's window unload logs `TEST_STATE:timer_list_hide`, so a test can see that the list closed. After each takeover, the test presses Down after the guard window and expects a snooze from the main window (`button_down` with `m=Counting`, `v=0` after), which shows that the alarm screen is on top. Run on basalt and aplite.
  - **Slot 0 ends** (the "vibrates unseen" case): save one ~20 s countdown, exit, reopen so the list shows. Expect `list_alarm_held` with `slot=0` and one `vibe,src=list_alarm` within ~1.5 s of the end time, no `alarm_start`, and no `timer_list_hide`. Take a screenshot and check the alarm icon on the row. Press Back: expect `list_alarm_takeover` with `slot=0`, `timer_list_hide`, and `alarm_start` with `v=1`.
  - **Slot 1 ends, Select on another timer** (the "does not ring" case): save a 5 min countdown in slot 0 and a ~30 s countdown in slot 1. Expect `list_alarm_held` with `slot=1`. Move the selection to the 5 min timer and press Select: expect `list_alarm_takeover` with `slot=1`, `alarm_start` with `v=1`, and `tl` equal to the short timer's length; the 5 min timer is not changed.
  - **Delete shifts the mask**: the same two timers; delete the 5 min one with hold Down. Expect `list_alarm_held` with `slot=0`; Back opens it with the short timer's `tl`.
  - **Deleted countdown**: the same two timers; delete the short one. Expect no `list_alarm_held` and no `vibe,src=list_alarm` within 3 s after its end time.
  - **Overdue and paused at open**: a countdown that ended before the relaunch (its alarm silenced), and a paused countdown. Expect no `list_alarm_held` within 3 s, and Back exits as before.
  - **Idle**: an alarm held in the list; press nothing. Expect `list_alarm_takeover` about 30 s after the last press, and no `timer_list_idle_background`.
  - **Select on New Timer**: an alarm held in the list; select "New Timer", add time, and let the edit expire. Expect no takeover while in New or EditSec, then `main_alarm_takeover` when the edit ends.
  - **Hold Down on New Timer**: an alarm held in the list; hold Down on "New Timer". Expect `list_alarm_takeover`, the app does not exit, and the Down release does not snooze (on aplite too, D6).
  - **Kept stopwatch**: after a Back takeover, silence the alarm, exit, and reopen. Expect one more list row.
  - Before the fix, run the slot 0 and slot 1 tests and record how they fail: slot 0 should log `alarm_start` while the list stays open, and slot 1 should log no `alarm_start` and no `list_alarm_held`. This confirms that the tests catch both failures in the Context.

## Risks / Trade-offs

- [The list signal can come up to 500 ms after the countdown ends] → This is fine for an alarm.
- [The user stays in the list and keeps pressing buttons] → The alarm stays held while the user is active in the list. The row mark and the five pulses tell them it is due. It takes over at most 30 s after the last press (idle), or at Back, Select, or hold Down on "New Timer".
- [The alarm icon costs heap] → Only while a row is marked (D4). Measured on aplite (D6).
- [The press that leaves the list is still down at the takeover (hold Down on "New Timer")] → The input guard drops its release. Aplite has no guard; the press-down was in the list window, so the main window gets only the release (a functional test checks this, D6).
- [Back or idle keeps the implicit stopwatch at a takeover] → This is the same as Back and idle without an alarm today. The user can delete it with hold Down.
- [On aplite, a stray press at the takeover silences, snoozes, or edits the alarm] → Accepted. The screen changed and the watch buzzed, so the alarm is not missed (D6).
- [The aplite heap falls below the safe floor, or aplite faults] → Measure and test on aplite before the change is done (D6). If it does not fit, trim in the D6 order in a follow-up change.
- [Another app's wakeups are within 1 minute of our primary and both backups] → All three fail. The alarm is held and signalled at the next open (D13). Very rare, accepted.
- [A backup rings 2 or 4 min late] → Accepted. Late is better than never, and the screen shows the real overtime.
- [A press within 400 ms of any alarm start is dropped, even one the user meant for the running timer] → Accepted (D17). The user presses again. Existing tests that press soon after an alarm start need a wait past the window.
- [The auto-quit timer now starts less often] → A countdown with 20 min or less left no longer auto-quits after an edit. The app stays open until the user exits. This is a small change in behavior, and it is safe, because the next-event wakeup does not depend on the app being closed.
- [A crash, battery pull, or reboot skips `prv_terminate`] → Nothing is saved or scheduled. No design can fix this.
- [An alarm that the user ignores is shown again after the app closes] → Only when the app closed before the alarm stopped. The alarm rings once more about 10 s later. This is correct for an alarm (D16).
- [Our wakeup fires 10 s after another app opened] → Our app takes the screen from that app. This is correct for an alarm. Test on the watch how the firmware handles a wakeup while another app is open.
- [A held repeating timer] → At the takeover, `timer_check_elapsed()` runs the repeat logic as it does today (one pulse, restart with the overshoot deducted). If it was held for more than one cycle, the schedule can drift. Accepted; repeats are rare with multiple timers.
- [The user stays busy in the main window for a long time] → The alarm stays held with no signal, as the user asked. There is no periodic check, so it costs nothing.

## Migration Plan

None. The saved timer data does not change. One new key (`PERSIST_PENDING_MASK_KEY`) is added; a missing key reads as 0. Kept stopwatches are ordinary slots.

## Open Questions

None.
