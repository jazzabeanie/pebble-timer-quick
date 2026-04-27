## Context

QuickTimer currently manages a single `Timer` struct (global `timer_data`) backed by one persistent storage slot. The app opens directly into that timer's running view. All control modes (`ControlModeNew`, `ControlModeCounting`, etc.) live in `main.c` as state on a single `Window`.

Adding multi-timer support requires:
- A way to store and manage up to 5 `Timer` instances.
- A new UI entry point (Timer List window) shown when the app opens with existing timers.
- Revised app-open, persistence, and button-handler logic.

Constraints: Pebble SDK (C), persistent storage (256-byte value limit per key, ~4 KB total), single-threaded event loop, no heap-heavy allocations.

## Goals / Non-Goals

**Goals:**
- Allow up to 5 concurrent countdown timers / stopwatches.
- New `multiple_timers_enabled` setting (default on).
- Timer List window: entry-point when ≥1 existing timer exists and setting is on.
- Auto-background after 30 s idle on the Timer List, saving only the implicit new stopwatch.
- Delete a timer from the list (hold Down) or from inside an open timer (hold Down).
- Existing single-timer behaviour unchanged when setting is off or no prior timers exist.

**Non-Goals:**
- Simultaneous alarm handling across multiple expired timers (timers still alarm independently when the app is open to that timer).
- Reordering timers manually.
- Syncing timer state with a phone companion app.

## Decisions

### 1. Timer data: fixed array, indexed persistence

**Decision**: Replace the single `timer_data` global with `Timer timer_slots[MAX_TIMERS]` (where `MAX_TIMERS = 5`) and a `uint8_t timer_count`. Each slot persists at its own key: `PERSIST_TIMER_KEY + slot_index` (slots 0–4). A separate key stores the count.

**Alternatives considered**:
- Store all timers in one blob: hits the 256-byte `persist_write_data` limit once `Timer` grows (currently ~50 bytes × 5 = 250 bytes — marginal, and fragile to struct growth).
- Linked list on heap: unnecessary complexity for ≤5 items.

**Why fixed array + per-slot keys**: Simple, cache-friendly, fits Pebble memory model. Slot keys are stable across add/remove (delete by zeroing + compacting the logical count, not the key mapping).

### 2. Timer List as a separate Window pushed onto the stack

**Decision**: Implement the Timer List as a new `Window` with a custom `Layer` (not `MenuLayer`). Push it onto the window stack before the main timer window on app open.

**Alternatives considered**:
- Use `SimpleMenuLayer`: limited to text-only rows — can't render the two-line custom format (time + remaining, or stopwatch notation) without raw cell drawing anyway.
- Integrate list into existing main window as another `ControlMode`: would couple unrelated UI logic and require threading a scroll index through all existing mode handlers.

**Why separate Window**: Clean separation of concerns; list window can be independently destroyed when the setting is disabled mid-session. Back exits the app from any screen — there is no "back to list" navigation.

### 3. Implicit new-timer slot created on list open; discarded if user navigates away

**Decision**: When the Timer List window is pushed, immediately create a new timer slot (chrono, running from `epoch()`, `length_ms = 0`) at the "top" logical position. This slot is the default selection. If the user scrolls to and selects an existing timer, the implicit slot is freed before pushing the main window. The slot is only permanently saved to persistence when the app backgrounds (either by the 30 s idle timer or the user explicitly pressing Back from the Timer List window), or when the new timer is selected for editing..

**Why**: Matches the spec: "if you do nothing, that timer continues as a stopwatch and is saved." Avoids a separate "are you sure?" flow. The cost of a wasted persist write on navigation is negligible.

### 4. Ordering: countdown timers by time remaining (soonest first), then stopwatches

**Decision**: On each Timer List render, compute `time_remaining_ms` for each slot. Countdown timers (non-chrono) sort ascending by remaining ms. Stopwatches (chrono) sort by elapsed time descending (longest running first), appended after countdown timers. The implicit new timer always appears at position 0.

**Why**: Soonest-expiring timer is most urgent and should be at the top. Stopwatches have no expiry, so relative order by elapsed is a reasonable secondary sort.

### 5. 30-second idle auto-background specific to Timer List, not global

**Decision**: The existing `AUTO_BACKGROUND_TIMER_LENGTH_MS` (20 min) applies to the main timer window. A new `AppTimer` within the Timer List window fires after 30 000 ms of no button interaction, saves the implicit new stopwatch, and calls `window_stack_pop_all()`.

**Why**: The 30 s timeout is a list-specific UX behaviour. Reusing the global timer would require passing context through callbacks and could interfere with single-timer sessions.

### 6. Hold Down semantics: delete and exit

**Decision**:
- **In Timer List**: hold Down deletes the currently selected existing timer (frees its slot, compacts array, refreshes list). The implicit new timer can also be deleted this way. It is also discarded by navigating and selecting an existing timer.
- **In main timer window**: hold Down deletes that specific timer slot and exits the app. This is consistent regardless of whether the timer was opened from the Timer List or directly.

**Why**: Back always exits the app — there is no navigation path back to the Timer List from an open timer. Hold Down delete therefore also exits. This keeps the mental model simple: leaving any screen (Back or delete) always goes to the watchface.

## Risks / Trade-offs

- **Persist storage exhaustion** → Mitigation: enforce the 5-timer cap in the UI; warn or block before writing a 6th slot.
- **Struct size growth** → Mitigation: `sizeof(Timer)` should be checked at compile time against remaining persist budget; assert or static_assert added.
- **Alarm contention** (two timers expire while app is in background) → Mitigation: out of scope for this change; alarms still fire only when user opens the relevant timer.
- **Migration from v5 persist data** → Mitigation: `timer_persist_read` already checks version keys; on first run after update, load the single existing timer into slot 0 and write new multi-slot format.
- **Hold Down in main window now always exits** → No context flag needed; simplifies the handler.

## Migration Plan

No migration. On first launch after upgrade, `timer_persist_read` will find no valid multi-timer data and start fresh (zero timers). Any existing single-timer state is discarded.
