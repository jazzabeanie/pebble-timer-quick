## Why

The watch gives one short vibration when a new timer starts after a button press, which confirms that the new timer is running. When the app opens in the Timer List there is correctly no vibration, but pressing Select on the "New Timer" entry also gives no vibration, so this one way of starting a new timer has no confirmation.

## What Changes

- Pressing Select on the "New Timer" entry in the Timer List gives one short vibration (`vibes_short_pulse()`), the same as other new-timer starts.
- Opening the app into the Timer List stays silent (unchanged).
- Selecting an existing timer from the list stays silent (unchanged).
- `docs/button-functions.md` is updated.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `timer-list-view`: Select on the "New Timer" entry also gives one short vibration.

## Impact

- `src/timer_list.c`: one `vibes_short_pulse()` call in the "New Timer" branch of `prv_select_click_handler`, and a TEST_STATE marker if the tests need one.
- Tests: the functional tests in `test/functional/test_timer_list.py` (and the unit tests, if the timer list is covered there).
- All platforms, aplite included. There is no RAM cost.
