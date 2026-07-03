## ADDED Requirements

### Requirement: Lap Stopwatch setting controls the lap feature

The app SHALL expose a `Lap Stopwatch` setting in the settings page that is
disabled (off) by default. The lap behavior on the Select button is active only
when this setting is enabled.

The lap feature is **not available on aplite** (the original Pebble / Pebble
Steel), where it is compiled out for RAM. The settings page SHALL make this
limitation clear on the `Lap Stopwatch` row (e.g. a label suffix such as
`(not on original Pebble)`, mirroring the Voice Naming row's
`(Pebble 2 only)`).

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

#### Scenario: Settings page states the aplite limitation

- **WHEN** the user opens the settings page
- **THEN** the `Lap Stopwatch` row indicates that the feature is not available
  on aplite (the original Pebble / Pebble Steel)

#### Scenario: No lap behavior on aplite

- **WHEN** the app runs on aplite
- **THEN** pressing Select on a running timer toggles play/pause regardless of
  the `Lap Stopwatch` setting (the feature is compiled out)

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
- **AND** the user is warned that no lap could be recorded (see the warning
  requirement below)

#### Scenario: Select still toggles play/pause when setting is off

- **WHEN** `Lap Stopwatch` is off
- **AND** the user presses Select on a running timer in Counting mode
- **THEN** play/pause toggles and no lap is recorded

---

### Requirement: Failing to record a lap at capacity warns the user

When a lap cannot be recorded because all timer slots are already in use, the app
SHALL alert the user with both a visible warning message and a haptic cue of
three short vibrations. The original timer SHALL keep running and the play/pause
state SHALL be unchanged.

#### Scenario: Warning shown when lapping at capacity

- **WHEN** the maximum number of timer slots are already in use
- **AND** the user presses Select to record a lap
- **THEN** a warning message is shown indicating that no lap could be recorded
  because all timer slots are full
- **AND** the watch emits three short vibrations
- **AND** the original timer continues running with its play/pause state unchanged

---

### Requirement: Lap slots are named with an incrementing prefix

A recorded lap slot SHALL be named by prepending `Lap [n]: ` to the original
timer's name, where `n` is the lap number starting at 1 and incrementing for each
successive lap recorded from the same originating timer.

If prepending the prefix would make the resulting name exceed the name buffer,
the END of the original name SHALL be trimmed (dropped) so the combined
`Lap [n]: ` prefix plus the trimmed name plus the terminating null fits exactly
within the buffer. The prefix SHALL never be truncated.

#### Scenario: First lap is numbered 1

- **WHEN** the first lap is recorded from a timer named `awesome honeybee`
- **THEN** the new lap slot is named `Lap 1: awesome honeybee`

#### Scenario: Successive laps increment the number

- **WHEN** a second lap is recorded from the same originating timer
- **THEN** the new lap slot is named `Lap 2: awesome honeybee`

#### Scenario: Long original name is trimmed at the end to fit the prefix

- **WHEN** a lap is recorded from a timer whose name is long enough that
  `Lap [n]: <name>` would exceed the name buffer
- **THEN** the lap slot is named `Lap [n]: ` followed by the original name with
  its end trimmed so the full string plus its null terminator fits the buffer
- **AND** the `Lap [n]: ` prefix is preserved in full

#### Scenario: Renaming a lap timer replaces the whole name

- **WHEN** the user re-opens a lap slot and renames it
- **THEN** the entire name including the `Lap [n]: ` prefix is replaced by the
  new name

---

### Requirement: Recorded lap flashes on screen before settling on the original

Immediately after a lap is recorded the display SHALL alternate between the
paused lap copy and the original running timer — 1 s showing the lap, 1 s
showing the original — for 5 seconds, after which the flash auto-dismisses and
only the original timer is shown. The active timer and all button context
remain the original timer throughout.

#### Scenario: Flash alternates for five seconds

- **WHEN** a lap is recorded
- **THEN** the screen shows the paused lap copy for 1 s, then the original for
  1 s, repeating for a total of 5 seconds
- **AND** after 5 seconds the flash auto-dismisses and only the original timer
  is shown

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

---

### Requirement: Approaching the slot limit during a lap warns within the flash

When recording a lap leaves 3 or fewer free timer slots remaining, the
approaching-limit warning defined in the `multi-timer-management` capability
(message conveying the number of free slots remaining, plus three short
vibrations) SHALL be presented within the lap flash window rather than as a
separate 3-second overlay. During the flash, the phase that would show the
original running timer SHALL instead show the warning message, while the phase
that shows the paused lap copy SHALL continue to flash as normal. After the flash
window ends, only the original running timer is shown.

#### Scenario: Lap near the limit shows the warning in place of the original

- **WHEN** a lap is recorded that leaves 3 or fewer free slots remaining
- **THEN** the watch emits three short vibrations
- **AND** during the flash window the display alternates between the paused lap
  copy (1 s) and the warning message shown in place of the original running
  timer (1 s)
- **AND** after the flash window ends only the original running timer is shown

#### Scenario: Lap with ample slots free flashes normally

- **WHEN** a lap is recorded that leaves more than 3 free slots remaining
- **THEN** the flash alternates between the paused lap copy and the original
  running timer as usual, with no warning message and no extra vibration

---

### Requirement: Stopwatch main value shows the current split; header shows total elapsed when lapping is enabled

