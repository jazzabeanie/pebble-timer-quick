## Why

Timers in the list view currently show their total duration on line 1, which makes it hard to distinguish between multiple timers at a glance. Giving each timer a memorable, unique name derived from its start time using the Mnemonic Major System makes the list scannable and human-friendly.

## What Changes

- Each timer receives a name automatically assigned at the moment it is created, encoded from its 24-hour start time (HH:MM) using the Mnemonic Major System: adjective for the hour, noun for the minute.
- A lookup table file (`src/mnemonic.c` / `src/mnemonic.h`) is introduced to encode hour (00–23) → adjective and minute (00–59) → noun without polluting other modules.
- If a newly created timer would share a name with an existing timer, a sequential suffix is appended (e.g., "dry mouse", "dry mouse 2", "dry mouse 3").
- In the Timer List view, line 1 of each timer entry is replaced by the timer's mnemonic name instead of the total set duration or stopwatch start marker.
- Timer names are persisted alongside other timer state.

## Capabilities

### New Capabilities
- `mnemonic-naming`: Lookup table and name-generation logic that maps a 24-hour HH:MM time to an adjective-noun phrase, with collision detection and sequential suffix assignment.

### Modified Capabilities
- `timer-list-view`: Line 1 of each timer entry now displays the mnemonic name instead of the total set duration (countdown) or start-time arrow (stopwatch).

## Impact

- `src/mnemonic.c` / `src/mnemonic.h`: New files containing the 100-entry adjective table (hours 00–23 used) and 100-entry noun table (minutes 00–59 used).
- `src/timer.c` / `src/main.c`: Timer creation code assigns a mnemonic name and stores it in the timer's persistent data.
- Timer list rendering layer: Updated to display `timer.name` on line 1 instead of computing the duration string.
- Persistent storage: Timer slot struct gains a name field (short string, ≤ 20 chars to fit Pebble display).
- `test/functional/`: New tests verifying name generation, collision resolution, and list-view display.
