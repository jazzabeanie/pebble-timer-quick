## Context

The main time display is rendered in `src/drawing.c` by two parallel functions: `prv_main_text_update_state` (computes per-field bounds / animations) and `prv_render_main_text` (draws the glyphs). Both split the time into a fixed array of `TEXT_FIELD_COUNT` (currently 6) text fields:

| Index | Content        | Example |
|-------|----------------|---------|
| 0     | `-` prefix (edit modes only) | `-` |
| 1     | hours          | `1`     |
| 2     | `:` (only if hours) | `:` |
| 3     | minutes        | `23`    |
| 4     | `:`            | `:`     |
| 5     | seconds        | `45`    |

Each field buffer is `char[4]`. Field widths feed an auto-scaling font sizer (`text_render_get_max_font_size`) so the whole string fills `MAIN_TEXT_BOUNDS`. The seconds value comes from `timer_get_time_parts(&hr, &min, &sec)` in `src/timer.c`, which currently exposes only hr/min/sec — not milliseconds. The underlying value is available at full ms precision via `timer_get_value_ms()`.

Paused vs. running is `timer_is_paused()`; stopwatch vs. countdown is `timer_is_chrono()`.

## Goals / Non-Goals

**Goals:**
- Show `.mmm` after the seconds when a stopwatch is paused and elapsed < 1 hour.
- Reuse the existing field-layout + auto-scaling pipeline so the millisecond text scales and animates like the rest of the display.
- Keep running stopwatch and all countdown displays byte-for-byte unchanged.

**Non-Goals:**
- No millisecond display while running (no design work for a fast-refresh path).
- No change to the header/footer/secondary displays or the timer-list display.
- No new persisted state; ms is derived from existing `timer_get_value_ms()`.

## Decisions

### Decision: Add milliseconds as a new 7th text field rather than appending to the seconds field

Append a dedicated millisecond field (`.mmm`) at index 6 and bump `TEXT_FIELD_COUNT` 6 → 7. The new field is empty (`""`) in every case except the paused-chrono-under-1h case.

- **Why over appending to `buff[5]`:** the seconds buffer is `char[4]` ("45" + NUL) and the per-field bounds/animation arrays are indexed per glyph group. Cramming `.456` into the seconds field would overflow the buffer and make the millisecond text scale/animate as one unit with the seconds, breaking alignment. A separate field flows through the existing loop untouched.
- **Buffer sizing:** the new field needs to hold `.456` (4 chars + NUL = 5), so its buffer must be ≥5. Simplest is to widen the field buffer array from `[4]` to `[8]` (the `.mmm` field is the only one needing >3, and uniform sizing keeps the array declaration simple). `tot_buff[32]` already has headroom.
- **Alternative considered:** a separate, independently-positioned ms text layer. Rejected — duplicates the scaling/animation logic and risks misalignment with the seconds baseline.

### Decision: Expose milliseconds via `timer_get_time_parts`

Extend `timer_get_time_parts` to also return the millisecond component (e.g. add a `uint16_t *ms` out-param, or add a sibling `timer_get_time_parts_ms`). The ms value is `timer_get_value_ms() % MSEC_IN_SEC`. Prefer extending the existing function and updating its one other caller (`src/utility.c`) so all callers stay consistent.

- **Alternative considered:** compute `timer_get_value_ms() % 1000` inline in drawing.c. Rejected — keeps time-part decomposition centralized in `timer.c`.

### Decision: Gating logic lives in drawing.c next to the existing `REDUCE_SCREEN_UPDATES` block

The condition to populate the ms field is: `timer_is_chrono() && timer_is_paused() && hr == 0` (hr derived from the same time-parts call; `hr == 0` is exactly "less than one hour"). This is evaluated in both `prv_main_text_update_state` and `prv_render_main_text` so layout and draw agree. Factor the field-population into a small shared helper to avoid the two copies drifting (they already duplicate the seconds logic today).

## Risks / Trade-offs

- **Two functions duplicate field-building logic** → extracting a shared helper for the ms field (and ideally the existing seconds field) keeps `update_state` and `render` in sync; a divergence would show as layout/draw mismatch.
- **Wider string may shrink font at small sizes** → `.mmm` adds 4 glyphs; the auto-scaler will pick a smaller font when ms is shown. Acceptable since it only happens while paused (static display, user is reading a measured value). Verify legibility on the smallest platform (aplite/diorite) during implementation.
- **`hr == 0` boundary** → "less than one hour" maps cleanly to `hr == 0` from `timer_get_time_parts`; confirm the 59:59.999 → 1:00:00 transition flips formats correctly in a test.
- **REDUCE_SCREEN_UPDATES interaction** → that block degrades the seconds field while running to reduce redraws; since ms is paused-only it sits outside that path, but ensure the ms field is cleared on the running/interaction branches.

## Open Questions

- Separator before ms: spec uses `.` (`1:23.456`). Confirm `.` over a different glyph — assumed `.` for this design.
