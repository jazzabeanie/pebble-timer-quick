## Why

When an alarm fires, a wakeup event launches the app and the timer window opens over whatever the user was doing. A button press already in progress then lands on the new window and can silence, snooze, restart, or exit the alarm before the user has seen it.

## What Changes

- When the app is launched by a **wakeup event** (an alarm), all four buttons are ignored for 250 ms after launch (on every platform except aplite).
- The wakeup time is rounded down to whole seconds, so the app can open up to 1 s before the alarm starts. On a wakeup launch, the 250 ms window therefore **restarts** when the alarm starts (the first alarm after the launch only).
- A press that **starts** inside that window is ignored until it is released. It can never turn into a single, long, multi, or raw-press action, even if its handler would fire after the window.
- A press that was already held down when the app opened is also ignored.
- The alarm keeps vibrating when a press is ignored; the user presses again to act on it.
- Normal (user) launches are not affected.
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
- `wakeup-input-guard`: Ignore button presses that begin within 250 ms of an alarm (wakeup) launch, or of the alarm start that follows that launch.

### Modified Capabilities
<!-- none -->

## Impact

- `src/main.c`: `prv_start_input_guard()` records the time and blocks all buttons; `prv_initialize` calls it on a wakeup launch and sets `s_restart_guard_on_alarm`, and `prv_app_timer_callback` calls it again when the alarm starts; the Up, Select, and Down raw-down handlers decide per press if it is blocked, and their click handlers return early for a blocked press; the Back single-click handler (which fires on press-down, as the SDK allows no raw click on Back) uses the same press-down check (`prv_press_down_blocked`).
- Ships on every platform except aplite. The guard costs about 336 bytes. The aplite heap was already below the ~1.6 KB floor (1365 bytes), so the guard is compiled out there with `WAKEUP_GUARD_FEATURE` (`src/main.h`).
- Tests: `test/test_main_logic.c` stubs `launch_reason()` as always `APP_LAUNCH_SYSTEM`; it must become configurable. The alarm-start restart needs a fake AppTimer scheduler in the unit tests, so that the app's own timers run in simulated time. A functional wakeup test needs a real alarm launch in the emulator.
- Interacts with the separate `lap-double-press-pause` change: whichever lands second must apply the guard to the new Select double-click handler.
