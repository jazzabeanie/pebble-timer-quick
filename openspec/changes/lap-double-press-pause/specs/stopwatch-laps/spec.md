## MODIFIED Requirements

### Requirement: Select records a lap from a running timer

Pressing Select SHALL record a lap when the `Lap Stopwatch` setting is enabled
and the app is in Counting mode with the active timer running (not paused): the
active timer is copied into a new timer slot as a paused snapshot, while the
original active timer continues running and remains the on-screen, active timer.

The snapshot value SHALL be the timer value at the moment the Select button was
pressed down, not the moment the single press was confirmed. Because a running
lap stopwatch also listens for a Select double-press, the single press is
confirmed only after the double-press window expires, so the lap is shown up to
that window later than the press.

#### Scenario: Recording a lap copies the timer into a new slot

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the app is in Counting mode with the active timer running
- **AND** the user presses Select once
- **THEN** a new timer slot is created holding a paused copy of the active timer
  at its value when Select was pressed down
- **AND** the original timer keeps running
- **AND** the active/on-screen timer remains the original timer
- **AND** all subsequent button presses act on the original timer

#### Scenario: Lap copy is paused at the snapshot value

- **WHEN** a lap is recorded while the original timer read a given value at
  Select press-down
- **THEN** the new lap slot is paused and holds that same value
- **AND** the lap slot does not continue counting

#### Scenario: Lap value is not shifted by the double-press window

- **WHEN** the user presses Select once on a running lap stopwatch
- **AND** the lap is confirmed after the double-press window expires
- **THEN** the lap value equals the stopwatch value at press-down, not at
  confirmation

#### Scenario: No free slot prevents recording a lap

- **WHEN** the maximum number of timer slots are already in use
- **AND** the user presses Select to record a lap
- **THEN** no new slot is created
- **AND** the original timer continues running unaffected
- **AND** the user is warned that no lap could be recorded (see the warning
  requirement below)

#### Scenario: Select still toggles play/pause when setting is off

- **WHEN** `Lap Stopwatch` is off
- **AND** the user presses Select on a running timer in Counting mode
- **THEN** play/pause toggles and no lap is recorded

## ADDED Requirements

### Requirement: Double-press Select pauses a running lap stopwatch

When the `Lap Stopwatch` setting is enabled and the app is in Counting mode with
a running stopwatch (chrono) as the active timer, pressing Select twice within
the double-press window (~300 ms) SHALL pause the stopwatch instead of recording
laps. The stopwatch SHALL be paused at its value at the first press-down. No lap
SHALL be recorded for either press.

The double-press SHALL be recognised only in that state. In all other modes and
states (edit modes, paused stopwatch, countdown timers, `Lap Stopwatch` off,
aplite) Select SHALL keep its single-press behavior with no added delay, and two
fast Select presses SHALL act as two single presses.

#### Scenario: Double-press pauses at the first press

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the app is in Counting mode with a running stopwatch
- **AND** the user presses Select twice within the double-press window
- **THEN** the stopwatch is paused
- **AND** its paused value equals its value at the first press-down
- **AND** no new lap slot is created

#### Scenario: Double-press during the lap flash pauses

- **WHEN** the lap flash is active after recording a lap
- **AND** the user presses Select twice within the double-press window
- **THEN** the flash is cancelled
- **AND** the stopwatch is paused at its value at the first press-down
- **AND** no further lap slot is created

#### Scenario: Single press resumes a paused lap stopwatch without delay

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the active stopwatch is paused in Counting mode
- **AND** the user presses Select once
- **THEN** the stopwatch resumes immediately
- **AND** no lap is recorded

#### Scenario: Double-press on a paused lap stopwatch is two single presses

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the active stopwatch is paused in Counting mode
- **AND** the user presses Select twice quickly
- **THEN** the first press resumes the stopwatch
- **AND** the second press is handled as a single press on a running lap
  stopwatch (it records a lap once confirmed, or starts a new double-press)

#### Scenario: Edit modes are not affected

- **WHEN** the app is in New or EditSec mode
- **AND** the user presses Select twice quickly
- **THEN** each press applies its time increment immediately, as before

#### Scenario: Countdown is not affected

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the active timer is a running countdown in Counting mode
- **AND** the user presses Select
- **THEN** play/pause toggles immediately, as before

#### Scenario: Setting off is not affected

- **WHEN** `Lap Stopwatch` is off
- **AND** the user presses Select twice quickly on a running stopwatch
- **THEN** the first press pauses and the second press resumes, as before

#### Scenario: Long press Select still restarts

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the app is in Counting mode with a running stopwatch
- **AND** the user holds Select
- **THEN** the stopwatch restarts and the lap session resets, as before

### Requirement: Display freezes at Select press-down on a running lap stopwatch

When the double-press is armed (the `Lap Stopwatch` setting is enabled and the
app is in Counting mode with a running stopwatch), pressing Select down SHALL
freeze the timer display at the stopwatch value at press-down. The frozen
display SHALL show the split main value with milliseconds and the header total
at that same instant. The freeze SHALL end when the press resolves (single
press, double press, or long press), when the lap-full warning is shown, or
after a safety timeout of about 1 s, whichever comes first. The freeze SHALL
NOT change the timer state. No haptic feedback SHALL be given on press-down.

#### Scenario: Display freezes at press-down

- **WHEN** the double-press is armed
- **AND** the user presses Select down
- **THEN** the display immediately stops at the stopwatch value at press-down
- **AND** the main value shows milliseconds
- **AND** the watch does not vibrate

#### Scenario: Single press shows the same value in the lap flash

- **WHEN** the display is frozen after a Select press-down
- **AND** the press resolves as a single press
- **THEN** the freeze ends and the lap flash starts
- **AND** the lap slot value equals the frozen value

#### Scenario: Double press pauses at the frozen value

- **WHEN** the display is frozen after a Select press-down
- **AND** the user presses Select a second time within the double-press window
- **THEN** the freeze ends
- **AND** the stopwatch is paused at the frozen value, so the display does not
  change

#### Scenario: Long press restarts after the freeze

- **WHEN** the display is frozen after a Select press-down
- **AND** the user holds Select past the long-press threshold
- **THEN** the display stays frozen while the button is held
- **AND** the freeze ends when the stopwatch restarts

#### Scenario: Lap-full warning ends the freeze

- **WHEN** the display is frozen after a Select press-down
- **AND** the single press cannot record a lap because all slots are full
- **THEN** the freeze ends and the lap-full warning is shown

#### Scenario: Safety timeout ends the freeze

- **WHEN** the display is frozen after a Select press-down
- **AND** no click handler resolves the press within about 1 s
- **THEN** the freeze ends and the live stopwatch value is shown again

#### Scenario: Press-down during the lap flash freezes the running stopwatch value

- **WHEN** the lap flash is active after recording a lap
- **AND** the user presses Select down
- **THEN** the flash stops changing frames
- **AND** the display shows the running stopwatch (not the lap slot) frozen at
  its value at press-down
- **AND** the display stays frozen if the flash would have changed frames before
  the press resolves
- **AND** if the press resolves as a single press, a new lap flash starts for
  the new lap
- **AND** if the press resolves as a double press or a long press, the flash is
  cancelled
- **AND** if the lap-full warning or the safety timeout ends the freeze, the
  flash does not continue and the live stopwatch value is shown

#### Scenario: No freeze when not armed

- **WHEN** the double-press is not armed (edit modes, a countdown, a paused
  stopwatch, or `Lap Stopwatch` off)
- **AND** the user presses Select down
- **THEN** the display does not freeze
