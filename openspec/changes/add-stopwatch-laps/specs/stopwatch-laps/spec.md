## ADDED Requirements

### Requirement: Lap Stopwatch setting controls the lap feature

The app SHALL expose a `Lap Stopwatch` setting in the settings page that is
disabled (off) by default. The lap behavior on the Select button is active only
when this setting is enabled.

#### Scenario: Setting defaults to off

- **WHEN** the app is launched for the first time with no stored settings
- **THEN** the `Lap Stopwatch` setting is off
- **AND** pressing Select on a running timer toggles play/pause (existing behavior)

#### Scenario: Enabling the setting activates lap behavior

- **WHEN** the user enables `Lap Stopwatch` in the settings page
- **THEN** pressing Select on a running timer in Counting mode records a lap
  instead of toggling play/pause

#### Scenario: Setting persists across launches

- **WHEN** the user enables `Lap Stopwatch` and the app is closed and relaunched
- **THEN** the setting remains enabled

---

### Requirement: Select records a lap from a running timer

Pressing Select SHALL record a lap when the `Lap Stopwatch` setting is enabled
and the app is in Counting mode with the active timer running (not paused): the
active timer is copied into a new timer slot as a paused snapshot, while the
original active timer continues running and remains the on-screen, active timer.

#### Scenario: Recording a lap copies the timer into a new slot

- **WHEN** `Lap Stopwatch` is enabled
- **AND** the app is in Counting mode with the active timer running
- **AND** the user presses Select
- **THEN** a new timer slot is created holding a paused copy of the active timer
  at its current value
- **AND** the original timer keeps running
- **AND** the active/on-screen timer remains the original timer
- **AND** all subsequent button presses act on the original timer

#### Scenario: Lap copy is paused at the snapshot value

- **WHEN** a lap is recorded while the original timer reads a given value
- **THEN** the new lap slot is paused and holds that same value
- **AND** the lap slot does not continue counting

#### Scenario: No free slot prevents recording a lap

- **WHEN** the maximum number of timer slots are already in use
- **AND** the user presses Select to record a lap
- **THEN** no new slot is created
- **AND** the original timer continues running unaffected

#### Scenario: Select still toggles play/pause when setting is off

- **WHEN** `Lap Stopwatch` is off
- **AND** the user presses Select on a running timer in Counting mode
- **THEN** play/pause toggles and no lap is recorded

---

### Requirement: Lap slots are named with an incrementing prefix

A recorded lap slot SHALL be named by prepending `Lap [n]: ` to the original
timer's name, where `n` is the lap number starting at 1 and incrementing for each
successive lap recorded from the same originating timer.

#### Scenario: First lap is numbered 1

- **WHEN** the first lap is recorded from a timer named `awesome honeybee`
- **THEN** the new lap slot is named `Lap 1: awesome honeybee`

#### Scenario: Successive laps increment the number

- **WHEN** a second lap is recorded from the same originating timer
- **THEN** the new lap slot is named `Lap 2: awesome honeybee`

#### Scenario: Renaming a lap timer replaces the whole name

- **WHEN** the user re-opens a lap slot and renames it
- **THEN** the entire name including the `Lap [n]: ` prefix is replaced by the
  new name

---

### Requirement: Recorded lap flashes on screen before settling on the original

Immediately after a lap is recorded the display SHALL alternate between the
paused lap copy and the original running timer — 0.5 s showing the lap, 0.5 s
showing the original — for 3 seconds, after which only the original timer is
shown. The active timer and all button context remain the original timer
throughout.

#### Scenario: Flash alternates for three seconds

- **WHEN** a lap is recorded
- **THEN** the screen shows the paused lap copy for 0.5 s, then the original for
  0.5 s, repeating for a total of 3 seconds
- **AND** after 3 seconds only the original timer is shown

#### Scenario: Buttons during the flash act on the original timer

- **WHEN** the flash is active after recording a lap
- **AND** the user presses a non-Select button (e.g. Up, Down, Back)
- **THEN** the action applies to the original running timer, not the lap copy

#### Scenario: Select during the flash records another lap

- **WHEN** the flash is active after recording a lap
- **AND** the user presses Select
- **THEN** the flash is cancelled
- **AND** a new lap is recorded from the original timer with the next lap number
- **AND** the flash restarts for the new lap
