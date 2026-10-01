## MODIFIED Requirements

### Requirement: App supports up to 32 concurrent timer slots
The app SHALL support a maximum of 32 concurrent timer or stopwatch instances (increased from the previous limit of 5). Attempting to create a timer beyond the maximum when all slots are in use SHALL be prevented.

**Aplite exception:** aplite has a limit of 3 slots (reduced from 5). Its 24 KB app region cannot hold more slots alongside the alarm-delivery code (measured; see the design of the `aplite-ram-trim` change).

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
- **AND** the user is warned with a message and three short vibrations that no lap could be recorded

#### Scenario: The aplite limit is 3
- **WHEN** the app runs on aplite and 3 timer slots are in use
- **AND** the user opens the app so that the Timer List shows
- **THEN** the app does not create an additional slot
- **AND** the list shows the 3 timers without a "New Timer" entry

---

### Requirement: Timer slots are persisted individually across app launches
Each active timer slot SHALL be saved to its own persistent storage key so that all running timers survive the app being backgrounded or closed.

If the saved timer count is more than the platform's slot limit (for example, 5 timers saved on aplite by a version with a limit of 5), the app SHALL load the first slots up to the limit, in their saved order and with their saved state, and SHALL discard the others. It SHALL NOT discard all timers.

#### Scenario: Multiple timers persist across app close
- **WHEN** 3 timers are active and the app is closed or backgrounded
- **THEN** on the next app launch, all 3 timers are restored with their correct state (time remaining, running/paused status)

#### Scenario: Timer count persists
- **WHEN** the app is closed with N active timers
- **THEN** on the next app launch the timer count is restored as N

#### Scenario: More saved timers than the limit
- **WHEN** 5 timers are saved and the app opens on a platform with a limit of 3 slots
- **THEN** the first 3 saved timers are restored with their correct state
- **AND** the other 2 are discarded, and their saved data is removed
- **AND** the timer count is 3
