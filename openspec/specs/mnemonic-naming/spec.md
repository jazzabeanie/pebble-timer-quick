### Requirement: Each timer receives a mnemonic name at creation time
When a new timer slot is created, the system SHALL assign it a unique human-readable name derived from the local wall-clock hour and minute at the moment of creation using the Mnemonic Major System. The hour (0–23) maps to an adjective and the minute (0–59) maps to a noun. The name is stored in the timer's persistent data.

#### Scenario: Name generated from current local time
- **WHEN** a new timer slot is created at local time 14:30
- **THEN** the timer's name is "dry mouse" (adjective for 14, noun for 30)

#### Scenario: Name generated at midnight
- **WHEN** a new timer slot is created at local time 00:00
- **THEN** the timer's name is "sissy sauce" (adjective for 00, noun for 00)

#### Scenario: Name generated at end of day
- **WHEN** a new timer slot is created at local time 23:59
- **THEN** the timer's name is "numb lip" (adjective for 23, noun for 59)

#### Scenario: Name persists across app close and reopen
- **WHEN** a timer with name "dry mouse" is saved and the app is closed and reopened
- **THEN** the timer's name is still "dry mouse"

---

### Requirement: Mnemonic lookup tables are isolated in a dedicated module
The adjective (hours 00–23) and noun (minutes 00–59) lookup tables SHALL reside exclusively in `src/mnemonic.c` and `src/mnemonic.h`. No other source file SHALL contain these tables.

#### Scenario: Lookup tables are not duplicated
- **WHEN** the codebase is built
- **THEN** only `src/mnemonic.c` defines the adjective and noun arrays

---

### Requirement: A timer's name is immutable after creation
Once assigned, a timer's mnemonic name SHALL NOT change regardless of subsequent edits to the timer's length, mode, or any other property. The name always reflects the wall-clock time at which the timer slot was first created.

#### Scenario: Name unchanged after editing a stopwatch's length
- **WHEN** a stopwatch named "dry mouse" is created at 14:30
- **AND** the user later edits the timer's length (e.g., sets it to 5 minutes)
- **THEN** the timer's name remains "dry mouse"

#### Scenario: Name unchanged after converting stopwatch to countdown
- **WHEN** a stopwatch named "noisy moon" is created at 20:32
- **AND** the user edits the timer length so it now runs as a countdown
- **THEN** the timer's name remains "noisy moon"

#### Scenario: Name unchanged after pausing and restarting
- **WHEN** a timer named "whitish honeybee" is created
- **AND** the timer is paused, edited, and restarted multiple times
- **THEN** the timer's name remains "whitish honeybee" throughout

---

### Requirement: Duplicate names are resolved with a sequential suffix
If a newly created timer would share the same base name as an existing timer slot, the system SHALL append a space and a sequential integer starting from 2. The suffix SHALL increment until the name is unique among all current timer slots.

#### Scenario: First duplicate gets suffix 2
- **WHEN** a timer named "dry mouse" already exists
- **AND** a new timer is created at 14:30
- **THEN** the new timer's name is "dry mouse 2"

#### Scenario: Second duplicate gets suffix 3
- **WHEN** timers named "dry mouse" and "dry mouse 2" already exist
- **AND** a new timer is created at 14:30
- **THEN** the new timer's name is "dry mouse 3"

#### Scenario: No suffix when no collision
- **WHEN** no timer with the base name exists
- **AND** a new timer is created
- **THEN** the timer's name has no numeric suffix
