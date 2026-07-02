## Context

QuickTimer stores up to `MAX_TIMERS` (5) timers in a fixed `Timer
timer_slots[MAX_TIMERS]` array (`src/timer.h`/`timer.c`). The active slot is an
indirection (`timer_data` macro → `timer_slots[s_active_slot]`). All drawing
reads the active slot globally (`src/drawing.c` uses `timer_data` and
`main_get_control_mode()` directly). The Timer List window (`src/timer_list.c`)
already has scroll plumbing (`s_scroll_y`, `prv_update_scroll`,
`s_screen_h`) but a fixed `MAX_TIMERS`-sized `s_sorted` array and no extra rows.

Button handling lives in `src/main.c`. In Counting mode, Select toggles
play/pause (`prv_select_click_handler`). Names are a fixed `char name[20]`
field; `timer_assign_name` builds a mnemonic, `timer_set_name` applies a
user/voice name. Persistence uses `PERSIST_VERSION` (currently 7); a version
mismatch wipes all timers on load. Settings are booleans persisted via
`AppSettings` and mirrored in `src/js/pebble-js-app.js` over AppMessage keys.

This change adds laps, more slots, longer names, list scrolling for the larger
set, a pinned "Delete all" row, and a post-delete selection change.

## Goals / Non-Goals

**Goals:**
- Record a paused copy of a running timer into a new slot on Select, keeping the
  original running and active, gated by a new off-by-default setting.
- Name lap copies `Lap [n]: <name>` with `n` incrementing per originating timer.
- Flash the lap copy vs. the original (0.5 s / 0.5 s) for 3 s, cancelable by a
  re-lap Select.
- Raise the slot limit to a high-but-reasonable value with list scrolling.
- Lengthen the stored name field unconditionally.
- Add a pinned "Delete all" row (hold Down clears all; Select shows a hint).
- After deleting a list entry, select the previous entry.

**Non-Goals:**
- Preserving existing persisted timers across the version bump (the current
  version-mismatch reset behavior is retained).
- A dedicated lap-history UI beyond the lap copies appearing as normal slots.
- Changing lap behavior for paused timers or non-Counting modes.

## Decisions

### Slot count and name length
Raise `MAX_TIMERS` to a higher constant (**32**). The relevant limit is Pebble
**persistent storage: 4096 bytes total per app** (the same on every target,
aplite included), with each `persist_write_data` value capped at
`PERSIST_DATA_MAX_LENGTH` = 256 bytes (also identical on all platforms). Each
slot is persisted as its own key (`timer_persist_store` calls
`persist_write_data(PERSIST_TIMER_SLOT_KEY(i), &timer_slots[i], sizeof(Timer))`),
so the 256-byte per-value cap is never a concern — the enlarged `Timer` struct is
~80 bytes (3×`int64`=24, 9 single-byte fields incl. `lap_count`, `name[40]`,
8-byte aligned).

The constraint is the shared 4096-byte total, which also holds the version key,
count key, and all settings, and carries per-field storage overhead beyond the
raw value bytes. 32 slots is ~2560 bytes of raw slot data; with overhead plus the
settings/version keys it still fits the 4 KB budget with margin, but the exact
maximum is not a clean `4096 / 80` — the true ceiling is somewhat below that and
has not been measured, so 32 is chosen for headroom rather than pushed to a
theoretical limit. RAM is a non-issue: `timer_slots[32]` is ~2560 bytes static,
negligible even on aplite. The practical limit is screen/scroll usability, not
hardware.

Raise `name` from `char[20]` to **`char[40]`** so `Lap [n]: ` (≤ ~9 chars for n
up to 99) plus any default-assigned mnemonic name fits comfortably. A
user-renamed name can occupy the full 40-byte buffer, in which case the
`snprintf`-built lap name trims the end of the original to make room for the
prefix (see the lap-recording section) — the prefix is never dropped. The main
timer page already renders the name on a single line with
`GTextOverflowModeTrailingEllipsis` (`prv_render_name_text`, `src/drawing.c`), so
a name longer than the line width truncates with an ellipsis exactly as today — no
layout breakage. The stored name (up to the buffer) is preserved and used for
laps. The Timer List row drawing uses local
`line1[20]`/`line2[20]` buffers that must be enlarged to display longer names.

