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
- Change the stopwatch **display** when lapping is enabled: the main value shows
  the current **split** (time since the last lap) and the header shows the
  **total** elapsed since first start, prefixed with the count-up arrow
  (`-->12:34`). Conceptually a lapping stopwatch on its first lap is identical to
  a non-lapping stopwatch except for the header, so the main value is always the
  split (equal to the total until a lap is recorded) and only the Select handler
  and header rendering depend on the setting. A recorded lap slot shows that lap's
  split as its main value and its cumulative time in the header.
- When lapping is enabled, a **long press of Select** restarts the stopwatch from
  the first lap and gives it a new name (previously recorded lap slots are kept);
  with lapping disabled, long-press Select restarts without renaming, as today.
- Increase the maximum number of timer slots from 5 to 32, and add **scrolling**
  support to the Timer List so all slots are reachable. **BREAKING**: persistence
  layout / version changes.
- **Warn as the slot limit is approached:** when creating a timer or lap leaves 3
  or fewer free slots, show an on-screen message (with the number of slots
  remaining) and three short vibrations, repeating for each subsequent creation.
  A normal timer shows the message for 3 seconds on creation; a lap shows it
  during the flash window in place of the original view while the paused lap keeps
  flashing. Attempting to lap with no free slots left instead shows a "no free
  slots" message with three vibrations and records nothing.
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
  the lap naming scheme, the post-lap flash behavior with its re-lap window, the
  in-flash presentation of the approaching-limit warning, the split/total display
  model (main = split, header = total with `-->` prefix), and the
  restart-and-rename long-press Select behavior.

### Modified Capabilities
- `multi-timer-management`: Maximum slot count increased beyond 5; stored timer
  name field lengthened; approaching-limit warning (message + three vibrations)
  when a creation leaves ≤ 3 free slots.
- `timer-list-view`: Adds scrolling for off-screen rows, a pinned "Delete all"
  row with its hold-Down / Select behaviors, and changes post-delete selection
  to favor the previous row.

## Impact

- Source: `src/timer.h`, `src/timer.c` (MAX_TIMERS, name length, persist version,
  `lap_count`/`last_lap_ms` fields, lap copy helper, `timer_get_split_ms`),
  `src/timer_list.c` (scrolling, Delete all row, post-delete selection),
  `src/main.c` (Select-as-lap in Counting mode, flash state machine, long-press
  restart-and-rename), `src/drawing.c` (render an overridden slot during flash,
  split main value, total/`-->`-prefixed header when lapping is enabled),
  `src/settings.c`, `src/settings.h`, `src/js/pebble-js-app.js` (new
  `lap_stopwatch_enabled` setting).
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
