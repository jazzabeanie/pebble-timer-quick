## MODIFIED Requirements

### Requirement: Timer List displays all timers with relevant time information
The Timer List SHALL display each saved timer as a two-line entry.

#### Scenario: Countdown timer entry display
- **WHEN** a timer entry is a countdown timer (not in chrono/stopwatch mode)
- **THEN** line 1 shows the timer's mnemonic name
- **AND** line 2 shows the time remaining (HH:MM:SS)

#### Scenario: Stopwatch entry display
- **WHEN** a timer entry is a stopwatch (in chrono mode)
- **THEN** line 1 shows the timer's mnemonic name
- **AND** line 2 shows the elapsed time (HH:MM:SS)
