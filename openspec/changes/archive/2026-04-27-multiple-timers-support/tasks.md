## 1. Settings

- [x] 1.1 Add `multiple_timers_enabled` bool field to `AppSettings` struct in `settings.c` / `settings.h`
- [x] 1.2 Set default value of `multiple_timers_enabled = true` in `settings_init`
- [x] 1.3 Add `settings_get_multiple_timers_enabled()` accessor function in `settings.h` / `settings.c`
- [x] 1.4 Handle the new `APPMSG_KEY_MULTIPLE_TIMERS_ENABLED` key in the settings message handler
- [x] 1.5 Add the "Multiple Timers" toggle entry to the Clay / JS settings page

## 2. Multi-Timer Data Layer

- [x] 2.1 Define `MAX_TIMERS = 5` constant and `PERSIST_TIMER_COUNT_KEY` / `PERSIST_TIMER_SLOT_KEY(n)` macros in `timer.c`
- [x] 2.2 Replace single `Timer timer_data` global with `Timer timer_slots[MAX_TIMERS]` and `uint8_t timer_count` in `timer.c`
- [x] 2.3 Update `timer_persist_store()` to write each slot to its own key plus the count key
- [x] 2.4 Update `timer_persist_read()` to read the multi-slot count and all slot data; start fresh if no valid multi-timer data exists
- [x] 2.5 Add `timer_slot_create()` — allocates next free slot, starts it as a running stopwatch, returns slot index (or -1 if full)
- [x] 2.6 Add `timer_slot_delete(uint8_t index)` — removes slot at index, compacts array, decrements count, clears freed persist key
- [x] 2.7 Add `timer_get_sorted_slots(uint8_t *out_indices, uint8_t *out_count)` — fills `out_indices` with slot indices sorted by expiry (countdown timers soonest first, then stopwatches longest-elapsed first)
- [x] 2.8 Update all existing `timer_data.*` references in `main.c`, `drawing.c`, `timer.c` to use a `timer_get_active_slot()` indirection (the "currently open" slot index)
- [x] 2.9 Add `timer_set_active_slot(uint8_t index)` and `timer_get_active_slot()` helpers so the main window always operates on one slot at a time

## 3. Tests: Multi-Timer Data Layer

- [x] 3.1 Write failing unit tests for `timer_slot_create` (success case, at-capacity case)
- [x] 3.2 Write failing unit tests for `timer_slot_delete` (slot compaction, persist key cleared)
- [x] 3.3 Write failing unit tests for `timer_get_sorted_slots` ordering (countdown before stopwatch, soonest first)
- [x] 3.5 Run tests, confirm they fail, then verify they pass after task 2 is complete

## 4. Timer List Window

- [x] 4.1 Create `src/timer_list.c` and `src/timer_list.h` — new source files for the Timer List window
- [x] 4.2 Implement `timer_list_window_create()` that builds a `Window` with a custom `Layer` for the list
- [x] 4.3 Implement the list draw callback: render "New Timer" row at top, then each sorted existing timer with two-line format (total / remaining for countdown; `HH:MM:SS -->` / elapsed for stopwatch)
- [x] 4.4 Implement Up/Down click handlers to move the selection index, with boundary clamping
- [x] 4.5 Implement Select click handler: if "New Timer" selected → save implicit slot, set it as active, push main window in `ControlModeNew`; if existing timer → free implicit slot, set selected slot as active, push main window in `ControlModeCounting`
- [x] 4.6 Implement Hold Down click handler on the list: if existing timer selected → call `timer_slot_delete`, refresh list; if "New Timer" selected → no-op
- [x] 4.7 Implement 30-second idle `AppTimer` within the Timer List window; on fire → save implicit slot to persist, call `window_stack_pop_all`
- [x] 4.8 Reset the 30-second idle timer on any button press within the Timer List window
- [x] 4.9 On Timer List window load, call `timer_slot_create()` for the implicit new timer (unless 5 slots already in use); store its index for tracking

## 5. Tests: Timer List Window

- [x] 5.1 Write failing functional tests: open app with existing timer → Timer List shown
- [x] 5.2 Write failing functional tests: select existing timer from list → opens normal view, implicit timer discarded
- [x] 5.3 Write failing functional tests: select "New Timer" → opens edit mode
- [x] 5.4 Write failing functional tests: hold Down on existing entry → timer deleted, list refreshes
- [x] 5.5 Write failing functional tests: 30s idle → app backgrounds, implicit timer persisted
- [x] 5.6 Run tests, confirm they fail, then verify they pass after task 4 is complete

## 6. App-Open Routing

- [x] 6.1 In `main.c` app-open logic (after `timer_persist_read`): check `settings_get_multiple_timers_enabled()` AND `timer_count > 0`; if true, push Timer List window instead of entering `ControlModeNew`/`ControlModeCounting` directly

## 7. Hold Down Delete in Main Timer Window

- [x] 7.1 In `prv_down_long_click_handler` in `main.c`: call `timer_slot_delete(active_slot)` then exit the app (same as current quit path); no context flag needed since Back always exits
- [x] 7.2 Write failing test: hold Down inside open timer → only that timer deleted, app exits; other timers remain persisted
- [x] 7.3 Run tests, confirm they fail, verify they pass

## 8. Update `button-functions.md`

- [x] 8.1 Document new Timer List control mode button functions in `docs/button-functions.md` (Up/Down scroll, Select open, Hold Down delete, auto-background, Back exits app)
- [x] 8.2 Document the updated Hold Down behaviour in the existing `ControlModeCounting` section (deletes only this timer and exits; Back also exits)
