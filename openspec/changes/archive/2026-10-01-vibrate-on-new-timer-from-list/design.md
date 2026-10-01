## Context

A new timer started from the main window calls `vibes_short_pulse()` in `prv_initialize` (`src/main.c`). A launch into the Timer List creates the implicit new timer without a vibration. This is correct, because the user has not chosen to start a timer yet. When the user presses Select on "New Timer", `prv_select_click_handler` (`src/timer_list.c`) sets the implicit slot active and switches to `ControlModeNew`, but it gives no vibration.

## Goals / Non-Goals

**Goals:**
- One short vibration when "New Timer" is selected from the Timer List.

**Non-Goals:**
- A vibration when the list opens, or when an existing timer is selected.
- Changes to the approaching-limit warning (three short vibrations when the list opens with 3 or fewer free slots).

## Decisions

### D1. Vibrate in the Timer List Select handler

Call `vibes_short_pulse()` in the "New Timer" branch of `prv_select_click_handler` in `src/timer_list.c`, before `window_stack_pop`. This is the only path that starts a new timer from the list, so the vibration stays local to the list code.

*Alternative:* vibrate in the main window when it appears in `ControlModeNew`. Rejected. The main window also appears in other ways, and it would need extra state to know that it came from "New Timer".

### D2. Test marker

`prv_log_list_state("timer_list_select_new")` already logs the selection. The functional test cannot sense a vibration in the emulator. So add a `TEST_STATE:vibe,src=list_new` log next to the call (only in test builds). The functional test then waits for this log. If the unit test stubs have `vibes_short_pulse`, a unit test can count the calls.

## Risks / Trade-offs

- [The limit warning (three vibrations) is still playing when the user presses Select] → `vibes_short_pulse()` can cut off the rest of the pattern. This is acceptable: the user has already seen the warning, and the pulse confirms the new timer.
