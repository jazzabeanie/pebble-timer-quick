## Context

`prv_initialize` (`src/main.c`) already detects `launch_reason() == APP_LAUNCH_WAKEUP`. It restores the alarming slot and skips the Timer List. The app cancels all wakeups on launch and schedules one only in `prv_terminate`. So a wakeup always launches a fresh app process. It never arrives while the app is running.

Button handling in `prv_click_config_provider`:
- Back: single.
- Up: single, raw (sets `s_up_held`), long.
- Select: single, raw (silences the alarm and starts the reset animation), long.
- Down: single, raw (empty), long.

The SDK does not allow raw or long click subscriptions on Back. If a button has no long or multi click subscription, its single-click handler fires on press-down. Back therefore always fires its single click on press-down. Up, Select, and Down have long clicks, so their single clicks fire on release. Long-click handlers fire after 750 ms (`BUTTON_HOLD_RESET_MS`). Raw-down fires on press. On Pebble, the order of the raw-up handler and the single-click handler on release is not guaranteed.

## Goals / Non-Goals

**Goals:**
- Ignore every press whose press-down is within 300 ms of a wakeup launch, until it is released.
- Ignore a press that was held down before launch.
- Cover every handler type, including any that other changes add later (for example the Select double-click from `lap-double-press-pause`).
- Keep the RAM cost small. Compile the guard out on aplite (D5).

**Non-Goals:**
- Guarding user launches.
- Guarding the Timer List window. It is not shown on wakeup launches.
- A configurable guard duration.

## Decisions

### D1. Decide per press on raw-down

Keep a small `uint8_t s_blocked_buttons` bitmask (one bit per `ButtonId`), and store `uint32_t s_wakeup_launch_ms` (the low 32 bits of `epoch()` at launch, see D3). Bit 7 of the bitmask, `WAKEUP_GUARD_OPEN` (0x80), means that the guard window may still be open.

- In `prv_initialize`: record `s_wakeup_launch_ms = (uint32_t)epoch()`. On a wakeup launch set `s_blocked_buttons = 0xFF` (all button bits and the OPEN bit), otherwise 0. The button bits block a release that has no matching press-down (an Up, Select, or Down press held from before launch).
- On press-down, `prv_press_down_blocked(button)` re-evaluates that button's bit. The press is blocked if the OPEN bit is set and `(uint32_t)epoch() - s_wakeup_launch_ms < WAKEUP_INPUT_GUARD_MS`. Otherwise the button's bit and the OPEN bit are cleared. The Up, Select, and Down raw-down handlers call it and return before their normal work when the press is blocked.
- Every other handler for those buttons starts with `if (prv_press_blocked(button)) return;`, which only reads the bit.
- Back calls `prv_press_down_blocked()` in its single-click handler (D2).

The bit is cleared only at the next raw-down, not at raw-up. So the order of raw-up and single-click on release does not matter. The late long press, single press, or multi press of a blocked press still sees the bit set.

*Alternatives:*
- Compare the handler fire time with the launch time. Rejected by the user. A press that starts at 200 ms and is held would fire its long-press action at ~950 ms.
- Swap the click config provider for a "no-op" provider for 300 ms. Rejected. A press that starts in the window and is released after the swap back would still fire.

### D2. Back makes the press-down check in its single-click handler

The SDK does not allow a raw click subscription on Back ("The back button cannot be overridden with a raw click"). It also does not allow a long click on Back. Back has only a single-click subscription, so its handler fires on press-down. The Back single-click handler therefore starts with `if (prv_press_down_blocked(BUTTON_ID_BACK)) return;`. The check happens at press-down, so it is the same check that the raw-down handlers make on the other buttons. A Back press held from before launch never fires in the new window, because its down event went to the previous app.

Up and Select already have raw-down handlers, so add the check to them. Down has an empty raw-down handler, so give it the check. The Up raw-up handler still clears `s_up_held`, which does no harm.

*Alternative:* a raw subscription on Back. Rejected. The SDK does not support it.

### D3. Time source and constant

Use `epoch()` (ms), which the app already uses, but store and compare only its low 32 bits. 32-bit math is smaller than 64-bit math on the watch's ARM chip. Unsigned 32-bit subtraction stays correct when the low bits wrap. The OPEN bit is cleared at the first press-down after the window, so a wrap about 49 days later cannot open the window again. Add `#define WAKEUP_INPUT_GUARD_MS 300` to `src/main.h`. Set the launch time in `prv_initialize`, before the window is pushed. The window animation is part of the 300 ms, which matches "after the screen first opens".

### D4. Test hooks

- `test/test_main_logic.c`: make the `launch_reason()` stub return a settable variable. Make the stubbed `epoch()` controllable, if it is not already. Then call the raw and click handlers directly.
- Log `TEST_STATE:input_blocked` when a press is dropped, and `TEST_STATE:wakeup_launch` on a wakeup launch, so that the functional tests can assert them. Both use `test_log_state()`: they carry the standard state fields but no button ID or `guard_ms` field. This reuses the shared format string and saves RAM.

### D5. Compile the guard out on aplite

Add `WAKEUP_GUARD_FEATURE` to `src/main.h`: 1 on every platform, 0 on aplite, the same pattern as `LAP_FEATURE`. The measured cost was 448 bytes at first and 336 bytes after the trims in D3 and D4. The aplite heap was already 1365 bytes before this change, below the ~1.6 KB floor, and the guard would take it to about 1029 bytes. On aplite, `prv_press_blocked()` and `prv_press_down_blocked()` become macros that return `false`, and the aplite build has the same sizes as the baseline.

*Alternatives:*
- Keep the guard on aplite. Rejected. The saved project notes put a text-rendering crash risk below about 1.4 KB of free heap.
- Find RAM elsewhere to make room. Rejected for this change. It is separate work, and it was already needed before this change.

## Risks / Trade-offs

- [A real "silence" press in the first 300 ms is dropped] → This is the goal. The alarm keeps vibrating, and the user presses again.
- [A future SDK or setup change makes the Back single click fire on release] → Back cannot have a long or multi click, so this cannot happen with the current SDK. A unit test covers the Back check.
- [If a new handler does not call the guard, it can leak a press] → Use one helper, `prv_press_blocked()`. Add a note in the design of `lap-double-press-pause`.
- [A functional test cannot press within 300 ms reliably] → The functional test triggers a real wakeup launch. It checks that a press after the window acts normally and that the launch was detected. The unit tests cover the timing.
- [No guard on aplite] → A press in progress can still act on an aplite alarm launch. Accepted to save RAM (D5).
- [The guard costs about 336 bytes on the other platforms] → Those platforms have ample heap (about 35 KB free on basalt).
- [The wakeup time is rounded down to whole seconds] → The app can open up to 1 s before the alarm vibrates. The guard still covers a press in progress when the screen opens.

## Migration Plan

None. The change is only in the firmware app, and it does not change the persisted data.

## Open Questions

None. Resolved: the emulator can trigger a real wakeup launch. `test/functional/test_wakeup_guard.py` starts a 10 s countdown, exits with Back, and sees the relaunch in about 40 s.
