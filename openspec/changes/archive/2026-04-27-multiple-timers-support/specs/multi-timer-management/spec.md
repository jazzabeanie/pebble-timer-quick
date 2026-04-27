## ADDED Requirements

### Requirement: App supports up to 5 concurrent timer slots
The app SHALL support a maximum of 5 concurrent timer or stopwatch instances. Attempting to create a 6th timer when 5 are already active SHALL be prevented.

#### Scenario: Creating a timer when fewer than 5 exist
- **WHEN** the user creates a new timer
- **AND** fewer than 5 timer slots are in use
- **THEN** the new timer is allocated a slot and saved

#### Scenario: Creating a timer when 5 already exist
- **WHEN** 5 timer slots are already in use
- **AND** the user attempts to open the Timer List (which would create a new implicit timer)
- **THEN** the app does not create an additional slot
- **AND** the user is shown the existing 5 timers without a "New Timer" entry

---

### Requirement: Timer slots are persisted individually across app launches
Each active timer slot SHALL be saved to its own persistent storage key so that all running timers survive the app being backgrounded or closed.

#### Scenario: Multiple timers persist across app close
- **WHEN** 3 timers are active and the app is closed or backgrounded
- **THEN** on the next app launch, all 3 timers are restored with their correct state (time remaining, running/paused status)

#### Scenario: Timer count persists
- **WHEN** the app is closed with N active timers
- **THEN** on the next app launch the timer count is restored as N

---

### Requirement: Deleting a timer frees its slot and compacts the slot list
When a timer is deleted (via hold Down from the list or from inside the open timer), its slot SHALL be freed and the remaining slots compacted so there are no gaps.

#### Scenario: Delete middle timer compacts remaining timers
- **WHEN** 3 timers exist at slots 0, 1, 2
- **AND** the timer at slot 1 is deleted
- **THEN** the timer previously at slot 2 is moved to slot 1
- **AND** the timer count is decremented to 2
- **AND** persist storage for the now-unused slot is cleared

---

### Requirement: Implicit new timer from Timer List is saved only under specific conditions
The implicit stopwatch created when the Timer List opens SHALL be saved permanently only if the user does nothing (allowing it to auto-background) or explicitly navigates into the new timer (by pressing Select on it). It SHALL NOT be saved if the user selects an existing timer from the list.

#### Scenario: Implicit timer saved on auto-background
- **WHEN** the Timer List is open with the implicit new timer counting
- **AND** the app auto-backgrounds after 30 seconds of inactivity
- **THEN** the implicit new timer is written to a new slot in persistent storage

#### Scenario: Implicit timer saved when user selects it
- **WHEN** the user presses Select on the "New Timer" entry
- **AND** then backgrounds or closes the app from within the new timer's view
- **THEN** the new timer is written to persistent storage

#### Scenario: Implicit timer discarded when user selects existing timer
- **WHEN** the user scrolls to an existing timer entry in the Timer List
- **AND** presses Select to open it
- **THEN** the implicit new timer slot is freed without being saved to persistence

---

### Requirement: Timer slots are ordered in memory by next approaching expiry for display
When the Timer List reads slots for display, the data layer SHALL provide them sorted: countdown timers ascending by time remaining, then stopwatches descending by elapsed time. The implicit new timer is always first.

#### Scenario: Sorted order for display
- **WHEN** the Timer List requests the ordered slot list for rendering
- **THEN** the returned list places countdown timers before stopwatches
- **AND** countdown timers are sorted soonest-expiry first
- **AND** stopwatches are sorted longest-elapsed first
