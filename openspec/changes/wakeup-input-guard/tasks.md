## 1. Failing tests

- [ ] 1.1 `test/test_main_logic.c`: make the `launch_reason()` stub return a settable variable; make `epoch()` controllable if it is not already
- [ ] 1.2 Add unit tests: on a wakeup launch, a Select, Back, Up, or Down press-down at +100 ms and its single-click handler has no effect (the alarm keeps vibrating, the app does not pop)
- [ ] 1.3 Add a unit test: a press-down at +200 ms followed by the long-click handler at +950 ms has no effect
- [ ] 1.4 Add a unit test: a single-click handler with no preceding raw-down (press held from before launch) has no effect
- [ ] 1.5 Add unit tests: a press-down at +400 ms acts normally (Down snoozes), and a new press after an ignored press acts normally
- [ ] 1.6 Add a unit test: a user launch (`APP_LAUNCH_SYSTEM`) press at +100 ms acts normally
- [ ] 1.7 Add a functional test (for example `test/functional/test_wakeup_guard.py`), if the emulator can trigger a wakeup launch: start a short countdown, exit, wait for the alarm launch, press after 300 ms, and check that the press acts
- [ ] 1.8 Run the new tests and confirm they fail

## 2. Implementation

- [ ] 2.1 Add `WAKEUP_INPUT_GUARD_MS 300` to `src/main.h`
- [ ] 2.2 Add `s_wakeup_launch_ms`, `s_blocked_buttons`, and `prv_press_blocked(ButtonId)` to `src/main.c`
- [ ] 2.3 In `prv_initialize`, on a wakeup launch, record the launch time and set all bits in `s_blocked_buttons`
- [ ] 2.4 Re-evaluate the button's blocked bit in the Up, Select, and Down raw-down handlers, and return early when the press is blocked
- [ ] 2.5 In the Back single-click handler (it fires on press-down; the SDK allows no raw click on Back), return early if the press is within the guard window
- [ ] 2.6 Add the `prv_press_blocked()` early return to every Up, Select, and Down single, long, and multi click handler, and log `TEST_STATE:input_blocked`
- [ ] 2.7 If `lap-double-press-pause` has already landed, add the guard to `prv_select_double_click_handler`

## 3. Verify

- [ ] 3.1 Re-run the new tests and confirm they pass
- [ ] 3.2 Run all unit tests and the full basalt functional suite (compare to the 141/0 baseline)
- [ ] 3.3 Build for aplite and confirm that the heap stays at or above ~1.6 KB

## 4. Docs

- [ ] 4.1 Update `docs/button-functions.md`: add a section on the wakeup input guard, with its test references
