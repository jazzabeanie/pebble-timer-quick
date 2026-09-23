## Context

On a user launch with saved timers (and "Multiple Timers" on, the default), `prv_initialize` does three things:

1. It calls `wakeup_cancel_all()`.
2. It loads all slots with `timer_persist_read()`, which sets the active slot to 0.
3. It pushes the Timer List on top of the main window.

The list (`src/timer_list.c`) has a 500 ms refresh timer (`REFRESH_MS`) that only redraws. It creates an implicit "New Timer" slot as a running chrono (`timer_slot_create()`: `start_ms = epoch()`, not paused). The main window's `prv_app_timer_callback` runs `timer_check_elapsed()` for the active slot only. The main timer can be up to a minute away, because `REDUCE_SCREEN_UPDATES` sets its interval from the active slot's value.

So a countdown that ends while the list is open either vibrates unseen behind the list (slot 0) or does not ring at all (any other slot).

The wakeup input guard (`wakeup-input-guard` capability) is in `src/main.c`: `s_wakeup_launch_ms` (low 32 bits of `epoch()`), the `s_blocked_buttons` bitmask with the `WAKEUP_GUARD_OPEN` bit, `prv_press_down_blocked()`, and `prv_press_blocked()`. `prv_start_input_guard()` records the time and sets `s_blocked_buttons = 0xFF`. On a wakeup launch, `prv_initialize` calls it and sets `s_restart_guard_on_alarm`, and `prv_app_timer_callback` restarts the guard at the first alarm start. The Timer List shows only on user launches, so that flag is always false while the list is open. The code is compiled out on aplite (`WAKEUP_GUARD_FEATURE`). `WAKEUP_INPUT_GUARD_MS` is 250.

## Goals / Non-Goals

**Goals:**
- A countdown that ends while the Timer List is open closes the list and shows its alarm screen within one refresh (500 ms).
- The implicit new timer is kept as a running stopwatch.
- The input guard protects the alarm at the takeover, as it does on a wakeup launch.
- Keep the detection logic in a pure helper that the unit tests can call.

**Non-Goals:**
- Taking over for countdowns that were already overdue or paused when the list opened.
- Alarms for non-active slots while the app is closed (only the active slot schedules a wakeup in `prv_terminate`).
- Aplite (compiled out, D6).

## Decisions

### D1. Watch a bitmask of countdowns that were running when the list opened

In `prv_window_load`, before the implicit slot is created, the list stores `s_watch_mask = timer_running_countdown_mask()`. Bit *i* is set when slot *i* is running (not paused) and has time left (`length_ms - elapsed > 0`). `MAX_TIMERS` is at most 32, so a `uint32_t` fits. Add a compile-time check for this.

A countdown that is overdue or paused when the list opens is not in the mask, so it can never take over. The list cannot start or resume a timer, so no new countdown can appear while it is open.

*Alternative:* Treat any running countdown that ended in the last *N* ms as "just ended". Rejected. After a delayed refresh it cannot tell "ended just now" from "was overdue at open", and it depends on refresh timing.

### D2. Detect the end in a pure helper in `timer.c`

Add `int8_t timer_find_ended_countdown(uint32_t mask)` to `src/timer.c`. It returns the slot, among the mask's bits, whose countdown has reached zero (`remaining <= 0`) and has the lowest remaining value (the one that ended first), or -1 if none has ended. It reads `timer_slots` and `epoch()` only, so `test/test_timer_multi.c` can test it directly.

The list's `prv_refresh_callback` calls it every 500 ms. That gives a delay of at most one refresh.

*Alternative:* Register an `AppTimer` for the soonest end time. Rejected. The alarm would be more exact, but it needs more code (rescheduling after every delete), and 500 ms is fine for an alarm.

### D3. Keep the mask in step with slot deletes

`timer_slot_delete(i)` moves every slot above *i* down by one. After a delete in the list (hold Down on a timer), the list applies the same move to the mask: it drops bit *i* and shifts the higher bits down by one. Only the list deletes slots while the list is open. "Delete all" and "hold Down on New Timer" close the app, so they need no update.

