## Why

The app currently supports only a single active timer or stopwatch at a time. Users who need to track multiple concurrent durations (e.g., cooking multiple dishes, interval training, managing parallel tasks) must rely on a single timer and lose context when switching. Adding multi-timer support directly addresses this gap without changing the existing single-timer experience.

## What Changes

- Add a **"Multiple Timers"** toggle to the settings page (enabled by default).
- When enabled and an existing timer is already running, opening the app shows a **Timer List** page instead of jumping directly into the active timer.
- The Timer List displays up to **5 concurrent timers/stopwatches**, sorted by next approaching expiry (soonest first), with a "New Timer" entry highlighted at the top.
- Each timer entry shows: total set time on one line, time remaining on the next line. Stopwatches show the start time with `-->` and elapsed time beneath.
- Pressing Select on an existing timer opens it in the normal running view.
- Pressing Select on the "New Timer" entry opens it in edit mode.
- The newly created timer (highlighted on open) auto-counts as a stopwatch; if no button is pressed for 30 seconds the app goes to background and **saves** that stopwatch.
- If the user navigates to and selects an existing timer instead, the new timer is **not saved**.
- Hold Down on the Timer List deletes the selected existing timer (does not affect others).
- Hold Down while inside an open timer deletes only that timer (and quits the app/goes to background).
- When the timer count reaches the 5-timer limit, no new timer can be created until one is deleted.

## Capabilities

### New Capabilities

- `timer-list-view`: The Timer List UI page — display format, entry layout (timers vs stopwatches), scrolling navigation, select/delete interactions, auto-background-on-idle (30s), and save/discard logic for the implicit new timer.
- `multi-timer-management`: Data layer for storing and managing up to 5 concurrent Timer instances — creation, deletion, persistence across app launches, ordering by expiry, and enforcement of the 5-timer cap.

### Modified Capabilities

<!-- No existing spec-level requirements are changing; this is additive. -->

## Impact

- `src/settings.c` / `src/settings.h` — new `multiple_timers_enabled` field in `AppSettings`.
- `src/timer.c` / `src/timer.h` — extend from a single `timer_data` global to an array/list of timers; update persist read/write to handle multiple entries.
- `src/main.c` — app-open logic: check settings + existing timer count to decide whether to show Timer List or jump straight into the timer.
- New source files likely needed for the Timer List window/layer.
- Pebble persistent storage key usage will increase (one slot per timer).
- No breaking changes to existing single-timer behaviour when the setting is disabled or no prior timers exist.
