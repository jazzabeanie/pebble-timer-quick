## MODIFIED Requirements

### Requirement: App supports up to 32 concurrent timer slots

The app SHALL support a maximum of 32 concurrent timer or stopwatch instances
(increased from the previous limit of 5). Attempting to create a timer beyond the
maximum when all slots are in use SHALL be prevented.

**Aplite exception:** aplite keeps the previous limit of 5 slots. Its 24 KB app
region cannot hold the enlarged slot array alongside the existing app (measured;
see the design's aplite section).

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
- **AND** the user is warned with a message and three short vibrations that no
  lap could be recorded

## ADDED Requirements

### Requirement: Timer name field accommodates lap-prefixed names

Each timer slot SHALL store a name up to a fixed buffer capacity. The capacity
SHALL be large enough that a lap-prefixed name (`Lap [n]: <original name>`) formed
from any name the app assigns by default fits without losing any of the original
name. The enlarged name length SHALL apply regardless of whether the lap feature
is enabled, on every platform except aplite (which keeps the previous 20-byte
name field for RAM; see the design's aplite section).

A user MAY rename a timer to a name that occupies up to the full buffer capacity
(any name longer than the buffer is itself truncated to fit when set). When such a
near-capacity name is lapped, the `Lap [n]: ` prefix cannot fit alongside the
whole original name, so the original name SHALL be trimmed at its end to make room
for the prefix, as specified by the `stopwatch-laps` capability. The prefix is
never dropped.

#### Scenario: Lap-prefixed name fits without truncating the original name

- **WHEN** a lap is recorded from a timer whose name is at the longest length the
  app assigns by default
- **THEN** the lap slot stores `Lap [n]: <original name>` with the original name
  intact

#### Scenario: Lapping a user-renamed near-capacity name trims the original

- **WHEN** a user has renamed a timer to a name that fills (or nearly fills) the
  name buffer
- **AND** a lap is recorded from that timer
- **THEN** the lap slot is named `Lap [n]: ` followed by the original name with its
  end trimmed so the full string plus its null terminator fits the buffer
- **AND** the `Lap [n]: ` prefix is preserved in full

#### Scenario: Longer names available even with lap feature disabled

- **WHEN** the `Lap Stopwatch` setting is disabled
- **THEN** timer names still use the enlarged name length

### Requirement: Approaching the slot limit warns the user

When a new timer or lap is created that leaves 3 or fewer free timer slots
remaining, the app SHALL warn the user with both an on-screen message and three
short vibrations. (Not on aplite, where the feature set is compiled out and the
previous 5-slot behavior is unchanged.) The message SHALL convey that the slot limit is being
approached, including the number of free slots remaining. This warning SHALL fire
for every such creation from the point 3 slots remain onward (i.e. when the
creation leaves 3, 2, 1, or 0 free slots), not only the first time. Creating a
timer or lap while more than 3 free slots remain SHALL show no warning.

For a normal timer creation the on-screen message SHALL be shown for 3 seconds
starting when the timer is first created, then dismissed automatically. (The
lap-recording case presents the same warning differently; see the
`stopwatch-laps` capability.)

#### Scenario: Warning when a new timer leaves 3 or fewer slots free

- **WHEN** a new timer is created that leaves 3 or fewer free slots remaining
- **THEN** an on-screen message conveying the number of free slots remaining is
  shown for 3 seconds and then automatically dismissed
- **AND** the watch emits three short vibrations

#### Scenario: No warning while more than 3 slots remain free

- **WHEN** a new timer or lap is created that leaves more than 3 free slots
  remaining
- **THEN** no approaching-limit warning is shown and no extra vibration occurs

#### Scenario: Warning repeats for each creation near the limit

- **WHEN** successive timers or laps are created while 3 or fewer slots remain
- **THEN** each such creation shows the approaching-limit warning again
