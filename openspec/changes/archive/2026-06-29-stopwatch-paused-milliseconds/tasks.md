## 1. Tests first

Hybrid strategy: exact-format scenarios that the emulator cannot reproduce (≥1h chrono, exact ms values) are deterministic **unit tests** in `test/test_drawing.c` (which mocks the timer); real end-to-end visibility is verified with **functional tests** on the basalt emulator via a logged display string.

- [x] 1.1 Unit test (`test/test_drawing.c`): paused chrono at 0:01:23.456 renders main text `1:23.456`; paused chrono at 0:00:05.007 renders millisecond field `.007` (zero-padded). SHALL fail before implementation.
- [x] 1.2 Unit test (`test/test_drawing.c`): paused chrono at ≥ 1h (e.g. 1:02:03) renders `1:02:03` with no millisecond field. Asserts absence of ms, so it SHALL pass already.
- [x] 1.3 Functional test (basalt): paused stopwatch < 1h logs a display string containing a `.ddd` millisecond group. SHALL fail before implementation.
- [x] 1.4 Functional test (basalt): running stopwatch logs no `.ddd` millisecond group. Asserts absence of ms, so it SHALL pass already.
- [x] 1.5 Functional test (basalt): paused countdown timer logs no `.ddd` millisecond group. Asserts absence of ms, so it SHALL pass already.
- [x] 1.6 Functional test (basalt): running countdown timer logs no `.ddd` millisecond group. Asserts absence of ms, so it SHALL pass already.
- [x] 1.7 Run the tests (unit: `cd test && make test_drawing`; functional: build then `cd test/functional && python -m pytest -v --platform=basalt`) and confirm 1.1/1.3 fail while 1.2/1.4/1.5/1.6 already pass

## 2. Expose millisecond time part

- [x] 2.1 Add a sibling accessor `timer_get_ms_part()` in `src/timer.c` / `src/timer.h` returning `timer_get_value_ms() % MSEC_IN_SEC` (lower blast radius than changing the shared `timer_get_time_parts` signature, which has 5+ call sites)

## 3. Render milliseconds in the main display

- [x] 3.1 Bump `TEXT_FIELD_COUNT` 6 → 7 in `src/drawing.c` and widen the per-field buffer from `char[4]` to `char[8]`
- [x] 3.2 Add a shared helper that populates the new millisecond field: non-empty (`.mmm`) only when `timer_is_chrono() && timer_is_paused() && hr == 0`, empty otherwise
- [x] 3.3 Call the helper from both `prv_main_text_update_state` (layout/bounds) and `prv_render_main_text` (draw), include the ms field in the `tot_buff` concatenation, and force full `%02d` seconds (bypass the `REDUCE_SCREEN_UPDATES` degradation) whenever the ms field is shown
- [x] 3.4 Ensure the ms field is empty on the running / interaction / `REDUCE_SCREEN_UPDATES` branches so it never appears while running
- [x] 3.5 Add `show_ms` to `DrawState` (set in `prv_draw_state_create`, compared in `prv_text_state_compare`) so pausing/unpausing a sub-1h chrono triggers a layout refresh — otherwise the field bounds are not recomputed when the ms field appears

## 4. Test instrumentation

- [x] 4.1 Emit the rendered main-text string for functional assertions as `TEST_STATE:display,disp=<string>` (throttled to log only when the string changes) from `src/drawing.c`, reusing the existing `LogCapture` state-parsing path in `test/functional/conftest.py`

## 5. Verify and document

- [x] 5.1 Build and re-run unit + functional tests; confirm 1.1/1.3 now pass (and 1.2/1.4/1.5/1.6 still pass) and no other tests regress
- [x] 5.2 Fix the stale `test/test_drawing.c` build (missing `GColorLightGray`, `RESOURCE_ID_IMAGE_ICON_EDIT_MIN`, `RESOURCE_ID_IMAGE_ICON_EDIT_SEC` defines) so the unit suite compiles
- [x] 5.3 Sanity-check legibility of the longer string and confirm the 59:59.999 → 1:00:00 format flip
- [x] 5.4 Update `docs/button-functions.md` display-format notes if the main display format is documented there
