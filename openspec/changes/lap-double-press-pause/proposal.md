## Why

With `Lap Stopwatch` enabled, Select on a running stopwatch records a lap instead of pausing, so there is no way to pause a lapping stopwatch. Users need a pause gesture that does not give up the one-press lap.

## What Changes

- Double-pressing Select on a **running stopwatch** with `Lap Stopwatch` enabled pauses it. The pause takes effect at the time of the **first** press, and no lap is recorded for either press.
- The double-press is only recognised ("armed") while a running lap stopwatch is shown in Counting mode. In every other mode and state, Select keeps its current single-click behavior with no added delay, so fast Select taps in edit modes still count individually.
- While armed, a single Select is confirmed only after the double-press window (~300 ms) expires, so the lap flash appears ~0.3 s later than today. The lap value is taken at the moment the button went down, so recorded lap values stay accurate.
- While armed, pressing Select down **freezes the timer display** (split with milliseconds, and the total in the header) at the press-down value. The freeze ends when the press resolves: the lap flash (single press), the pause (double press), or the restart (long press). It also ends when the lap-full warning shows, or after a ~1 s safety timeout. Lap and pause both show this same value, so the display never jumps, and the user sees at once that the lap was taken at the press. There is no haptic feedback.
- A paused lap stopwatch still resumes with a single Select press (unchanged, and not delayed because the double-press is not armed while paused).
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `stopwatch-laps`: Adds double-press Select to pause a running lap stopwatch; the lap snapshot value is taken at Select press-down time; the display freezes at Select press-down while armed.

## Impact

- `src/main.c`: Select click configuration becomes state-dependent (multi-click subscribed only while armed, re-applied when the armed state changes); Select raw-down handler records the press time; new double-click handler; lap recording uses the press time.
- `src/drawing.c` / `drawing.h`: a render-time freeze override, like the existing slot override.
- `src/timer.c` / `timer.h`: helpers to pause the active timer and to snapshot a lap at a given epoch time.
- Aplite: all new code is inside `LAP_FEATURE` and compiled out.
- Tests: new unit tests in `test/test_main_logic.c` and `test/test_timer_multi.c`; the unit-test stubs need `window_multi_click_subscribe`. New functional tests in `test/functional/test_stopwatch_laps.py`. Existing lap functional tests may need to wait for the delayed single click.
- Interacts with the separate `wakeup-input-guard` change: whichever lands second must apply the guard to the new double-click handler.