A stopwatch's **main value** SHALL always show the time elapsed since the most
recent lap was recorded (the current split). Because a lap can only be recorded
when `Lap Stopwatch` is enabled, a stopwatch that has recorded no laps — which
includes every stopwatch while `Lap Stopwatch` is disabled, and any stopwatch
before its first lap — has a split equal to the total elapsed since it started.
Its main value is therefore unchanged from existing behavior in those cases; no
`Lap Stopwatch` check is needed on the main-value path.

The **header** SHALL differ only according to the `Lap Stopwatch` setting:

- **Enabled:** the total elapsed time since the stopwatch was first started,
  prefixed with the count-up arrow (e.g. `-->12:34`).
- **Disabled:** the time of day the timer was started, prefixed with `@` and
  followed by the count-up arrow (e.g. `@12:45-->`), formatted per the watch's
  12/24-hour clock style. The `@` prefix distinguishes this from an overtime
  countdown's header, which also shows a bare `NN:NN-->` (its original base
  length, e.g. `05:00-->`) and would otherwise be visually indistinguishable.
  This replaces the `00:00-->` base-length header shown previously for a
  genuine stopwatch (a timer with no original countdown length). (On aplite,
  where the feature set is compiled out, the previous `00:00-->` header is
  kept.)

This header change applies only to a genuine stopwatch (created with no
countdown length). An ordinary countdown timer that runs past zero into
overtime keeps showing its unchanged base-length header (`05:00-->`)
regardless of the `Lap Stopwatch` setting when disabled — only the
lapping-*enabled* header (above) treats an overtime countdown like a
stopwatch, consistent with Select already recording laps for any running
counting-mode timer once the setting is on.

The main value updates live while the stopwatch runs and holds while it is
paused. Before the first lap, the main value and the header (when lapping is
enabled) show the same time.

Conceptually, a stopwatch with lapping disabled behaves exactly like a stopwatch
with lapping enabled that is still on its first lap, except that the header shows
the start time instead of the total. This keeps the only lapping-dependent code
to the Select handler and the header rendering.

#### Scenario: Before the first lap the split equals the total

- **WHEN** a stopwatch is started with `Lap Stopwatch` enabled and no lap has been
  recorded
- **THEN** the main value and the header both show the total elapsed time since
  the stopwatch was started
- **AND** the header is prefixed with the count-up arrow (e.g. `-->00:07`)

#### Scenario: After a lap the main value counts the new split

- **WHEN** a lap is recorded on a running stopwatch with `Lap Stopwatch` enabled
- **THEN** the main value restarts from zero and counts the time since that lap
- **AND** the header continues to show the total elapsed time since the stopwatch
  was first started

#### Scenario: Lapping disabled shows the start time in the header

- **WHEN** a stopwatch is running with `Lap Stopwatch` disabled
- **THEN** the main value shows the total elapsed time (no lap has been recorded)
- **AND** the header shows the time of day the stopwatch was started, prefixed
  with `@` and followed by the count-up arrow (e.g. a stopwatch started at
  12:45 shows `@12:45-->`)

#### Scenario: An overtime countdown keeps its base-length header regardless of the setting

- **WHEN** an ordinary countdown timer (started with a nonzero length) runs
  past zero into overtime
- **AND** `Lap Stopwatch` is disabled
- **THEN** the header shows the countdown's original base length followed by
  the count-up arrow (e.g. `05:00-->`), unchanged from existing behavior
- **AND** it is not prefixed with `@` and does not show a time of day

---

### Requirement: A recorded lap slot shows its own split and cumulative time

A recorded lap slot (the paused `Lap [n]: ` snapshot) SHALL show its own split as
the main value and its cumulative time as the header, using the same computation
as the active stopwatch:

- The **main value** SHALL show that lap's split — the time between the previous
  lap and this lap (or between the stopwatch start and this lap, for the first
  lap).
- The **header** SHALL show the cumulative total elapsed at the moment the lap was
  recorded, prefixed with the count-up arrow (e.g. `-->12:34`).

#### Scenario: Lap slot shows split and cumulative

- **WHEN** the third lap is recorded 41 seconds after the second, at a cumulative
  total of 12:34
- **THEN** the `Lap 3:` slot shows `00:41` as its main value
- **AND** its header shows `-->12:34`

#### Scenario: First lap slot split is measured from the start

- **WHEN** the first lap is recorded
- **THEN** the `Lap 1:` slot's main value equals the cumulative total at that lap
  (its split is measured from the stopwatch start)
- **AND** its header shows the same time prefixed with the count-up arrow

---

### Requirement: Long press Select restarts and renames the stopwatch when lapping is enabled

When `Lap Stopwatch` is enabled, a long press of Select on a stopwatch in Counting
mode SHALL restart it from the first lap — resetting the total and current split
to zero and resetting the lap numbering so the next recorded lap is `Lap 1` — and
SHALL assign the stopwatch a new name. Previously recorded lap slots are not
affected. When `Lap Stopwatch` is disabled, long press Select restarts the
stopwatch without changing its name (existing behavior).

#### Scenario: Long press Select while lapping restarts and renames

- **WHEN** `Lap Stopwatch` is enabled and a stopwatch is running in Counting mode
- **AND** the user long-presses Select
- **THEN** the stopwatch restarts from zero with its lap numbering reset so the
  next lap is `Lap 1`
- **AND** the stopwatch is given a new name
- **AND** any previously recorded lap slots remain unchanged

#### Scenario: Long press Select without lapping keeps the name

- **WHEN** `Lap Stopwatch` is disabled and a stopwatch is running in Counting mode
- **AND** the user long-presses Select
- **THEN** the stopwatch restarts without changing its name (existing behavior)
