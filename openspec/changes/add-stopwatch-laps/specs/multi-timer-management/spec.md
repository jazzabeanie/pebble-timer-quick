## MODIFIED Requirements

### Requirement: App supports up to a high reasonable number of concurrent timer slots

The app SHALL support a maximum number of concurrent timer or stopwatch
instances that is a high but reasonable limit (greater than the previous limit of
5). Attempting to create a timer beyond the maximum when all slots are in use
SHALL be prevented.

#### Scenario: Creating a timer when below the maximum

- **WHEN** the user creates a new timer
- **AND** fewer than the maximum number of timer slots are in use
- **THEN** the new timer is allocated a slot and saved

#### Scenario: Creating a timer when at the maximum

- **WHEN** all timer slots are already in use
- **AND** the user attempts to open the Timer List (which would create a new implicit timer)
- **THEN** the app does not create an additional slot
- **AND** the user is shown the existing timers without a "New Timer" entry

#### Scenario: Recording a lap when at the maximum

- **WHEN** all timer slots are already in use
- **AND** the user records a lap
- **THEN** no new slot is created and the original timer continues running

## ADDED Requirements

### Requirement: Timer name field accommodates lap-prefixed names

Each timer slot SHALL store a name long enough to hold a lap-prefixed name
(`Lap [n]: <original name>`) without losing the originating timer's name. The
enlarged name length SHALL apply regardless of whether the lap feature is
enabled.

#### Scenario: Lap-prefixed name fits without truncating the original name

- **WHEN** a lap is recorded from a timer whose name is at the longest length the
  app assigns by default
- **THEN** the lap slot stores `Lap [n]: <original name>` with the original name
  intact

#### Scenario: Longer names available even with lap feature disabled

- **WHEN** the `Lap Stopwatch` setting is disabled
- **THEN** timer names still use the enlarged name length
