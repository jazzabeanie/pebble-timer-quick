## Context

`prv_select_click_handler` (`src/main.c`) records a lap when `Lap Stopwatch` is on and the active stopwatch is running in Counting mode. Otherwise Select toggles play/pause or adds time. `prv_click_config_provider` subscribes Select to single, raw, and long (750 ms) clicks. It does not subscribe to multi-click.

On Pebble, if a button has a multi-click subscription, the single-click handler is delayed until the multi-click timeout expires. The raw-down handler still fires immediately. The click config is set per window, but `window_set_click_config_provider` can be called again at runtime to re-subscribe.

The lap feature is inside `LAP_FEATURE` and is compiled out on aplite, where RAM is full.

## Goals / Non-Goals

**Goals:**
- Double-press Select pauses a running lap stopwatch at the first press time.
- No added delay and no merged presses anywhere else (edit modes, countdowns, paused stopwatch, setting off).
- Lap values stay accurate despite the delayed single click.
- The display shows at once that the lap was taken at the press, so the delayed lap flash does not look like a late lap.

**Non-Goals:**
- Changing any other button, or the long-press restart.
- A configurable double-press window.
- Aplite support.

## Decisions

### D1. Use Pebble multi-click, subscribed only while "armed"

"Armed" means: `LAP_FEATURE`, `Lap Stopwatch` on, Counting mode, active timer is a running chrono. A helper `prv_lap_double_press_armed()` computes this. A helper `prv_refresh_click_config()` keeps a cached `select_multi_armed` flag. When the computed state differs from the flag, it calls `window_set_click_config_provider` again. The provider subscribes `window_multi_click_subscribe(BUTTON_ID_SELECT, 2, 2, 300, true, prv_select_double_click_handler)` only when armed.

Call `prv_refresh_click_config()` at the end of `prv_finish_interaction`, from the settings-changed callback, after returning from the Timer List, and after the New-mode expire callback changes the mode. These are all places where the armed state can change.

*Alternatives:*
- Always subscribe multi-click. Rejected. It delays every Select and merges fast taps in edit modes.
- Record the lap at once and undo it on a second press. Rejected by the user. It shows a short lap flash that then goes away, and it needs more code.
- Use Down to pause. Rejected by the user. Select is the preferred gesture.

### D2. Take the press time on raw-down

`prv_select_raw_click_handler` already fires on press-down. It stores `main_data.select_down_ms = epoch()`. The single-click lap path and the double-click pause path both use this stored time. The double-click handler needs the **first** press time. So the raw handler stores the time only when no press is pending: it sets a `select_press_pending` flag, and the click handlers clear it. The pause uses the time from the first press.

### D3. Timer helpers that take a time

- `timer_pause_at(int64_t at_ms)`: pauses the running active timer as if paused at `at_ms` (for chrono: `start_ms = at_ms - start_ms` in the paused encoding).
- `timer_slot_lap_at(uint8_t slot, int64_t at_ms)`: the same as `timer_slot_lap` with the snapshot and `last_lap_ms` taken at `at_ms`. `timer_slot_lap` becomes a wrapper that passes `epoch()`.

Both are unit-testable in `test/test_timer_multi.c`.

### D4. Double-click handler

`prv_select_double_click_handler` does the standard interaction bookkeeping. It calls `prv_flash_cancel()` and then `timer_pause_at(main_data.select_down_ms)`. It then calls `prv_finish_interaction("double_press_select")`. That call disarms the multi-click, because the stopwatch is now paused. It also logs a `TEST_STATE` for the functional tests.

### D5. Freeze the display at press-down

The single click is delayed (D1), so the lap flash starts ~300 ms after the press. To show that the lap was taken at the press, the Select raw-down handler freezes the display when armed. `drawing_set_freeze_ms(int64_t at_ms)` / `drawing_clear_freeze()` add a render-time override, like `prv_apply_slot_override`. While it is set, the draw path evaluates the active timer at `at_ms` instead of `epoch()` (the split main value and the header total) and shows the millisecond field.

The freeze is cleared by the single-click handler (a new lap flash takes over), the double-click handler (the paused value is the same), the long-click handler (restart), the lap-full warning path, a 1 s safety `AppTimer`, and `prv_terminate`. Lap and pause both continue from the frozen value, so the display does not jump. Restart goes to 0:00, as the user expects. The lap-full warning and the safety timeout return to the live running value, which is correct because the stopwatch never stopped.

The freeze takes priority over the lap flash. On press-down during a flash, the raw-down handler stops the flash timer and clears the flash slot override, so the frozen frame shows the running stopwatch, not the lap slot. A single press then starts a new flash for the new lap (as today). A double or long press leaves the flash cancelled. When the lap-full warning or the safety timeout ends the freeze, the old flash does not continue.

*Alternatives:*
- Pause the timer for a short time on press-down. Rejected. It changes real timer state that the single-press path must then undo.
- A haptic tick on press-down. Rejected by the user.

## Risks / Trade-offs

- [The lap flash starts ~300 ms later than today] → The lap value is taken at press-down (D2), and the display freezes at the press (D5), so the user sees the correct value at once. This is documented in `button-functions.md`.
- [A second press just after resume counts as a single press] → This is what the spec requires. The stopwatch is running, so that press will record a lap. It will not pause again.
- [The freeze stays on screen if no handler resolves the press] → A 1 s safety timer clears it; `prv_terminate` clears it too.
- [Re-setting the click config during a handler may reset the click recognizers] → The config is only re-applied after the handler has done its work. Verify on the emulator that the recognizers work after arm and disarm.
- [Existing functional lap tests expect the lap log right after Select] → Wait for the `lap_recorded` state, which some tests already do. Adjust the others.
- [The double-click handler is not covered by the wakeup guard] → The `wakeup-input-guard` change must add its guard to this handler. The change that lands second does this.

## Migration Plan

None. The change is only in the firmware app, and it does not change the persisted data.

## Open Questions

- Is the Pebble default 300 ms multi-click timeout comfortable on real hardware? It can be tuned after testing.