Both limits are compile-time constants; `timer_slots` stays a fixed array. Bump
`PERSIST_VERSION` so the enlarged struct and higher count don't read stale data;
on mismatch the existing reset path runs (timers wiped). The persisted
slot-count validation (`count > MAX_TIMERS`) automatically tracks the new
constant.

*Alternative:* dynamic allocation — rejected; fixed array matches existing code
and avoids heap churn.

### Split/total display model (`timer.c`, `drawing.c`)
Conceptually a stopwatch with lapping disabled is identical to a lapping-enabled
stopwatch still on its first lap; only the header differs. Exploit this so the
lapping flag is checked in exactly two places — the Select handler and the header
renderer — and nowhere on the main-value path.

Add one field to `Timer`: `int64_t last_lap_ms` = the cumulative elapsed captured
at the most recent lap (0 = no lap yet). Two quantities derive from it:

- **Total** = the existing `timer_get_value_ms()` (elapsed since first start).
- **Split** = `total − last_lap_ms`. Add `int64_t timer_get_split_ms(void)`
  returning this; with `last_lap_ms == 0` (every stopwatch with no laps, i.e.
  every stopwatch while lapping is off) it equals the total, so the main value is
  unchanged in those cases without any flag test.

`prv_render_main_text` switches from total to `timer_get_split_ms()` for the main
value (identical output until a lap is recorded). `prv_render_header_text` is the
only display that branches on `settings_get_lap_stopwatch_enabled()`: when enabled
and the timer is a chrono, show the **total** prefixed with the count-up arrow
(`-->%02d:%02d` / `-->%02d:%02d:%02d`); otherwise keep the current
`00:00-->`/base-length header. (Note the arrow moves to a prefix in the
lapping-enabled header.) Callers of `timer_get_value_ms()` used for non-display
purposes (footer end-time, vibration threshold) keep using the total.

