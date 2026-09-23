## Why

When the user opens the app just before a countdown ends, the Timer List opens and stays on screen when the alarm is due. The user does not see the alarm screen. Often the alarm does not ring at all. The cause has three parts:

- A user launch cancels all wakeups (`wakeup_cancel_all()` in `prv_initialize`), so the alarm cannot relaunch the app.
- The Timer List redraws its rows, but it never checks for an alarm.
- The main window under the list checks only the active slot. After `timer_persist_read()`, the active slot is slot 0, which is not always the timer that ends.

## What Changes

- While the Timer List is open, the app watches every countdown that was running with time left when the list opened. (The list cannot start or resume a timer, so no other countdown can end while it is open.) When one of them reaches zero, the app opens that timer, as if the user pressed Select on it: it becomes the active slot, the main window goes to Counting mode, and the list closes. The alarm screen shows, and the alarm vibrates.
- Unlike a Select on an existing timer, the implicit "New Timer" slot is **kept** as a running stopwatch (chrono). It is not discarded, and it shows in the list next time.
- When the list closes for an alarm, the input guard from `wakeup-input-guard` starts (`WAKEUP_INPUT_GUARD_MS`, now 500 ms). The user is often pressing buttons in the list at that moment, and such a press must not silence the alarm before the user has seen it.
- A countdown that had already ended before the list opened does not cause a takeover. The list opens as before.
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
- `list-alarm-takeover`: While the Timer List is open, a countdown that reaches zero closes the list and opens that timer's alarm screen, keeps the implicit new timer as a stopwatch, and starts the input guard.

### Modified Capabilities
<!-- none: the Select, Back, idle, and delete behavior of the Timer List does not change -->

## Impact

- `src/timer.c` / `timer.h`: a small pure helper that finds a watched countdown that has ended (unit-testable).
- `src/timer_list.c`: keep a bitmask of watched countdown slots, check it on each 500 ms refresh, keep the mask correct when a slot is deleted, and do the takeover.
- `src/main.c` / `main.h`: a new `main_show_alarm()` API. It sets Counting mode, stops the edit-expire timer, starts the input guard, and checks the alarm at once (the main refresh timer can be up to a minute away).
- Depends on `wakeup-input-guard` (its guard state and helpers in `src/main.c`). Archive that change first.
- Aplite: compiled out with the `WAKEUP_GUARD_FEATURE` switch. The aplite heap is already below the ~1.6 KB floor. Aplite keeps today's behavior.
- Tests: unit tests in `test/test_timer_multi.c` and `test/test_main_logic.c`; a functional test in `test/functional/`.
- Non-goal: alarms for non-active slots while the app is closed. Only the active slot schedules a wakeup in `prv_terminate`. That is a separate issue.