### D4. Takeover: open the timer, keep the implicit slot

When `timer_find_ended_countdown()` returns a slot:

1. `timer_set_active_slot(slot)`.
2. Leave the implicit slot in `timer_slots`. It is already a running chrono, so it is saved on terminate, like the idle-background path. No index adjustment is needed, because nothing is deleted.
3. Log `TEST_STATE:list_alarm_takeover,slot=<n>`.
4. Call `main_show_alarm()` (D5).
5. `window_stack_pop(true)`. The window unload cancels the list's idle and refresh timers.

*Alternative:* Reuse the Select handler's "existing timer" path. Rejected. That path deletes the implicit slot, and it shifts the selected slot index to match.

### D5. `main_show_alarm()` in `main.c`

Add a new public API that the list calls:

- `main_set_control_mode(ControlModeCounting)` (this also cancels any lap flash), clear `is_reverse_direction`, and stop the edit-expire timer.
- Start the input guard: call the existing `prv_start_input_guard()` directly. Do not set `s_restart_guard_on_alarm` instead: if the slot is slot 0, it can already be vibrating behind the list, so there is no not-elapsed to elapsed change and the restart would never fire.
- `prv_record_interaction()` (screen-on window and fast refresh).
- Cancel `main_data.app_timer` and call `prv_app_timer_callback(NULL)` at once. It runs `timer_check_elapsed()` on the new active slot. That starts the vibration, logs `alarm_start`, turns on the backlight, and reschedules the refresh for the new slot. If slot 0 was already the active slot and its alarm started behind the list, `alarm_start` was logged before the takeover and is not logged again.

A button held in the list at the takeover has no press-down in the main window. The 0xFF mask blocks its release, as it blocks a press held across a wakeup launch.

### D6. Aplite

The takeover depends on the guard, and the aplite heap is already below the ~1.6 KB floor. The new code (the mask, the helper, the refresh check, `main_show_alarm`) is compiled out with `WAKEUP_GUARD_FEATURE`. Aplite keeps today's behavior. The helper in `timer.c` is still compiled for the unit tests, and `--gc-sections` drops it on aplite, because nothing calls it there.

### D7. Tests

- `test/test_timer_multi.c`: `timer_running_countdown_mask()` (running countdown, paused countdown, overdue countdown, chrono) and `timer_find_ended_countdown()` (none ended, one ended, two ended picks the first, bits outside the mask ignored).
- `test/test_main_logic.c`: `main_show_alarm()` switches to Counting on the new slot and starts the guard. A press at +100 ms and a release with no press-down are ignored, and a press at +600 ms acts. Use the existing sim helpers (fake AppTimer scheduler, `prv_sim_press`).
- The list's mask shift on delete: a small static helper `prv_mask_remove_slot()`. It is covered by the functional test for deletes, because `timer_list.c` has no unit test harness.
- Functional (`test/functional/test_list_alarm_takeover.py`): save a ~15 s countdown, exit, reopen (user launch) so the Timer List shows, wait for `list_alarm_takeover` and `alarm_start` (`m=Counting`, `v=1`; accept `alarm_start` before or after the takeover, see D5), then check that the next list shows the kept stopwatch.

## Risks / Trade-offs

- [The takeover can come up to 500 ms after the countdown ends] → This is fine for an alarm. The main window's own check starts the vibration at once.
- [The user is in the middle of an action in the list (for example, holding Down to delete)] → The list closes, and the input guard drops that press. If the long-click fired before the takeover, the delete happens first, and the mask is updated (D3).
- [The kept implicit stopwatch adds a slot the user did not ask for] → This is what the user asked for. The same thing happens on the idle-background path. The user can delete it with hold Down.
- [Slot 0 ends and vibrates behind the list before the list refresh] → The takeover follows within 500 ms, and the alarm is still ringing.
- [Aplite still has the bug] → Accepted to save RAM (D6).

## Migration Plan

None. No persisted data changes. Kept stopwatches are ordinary slots.

## Open Questions

None.
