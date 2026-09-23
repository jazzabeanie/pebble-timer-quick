## 1. Failing tests

- [ ] 1.1 `test/functional/test_timer_list.py`: add a test that Select on "New Timer" logs the new-timer vibration marker
- [ ] 1.2 Add tests that selecting an existing timer, and opening the list with more than 3 free slots, do not log a vibration marker
- [ ] 1.3 Build, run the new tests, and confirm the "New Timer" vibration test fails

## 2. Implementation

- [ ] 2.1 In `src/timer_list.c` `prv_select_click_handler`, "New Timer" branch: call `vibes_short_pulse()` and log `TEST_STATE:vibe,src=list_new`

## 3. Verify

- [ ] 3.1 Re-run the new tests and confirm they pass
- [ ] 3.2 Run the full basalt functional suite (compare to the 141/0 baseline)

## 4. Docs

- [ ] 4.1 Update the Timer List Select row in `docs/button-functions.md` (vibration on "New Timer", with the test reference)
