## Why

When a stopwatch is paused, the user is typically reading off a measured time (lap, split, reaction time), where sub-second precision matters. Today the paused stopwatch only shows whole seconds, discarding the millisecond resolution the timer already tracks internally.

## What Changes

- When a stopwatch (chrono mode) is **paused**, the main time display SHALL show milliseconds (e.g. `1:23.456`).
- Milliseconds are shown **only** when the elapsed time is **less than one hour**, to keep the digit count manageable on screen. At one hour or more, the paused stopwatch keeps the existing `H:MM:SS` format.
- Milliseconds are **not** shown while the stopwatch is **running** (the value changes too fast to read and would thrash the display).
- This applies to **stopwatch / chrono mode only**. Countdown timers are unaffected in every state.

## Capabilities

### New Capabilities
- `stopwatch-millisecond-display`: Defines when and how the paused stopwatch shows millisecond precision in the main time display, including the sub-one-hour gate and the running/countdown exclusions.

### Modified Capabilities
<!-- No existing capability spec governs the main time-display format; this is net-new behaviour. -->

## Impact

- **Code**: `src/drawing.c` — main time rendering (`prv_main_text_update_state`, `prv_render_main_text`) and possibly the `TEXT_FIELD_COUNT` field layout; `src/timer.c` / `src/timer.h` — exposing the millisecond component of the elapsed value (e.g. extending `timer_get_time_parts` or a new accessor).
- **Display layout**: Adds up to 4 extra characters (`.456`) to the main text, which the auto-scaling font logic (`text_render_get_max_font_size`) must accommodate.
- **Tests**: New functional tests under `test/functional/` to verify ms shown when paused & <1h, hidden when running, hidden at ≥1h, and absent for countdown timers.
- **Docs**: `docs/button-functions.md` display-format notes may need an update if display behaviour is documented there.