### Lap recording (`timer.c`)
Add `int8_t timer_slot_lap(uint8_t src_idx)`: allocate the next free slot
(reuse `timer_slot_create` allocation, or a dedicated copy), `memcpy` the source
`Timer`, then convert the copy to a paused snapshot whose **total** equals the
source's current elapsed (`is_paused = true`, `start_ms = <total at snapshot>`),
and set its name to `Lap [n]: <src name>`. Carry the lap boundaries so the copy
displays with the same formula: set `copy.last_lap_ms = src.last_lap_ms` (the
previous lap's cumulative) so the copy's split = its total − its `last_lap_ms` =
this lap's split, and its header shows its total (the cumulative at the lap). Then
update the source: `src.last_lap_ms = <total at snapshot>` so the running split
restarts from this lap, and increment `src.lap_count`.

`n` is derived per originating timer. Because slots are compacted on delete and
copies are independent, the lap number cannot be stored as an index; instead the
per-timer `uint8_t lap_count` on the source `Timer` increments on each lap so
successive laps read 2, 3, …. The prefix is built with `snprintf` into the
enlarged name buffer; if the source name is itself a `Lap [n]: ` name (re-lapping
a lap is out of normal flow) the prefix is still prepended to the source's stored
name.

### Long-press Select restart (`main.c`)
The existing chrono restart on long-press Select keeps the timer's name. When
`settings_get_lap_stopwatch_enabled()`, extend it to also reset the lap session:
zero the total and split (`start_ms`/`last_lap_ms`), reset `lap_count` to 0 so the
next lap is `Lap 1`, and assign a new name (reuse `timer_assign_name`).
Previously recorded lap slots are independent and untouched. With lapping
disabled, the restart path is unchanged (name preserved).

### Select-as-lap in main.c
In `prv_select_click_handler`, before the existing play/pause path: if
`settings_get_lap_stopwatch_enabled()` and `control_mode == ControlModeCounting`
and `!timer_is_paused()` and not handling an alarm, call the lap flow instead of
`timer_toggle_play_pause()`. The active slot is unchanged (original stays
active). Then start/refresh the flash.

Guard against the no-free-slot case: when `timer_slot_lap` returns -1 (all slots
in use), do **not** toggle play/pause or start the flash. Instead warn the user
with an on-screen message plus three short vibration pulses. This reuses the
existing capacity-warning idiom — `prv_show_no_phone_feedback` already pairs a
temporary on-screen indicator with a three-pulse `VibePattern`
(`{100,100,100,100,100}` = on-off-on-off-on = three distinct buzzes,
`vibes_enqueue_custom_pattern`); factor that pattern into a small helper (or add a
sibling `prv_show_no_free_slot_feedback`) so the lap-at-capacity warning shares
the same haptic and a "no free slots" message. The original timer keeps running
with its play/pause state unchanged throughout.

### Flash state machine
Add flash state to `main_data`: the lap slot index to show during "on" frames, a
flash deadline (`epoch() + 3000`), and an `AppTimer` toggling every 500 ms. A
`bool s_flash_showing_lap` flips each tick. Rendering: add a drawing override
`drawing_set_slot_override(int8_t slot)` (−1 = none). During "on" frames the
override is the lap slot and `drawing_render` reads that slot as a paused
Counting timer; during "off" frames the override is cleared so the normal active
timer renders. The override only affects what is drawn — `s_active_slot` and all
button handlers keep operating on the original. On flash expiry, clear override
and timer. A Select press while the flash is active cancels it and immediately
re-laps (records the next lap and restarts the flash).

*Alternative:* temporarily swapping `s_active_slot` during draw — rejected;
risks button handlers racing on a transiently-wrong active slot. A draw-only
override keeps the swap confined to rendering.

### Approaching-limit warning
After any successful timer or lap creation, compute the remaining free slots
(`MAX_TIMERS - timer_count`). When it is ≤ 3 (i.e. the creation left 3, 2, 1, or
0 slots free), emit the same three-pulse `VibePattern` as the capacity/no-phone
warning and show an on-screen message that states how many slots remain (e.g.
"3 slots left"). This check runs on every qualifying creation, so the warning
repeats as the user keeps filling slots; above 3 free it never fires. This is
distinct from the *at-capacity* lap failure (0 free, creation refused), which
keeps its own "no free slots" message.

Presentation differs by path:
- **Normal timer:** reuse the transient-overlay idiom (an AppTimer-driven flag
  like `prv_show_no_phone_feedback`, but held for 3 s) to show the message when
  the timer is first created, then auto-dismiss.
- **Lap:** do not add a separate overlay; fold the message into the existing
  flash state machine. Add a flag (e.g. `s_flash_show_limit_warning`) set when
  the just-recorded lap left ≤ 3 free. In the flash tick, the "off"/original
  phase renders the warning message instead of the original timer, while the
  "on" phase keeps flashing the paused lap slot via the draw override. When the
  3 s flash window ends, clear the flag and the override so only the original
  timer remains. The three vibrations fire once when the lap is recorded.

Both paths share one helper to build the "N slots left" string and enqueue the
three-pulse pattern, so the haptic and wording stay consistent across normal
creation, lap creation, and the at-capacity failure.

### Timer List: Delete all, scrolling, post-delete selection
- Add a synthetic bottom row "Delete all" that is not backed by a slot. Row
  count becomes `implicit + sorted + 1`. `prv_slot_for_row` returns a sentinel
  for the Delete all row; drawing renders the literal label.
- Select handler: on the Delete all row, show a transient hint message (a small
  overlay/state with an AppTimer, mirroring the no-phone feedback pattern) and
  do nothing else. Hold-Down handler: on the Delete all row, delete every slot
  (loop `timer_slot_delete` / reset count to 0) and exit or refresh to empty.
- Scrolling already exists via `s_scroll_y`/`prv_update_scroll`; with the higher
  slot count plus the Delete all row, increase `s_sorted`'s capacity to
  `MAX_TIMERS` (already sized by the constant) and confirm `prv_update_scroll`
  accounts for the extra synthetic row in `s_total_rows`.
- Post-delete selection: in `prv_down_long_click_handler`, after rebuilding the
  list, move `s_selected_row` to the previous timer entry (`r - 1`). If `r - 1`
  is the "New Timer" row (the deleted timer was the topmost), keep the position
  at `r` instead so the next timer shifts up into the selection; if no timers
  remain, select the "New Timer" row (row 0). Concretely:
  `selected = clamp(max(first_real_row, r - 1), first_real_row, last_real_row)`,
  where `first_real_row` is 1 when a New Timer row is present and `last_real_row`
  is `total_rows - 2` (the row just above Delete all); fall back to row 0 when no
  real timers remain. This selects the previous timer on a normal delete, never
  lands on Delete all, and only reaches the New Timer row when the list is empty.

### Settings + JS
Add `lap_stopwatch_enabled` (default false) to `AppSettings`, a new AppMessage
key (`15`), a getter `settings_get_lap_stopwatch_enabled()`, bump
`PERSIST_SETTINGS_VERSION`, and add the toggle row + payload entry in
`pebble-js-app.js`.

## Risks / Trade-offs

- [Enlarged `Timer` struct × higher `MAX_TIMERS` raises persistent-storage and
  RAM use] → Keep `name[40]` and `MAX_TIMERS=32` modest; each slot uses its own
  persist key, well within Pebble limits. Validate the final struct size builds
  on all target platforms (aplite/basalt/chalk/emery).
- [Version bump wipes existing user timers] → Consistent with current upgrade
  behavior; called out in the proposal. No migration is attempted.
- [Flash draw-override could leak if an AppTimer is missed or the window changes]
  → Always clear the override on flash expiry, on re-lap, and on leaving Counting
  mode / window unload.
- [`Lap [n]:` with large `n` plus a long name could still exceed the buffer] →
  building the name with `snprintf` into the `name[40]` buffer trims the END of
  the original name so the `Lap [n]: ` prefix always survives and the result is
  null-terminated within the buffer; `name[40]` covers `n` to 99 with a full name.
- [Per-timer `lap_count` lives on the source slot, so deleting and recreating a
  source resets numbering] → Acceptable; lap numbers are per originating run.

## Migration Plan

1. Bump `PERSIST_VERSION` and `PERSIST_SETTINGS_VERSION`; existing timers reset
   on first launch of the new build (existing behavior).
2. Ship watch + JS together so the new setting key is understood on both sides;
   the JS already retries sends and the watch requests settings on boot.
3. Rollback: reverting the build restores the old constants; persisted data from
   the new version fails the version check and resets cleanly.

## Open Questions

- Final values: `MAX_TIMERS` (32) and `name` length (proposed 40).
  Fits the 4 KB total persist / 256 B per-field budget on all targets (aplite
  included) with headroom; the exact per-app slot ceiling is not `4096 / 80`
  (per-field overhead plus shared settings/version keys lower it) and has not been
  measured, so 32 is a margin-based choice, not the hardware maximum.
- Exact wording and presentation of the "hold Down to clear all" hint message.

Resolved:
- "Delete all" via hold Down deletes every slot and exits the app to the
  watchface (matching delete-to-empty behavior today).
- Post-delete selection moves to the previous timer entry; if the deleted timer
  was the topmost, the position is kept so the next timer shifts up; if no timers
  remain, the New Timer row is selected. The selection never lands on "Delete
  all".
