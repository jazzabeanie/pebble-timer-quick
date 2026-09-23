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
- Run on aplite with a very small RAM cost.

**Non-Goals:**
- Guarding user launches.
- Guarding the Timer List window. It is not shown on wakeup launches.
- A configurable guard duration.

## Decisions

### D1. Decide per press on raw-down

Keep a small `uint8_t s_blocked_buttons` bitmask (one bit per `ButtonId`), and store `s_wakeup_launch_ms` (0 when this is not a wakeup launch).

- In `prv_initialize`, on a wakeup launch: `s_wakeup_launch_ms = epoch()` and set all bits in `s_blocked_buttons`. This blocks a release that has no matching press-down (an Up, Select, or Down press held from before launch).
- For Up, Select, and Down, the raw-down handler re-evaluates that button's bit: blocked if `s_wakeup_launch_ms != 0 && epoch() - s_wakeup_launch_ms < WAKEUP_INPUT_GUARD_MS`, else clear. When blocked, the raw-down handler returns before its normal work.
- Every other handler for those buttons starts with `if (prv_press_blocked(button)) return;`.
- Back is a special case (D2). Its single-click handler fires on press-down, so it checks the time directly and does not use the bitmask.

The bit is cleared only at the next raw-down, not at raw-up. So the order of raw-up and single-click on release does not matter. The late long press, single press, or multi press of a blocked press still sees the bit set.

*Alternatives:*
- Compare the handler fire time with the launch time. Rejected by the user. A press that starts at 200 ms and is held would fire its long-press action at ~950 ms.
- Swap the click config provider for a "no-op" provider for 300 ms. Rejected. A press that starts in the window and is released after the swap back would still fire.

### D2. Back checks the time in its single-click handler

The SDK does not allow a raw click subscription on Back ("The back button cannot be overridden with a raw click"). It also does not allow a long click on Back. Back has only a single-click subscription, so its handler fires on press-down. The Back single-click handler therefore starts with a time check: if this is a wakeup launch and `epoch() - s_wakeup_launch_ms < WAKEUP_INPUT_GUARD_MS`, it returns. The check happens at press-down, so it has the same meaning as the raw-down check on the other buttons. A Back press held from before launch never fires in the new window, because its down event went to the previous app.

Up and Select already have raw-down handlers, so add the check to them. Down has an empty raw-down handler, so give it the check. The Up raw-up handler still clears `s_up_held`, which does no harm.

*Alternative:* a raw subscription on Back. Rejected. The SDK does not support it.

### D3. Time source and constant

Use `epoch()` (ms), which the app already uses. Add `#define WAKEUP_INPUT_GUARD_MS 300` to `src/main.h`. Set the launch time in `prv_initialize`, before the window is pushed. The window animation is part of the 300 ms, which matches "after the screen first opens".

### D4. Test hooks

- `test/test_main_logic.c`: make the `launch_reason()` stub return a settable variable. Make the stubbed `epoch()` controllable, if it is not already. Then call the raw and click handlers directly.
- Log `TEST_STATE:input_blocked,button=<id>` when a press is dropped, so that the functional tests can assert it.

## Risks / Trade-offs

- [A real "silence" press in the first 300 ms is dropped] → This is the goal. The alarm keeps vibrating, and the user presses again.
- [A future SDK or setup change makes the Back single click fire on release] → Back cannot have a long or multi click, so this cannot happen with the current SDK. A unit test covers the Back check.
- [If a new handler does not call the guard, it can leak a press] → Use one helper, `prv_press_blocked()`. Add a note in the design of `lap-double-press-pause`.
- [A functional test cannot press within 300 ms reliably] → The functional test triggers a real wakeup launch. It checks that a press after the window acts normally and that the launch was detected. The unit tests cover the timing.
- [Aplite RAM] → The cost is about 9 bytes of static data and a few small functions. Check that the aplite heap stays at or above ~1.6 KB.

## Migration Plan

None. The change is only in the firmware app, and it does not change the persisted data.

## Open Questions

- Can the emulator test harness trigger a wakeup launch in a reasonable time (a short countdown, then exit the app, then wait)? If not, drop the functional test and rely on the unit tests.
