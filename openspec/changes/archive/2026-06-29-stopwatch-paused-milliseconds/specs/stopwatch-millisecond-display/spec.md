## ADDED Requirements

### Requirement: Paused stopwatch under one hour shows milliseconds

When the active timer is in stopwatch (chrono) mode AND is paused AND its elapsed time is strictly less than one hour, the main time display SHALL show the elapsed time with millisecond precision in the form `M:SS.mmm` (or `MM:SS.mmm`), where `mmm` is the zero-padded millisecond component of the elapsed time.

#### Scenario: Paused stopwatch below one hour shows milliseconds
- **WHEN** a stopwatch has elapsed 1 minute, 23 seconds and 456 milliseconds
- **AND** the stopwatch is paused
- **THEN** the main time display shows `1:23.456`

#### Scenario: Millisecond component is zero-padded
- **WHEN** a stopwatch has elapsed 5 seconds and 7 milliseconds
- **AND** the stopwatch is paused
- **THEN** the millisecond portion of the display reads `.007`

### Requirement: Milliseconds are hidden at one hour or more

When a paused stopwatch's elapsed time is one hour or greater, the main time display SHALL NOT show milliseconds and SHALL keep the existing `H:MM:SS` format, to limit the number of digits shown on screen.

#### Scenario: Paused stopwatch at one hour or more hides milliseconds
- **WHEN** a stopwatch has elapsed 1 hour, 2 minutes and 3 seconds
- **AND** the stopwatch is paused
- **THEN** the main time display shows `1:02:03`
- **AND** no millisecond component is shown

### Requirement: Running stopwatch does not show milliseconds

While a stopwatch is running (not paused), the main time display SHALL NOT show milliseconds, regardless of elapsed time. The running display retains its existing seconds-resolution format.

#### Scenario: Running stopwatch below one hour hides milliseconds
- **WHEN** a stopwatch has elapsed 1 minute and 23 seconds
- **AND** the stopwatch is running
- **THEN** the main time display shows `1:23`
- **AND** no millisecond component is shown

### Requirement: Countdown timers never show milliseconds

The millisecond display applies to stopwatch (chrono) mode only. A countdown timer SHALL NOT show milliseconds in any state (running, paused, or expired).

#### Scenario: Paused countdown timer below one hour hides milliseconds
- **WHEN** a countdown timer shows 1 minute and 23 seconds remaining
- **AND** the timer is paused
- **THEN** the main time display shows `1:23`
- **AND** no millisecond component is shown
