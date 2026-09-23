## ADDED Requirements

### Requirement: A countdown that ends while the Timer List is open opens its alarm screen

While the Timer List window is open, the app SHALL watch every countdown timer
that was running with time left when the list opened. When a watched countdown
reaches zero, the app SHALL close the Timer List and show that timer in the main
window in Counting mode, as the active timer, with its alarm vibrating. This
SHALL happen within one list refresh (500 ms) of the countdown reaching zero,
whatever row is selected in the list.

#### Scenario: Countdown ends while the list is open

- **WHEN** the user opens the app while a countdown has 10 seconds left
- **AND** the Timer List is shown
- **AND** the countdown reaches zero while the list is still open
- **THEN** the Timer List closes
- **AND** the main window shows that timer in Counting mode
- **AND** the alarm vibrates

#### Scenario: The ending timer is not slot 0

- **WHEN** two countdowns are saved and the one that ends is not in slot 0
- **AND** it reaches zero while the Timer List is open
- **THEN** that timer becomes the active timer and its alarm screen shows

#### Scenario: Two countdowns end in the same refresh

- **WHEN** two watched countdowns both reach zero before the next list refresh
- **THEN** the app opens the countdown that reached zero first

#### Scenario: A deleted countdown is not opened

- **WHEN** the user deletes a watched countdown from the list (hold Down)
- **THEN** that timer does not open when its end time passes
- **AND** the other watched countdowns are still watched

---

### Requirement: Countdowns that ended before the list opened do not take over

A countdown that had already reached zero, or that was paused, when the Timer
List opened SHALL NOT close the list. The list SHALL behave as before for such
timers.

#### Scenario: Overdue countdown at launch

- **WHEN** a saved countdown ended before the app was opened
- **AND** the user opens the app and the Timer List is shown
- **THEN** the Timer List stays open

#### Scenario: Paused countdown

- **WHEN** a saved countdown is paused
- **AND** the Timer List is open
- **THEN** the paused countdown never closes the list

---

### Requirement: The implicit new timer is kept as a stopwatch on takeover

When the Timer List closes because a countdown ended, the implicit "New Timer"
slot created when the list opened SHALL NOT be discarded. It SHALL stay saved
as a running stopwatch (chrono) that counts from the moment the list opened.

#### Scenario: New Timer slot kept

- **WHEN** a countdown ends while the Timer List is open
- **THEN** the implicit new timer is still saved as a running stopwatch
- **AND** the next time the Timer List opens it shows that stopwatch as an entry

---

### Requirement: The input guard starts when the alarm takes over

When the Timer List closes because a countdown ended, the app SHALL ignore every
button press whose press-down occurs within `WAKEUP_INPUT_GUARD_MS` (500 ms) of
the takeover, and every press that was already held down at the takeover. This
uses the same rules as the wakeup input guard: an ignored press triggers no
single-click, long-click, multi-click, or raw press-down action, and the alarm
keeps vibrating.

#### Scenario: Press held from the list is ignored

- **WHEN** the user is holding Down in the Timer List
- **AND** a countdown ends and its alarm screen opens
- **AND** the user then releases Down
- **THEN** the alarm is not snoozed and keeps vibrating

#### Scenario: Press just after the takeover is ignored

- **WHEN** a countdown ends and its alarm screen opens
- **AND** the user presses Back 100 ms later
- **THEN** the app stays open and the alarm keeps vibrating

#### Scenario: Press after the guard window works

- **WHEN** a countdown ends and its alarm screen opens
- **AND** the user presses Down 600 ms later
- **THEN** the alarm is snoozed as usual

---

### Requirement: The takeover is not included on aplite

The alarm takeover SHALL be active on every supported platform except aplite.
On aplite it SHALL be compiled out to save RAM, and the Timer List SHALL behave
as before.

#### Scenario: No takeover on aplite

- **WHEN** the app runs on aplite and a countdown ends while the Timer List is open
- **THEN** the Timer List stays open
