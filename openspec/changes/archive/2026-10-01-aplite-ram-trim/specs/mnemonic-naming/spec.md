## MODIFIED Requirements

### Requirement: Each timer receives a mnemonic name at creation time
When a new timer slot is created, the system SHALL assign it a unique human-readable name derived from the local wall-clock hour and minute at the moment of creation using the Mnemonic Major System. The hour (0–23) maps to an adjective and the minute (0–59) maps to a noun. The name is stored in the timer's persistent data.

**Aplite exception:** aplite has no mnemonic names (its 24 KB app region cannot hold the lookup tables with the alarm-delivery code). On aplite the system SHALL assign the name "Timer N", where N is the lowest number from 1 that no other current timer slot's name uses. The name is stored in the timer's persistent data in the same way. A timer that was saved with a mnemonic name by an earlier version keeps that name.

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

#### Scenario: First timer on aplite
- **WHEN** the app runs on aplite and a new timer slot is created while no other timer exists
- **THEN** the timer's name is "Timer 1"

#### Scenario: Lowest free number on aplite
- **WHEN** the app runs on aplite with timers named "Timer 1" and "Timer 2"
- **AND** the user deletes "Timer 1" and then creates a new timer
- **THEN** the new timer's name is "Timer 1"
- **AND** no two timers have the same name

#### Scenario: A saved mnemonic name stays on aplite
- **WHEN** the app runs on aplite and a timer named "dry mouse" was saved by an earlier version
- **THEN** the timer's name is still "dry mouse"

---

### Requirement: Duplicate names are resolved with a sequential suffix
If a newly created timer would share the same base name as an existing timer slot, the system SHALL append a space and a sequential integer starting from 2. The suffix SHALL increment until the name is unique among all current timer slots.

**Aplite exception:** this rule does not apply on aplite. The "Timer N" name is unique by its number (see "Each timer receives a mnemonic name at creation time").

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
