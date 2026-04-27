## Context

The `Timer` struct (`src/timer.h`) holds runtime and persist data for each of up to 5 timer slots. It has no name field today. Timer names are to be generated from the wall-clock start time using the Mnemonic Major System (adjective for hour, noun for minute) and must survive app backgrounding via Pebble's `persist_write_data`.

The timer list renderer (`src/timer_list.c` lines 140–164) writes `line1` as either a duration string (countdown) or a duration+arrow string (stopwatch). This is the single location that needs updating.

Persist versioning is managed via `PERSIST_VERSION_KEY`. The `Timer` struct is stored verbatim with `persist_write_data`. Adding a field changes the struct size and requires a version bump to avoid reading garbage from old saves.

## Goals / Non-Goals

**Goals:**
- Generate a deterministic adjective-noun name from the 24-hour HH:MM at the moment `timer_slot_create()` is called.
- Store the name inside the `Timer` struct so it persists automatically alongside all other timer state.
- Resolve collisions (same name already in use) by appending " 2", " 3", etc.
- Replace line 1 in the timer list with the stored name for all existing timer entries.
- Keep mnemonic lookup tables in isolated files (`src/mnemonic.h` / `src/mnemonic.c`).

**Non-Goals:**
- User-editable names.
- Names for the implicit "New Timer" entry (it keeps its label).
- Changing how line 2 is rendered.
- Exposing the name anywhere other than the timer list (e.g., the running timer window).

## Decisions

### 1. Name stored inside `Timer` struct (not a separate lookup)

**Decision:** Add `char name[20]` to `Timer`.

**Rationale:** The persist layer serialises the entire `Timer` struct with a single `persist_write_data` call. Storing the name inside the struct means names persist for free with zero extra code. A separate persist key per timer would require coordinated reads/writes and extra key management.

**Alternative considered:** Generate the name on-the-fly at render time from `start_ms`. Rejected because collision resolution (which suffix " 2"?" 3"?) requires knowing what names all other slots already hold, and re-deriving that consistently at render time is error-prone and wasteful.

### 2. Name assigned inside `timer_slot_create()`

**Decision:** Call `mnemonic_name_for_slot()` immediately after the struct is zero-filled in `timer_slot_create()`, before the function returns.

**Rationale:** This is the only place a new slot is born, and `start_ms = epoch()` is already set there, giving the exact HH:MM to encode. Doing it here keeps callers simple.

**Collision check:** iterate `timer_slots[0..timer_count-2]` (the already-committed slots) and compare names. The new slot is at `timer_count-1` and not yet checked against itself.

### 3. Lookup tables: `adjectives[24]` and `nouns[60]` in `src/mnemonic.c`

**Decision:** Two `static const char *` arrays indexed directly by hour (0–23) and minute (0–59). Public API is one function:

```c
// src/mnemonic.h
void mnemonic_generate_name(int hour, int minute,
                             const char **adj_out, const char **noun_out);
```

Internal to `timer.c`, a helper builds the full string and appends the suffix:

```c
// src/timer.c (static)
static void prv_assign_name(uint8_t new_idx) {
    const char *adj, *noun;
    int hour = wall_clock_hour_from_ms(timer_slots[new_idx].start_ms);
    int min  = wall_clock_min_from_ms(timer_slots[new_idx].start_ms);
    mnemonic_generate_name(hour, min, &adj, &noun);

    char base[18];
    snprintf(base, sizeof(base), "%s %s", adj, noun);

    // Collision check
    int suffix = 1;
    bool collision;
    do {
        collision = false;
        if (suffix == 1) {
            snprintf(timer_slots[new_idx].name, 20, "%s", base);
        } else {
            snprintf(timer_slots[new_idx].name, 20, "%s %d", base, suffix);
        }
        for (uint8_t i = 0; i < new_idx; i++) {
            if (strncmp(timer_slots[i].name,
                        timer_slots[new_idx].name, 20) == 0) {
                collision = true;
                break;
            }
        }
        suffix++;
    } while (collision);
}
```

**Rationale:** Direct array indexing is O(1) and produces zero allocation on Pebble's constrained heap. The public API returns pointers into the `static` arrays so no buffer allocation is needed in `mnemonic.c`.

### 4. Persist version bump

**Decision:** Increment `PERSIST_VERSION` by 1. The existing read path already resets all timers on version mismatch, which is acceptable.

**Rationale:** Adding `char name[20]` increases `sizeof(Timer)` from 40 B to 60 B. Pebble's `persist_read_data` into a larger struct would read stale bytes for the name field, producing garbage display text. A version bump forces a clean slate instead.

### 5. Timer list line 1 change

**Decision:** Replace lines 154–161 in `timer_list.c` with `strncpy(line1, timer_slots[slot].name, sizeof(line1) - 1)` for both the chrono and countdown branches.

**Rationale:** The name field is already the right length (≤ 19 chars + NUL). The existing `line1[20]` buffer is sufficient. No other rendering change is needed.

## Risks / Trade-offs

- **Persist wipe on upgrade** → Existing timers are lost when the user updates the app. Acceptable for a Pebble hobby project with no migration path; the version bump makes the wipe intentional rather than a data-corruption silent failure.
- **Name length overflow** → The longest possible base name is "Jewish cha-cha" (14 chars). With suffix " 5" (max with 5 slots) that is 16 chars — fits comfortably in 20 bytes. No truncation risk.
- **Wall-clock accuracy** → `start_ms` is set from `epoch()` which is wall-clock UTC. Hour/minute extraction must use localtime (Pebble's `clock_to_timestamp` or equivalent). Using UTC would produce wrong names for timers started outside UTC+0.

## Migration Plan

No server-side or coordinated deployment needed. The PERSIST_VERSION bump causes a single clean-slate reset on first launch after update. Users lose no functionality; they simply start fresh.

## Open Questions

- Confirm Pebble SDK function for local wall-clock hour/minute extraction from an epoch ms value (likely `clock_to_timestamp` + `struct tm`). Should be verified before implementation.
