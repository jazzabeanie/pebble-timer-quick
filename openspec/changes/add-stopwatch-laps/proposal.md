## Why

Stopwatch users frequently want to record split/lap times without stopping the
running clock — today the app can only pause or reset, losing intermediate
times. Adding a lap feature lets users capture a snapshot of a running timer
into its own slot while the original keeps running, which also exposes the need
for more timer slots, longer names, list scrolling, and a fast "clear
everything" affordance.

## What Changes

- Add a **Lap** capability (off by default, toggled by a new `Lap Stopwatch`
  setting). When enabled, pressing **Select** on a running timer in Counting
  mode pauses a copy of that timer into a new slot, named `Lap [n]: <name>`,
  while the original timer keeps running and remains the active/on-screen timer.
- After a lap is recorded the paused lap copy **flashes** on screen (0.5 s
  showing the lap, 0.5 s showing the original) for 3 seconds, then only the
  original is shown. Pressing **Select** again during the flash window cancels
  the flash and immediately records another lap (incrementing `n`).
- Increase the maximum number of timer slots from 5 to a higher reasonable
  limit, and add **scrolling** support to the Timer List so all slots are
  reachable. **BREAKING**: persistence layout / version changes.
- Increase the stored timer **name length** (applies regardless of whether the
  lap feature is enabled). **BREAKING**: persisted `Timer` struct grows.
- A lap timer is a normal timer once recorded: re-opening and renaming it
  replaces the entire name including the `Lap [n]: ` prefix.
- Add a **"Delete all"** entry pinned to the very bottom of the Timer List
  (shown regardless of the lap setting). Holding **Down** on it removes every
  timer; pressing **Select** on it briefly shows a message instructing the user
  to hold Down to clear all timers.
- Change Timer List deletion behavior so that after deleting an entry the
  **previous** timer is selected (the entry above), instead of the one below. If
  the deleted timer was the topmost, the position is kept so the next timer shifts
  up; if no timers remain, the "New Timer" row is selected. The selection never
  lands on "Delete all", so users never reach it without navigating there.

## Capabilities

### New Capabilities
- `stopwatch-laps`: Recording lap snapshots of a running timer into new slots,
  the lap naming scheme, and the post-lap flash behavior with its re-lap window.

### Modified Capabilities
- `multi-timer-management`: Maximum slot count increased beyond 5; stored timer
  name field lengthened.
- `timer-list-view`: Adds scrolling for off-screen rows, a pinned "Delete all"
  row with its hold-Down / Select behaviors, and changes post-delete selection
  to favor the previous row.

## Impact

- Source: `src/timer.h`, `src/timer.c` (MAX_TIMERS, name length, persist version,
  lap copy helper), `src/timer_list.c` (scrolling, Delete all row, post-delete
  selection), `src/main.c` (Select-as-lap in Counting mode, flash state machine),
  `src/drawing.c` (render an overridden slot during flash), `src/settings.c`,
  `src/settings.h`, `src/js/pebble-js-app.js` (new `lap_stopwatch_enabled`
  setting).
- Persistence: `PERSIST_VERSION` bump for the enlarged `Timer` struct and higher
  slot count; settings version bump for the new toggle. Existing timers are
  discarded on upgrade per the current version-mismatch reset behavior.
- Docs: `docs/button-functions.md` updated for the new Select-lap action, the
  flash window, the Delete all row, and the changed post-delete selection.
  `README.md` gains a warning that updating to this version erases previously
  saved timers (persisted data reset by the `PERSIST_VERSION` bump).
- Tests: new unit tests (`test/test_timer*.c`) for lap copy/naming and
  functional tests (`test/functional/`) for the flash, Delete all, scrolling,
  and post-delete selection.
