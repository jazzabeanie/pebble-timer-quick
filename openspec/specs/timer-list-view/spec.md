## ADDED Requirements

### Requirement: Timer List opens when existing timers are present
When the app is launched and the "Multiple Timers" setting is enabled and at least one timer slot is already saved, the app SHALL open to the Timer List window instead of the normal timer view.

#### Scenario: App opens with existing timer and setting enabled
- **WHEN** the user launches the app
- **AND** `multiple_timers_enabled` is `true`
- **AND** at least one saved timer slot exists
- **THEN** the Timer List window is shown as the first visible UI

#### Scenario: App opens with no existing timers
- **WHEN** the user launches the app
- **AND** no saved timer slots exist
- **THEN** the app opens normally to the new-timer edit view (existing behaviour)

#### Scenario: App opens with setting disabled
- **WHEN** the user launches the app
- **AND** `multiple_timers_enabled` is `false`
- **THEN** the app opens normally to the single existing timer view (existing behaviour)

---

### Requirement: Timer List displays all timers with relevant time information
The Timer List SHALL display each saved timer as a two-line entry.

#### Scenario: Countdown timer entry display
- **WHEN** a timer entry is a countdown timer (not in chrono/stopwatch mode)
- **THEN** line 1 shows the total set duration (HH:MM:SS)
- **AND** line 2 shows the time remaining (HH:MM:SS)

#### Scenario: Stopwatch entry display
- **WHEN** a timer entry is a stopwatch (in chrono mode)
- **THEN** line 1 shows the start duration with `-->` appended (e.g., `00:05:00 -->`)
- **AND** line 2 shows the elapsed time (HH:MM:SS)

---

### Requirement: Timer List includes a "New Timer" entry at the top
The Timer List SHALL always show a "New Timer" entry as the first item, which represents an implicit new stopwatch that begins counting from the moment the list opens.

#### Scenario: New Timer entry is highlighted by default
- **WHEN** the Timer List window is displayed
- **THEN** the "New Timer" entry is the selected (highlighted) item

#### Scenario: New Timer is already counting as stopwatch
- **WHEN** the Timer List window is displayed
- **THEN** the implicit new timer has already started counting elapsed time from zero

---

### Requirement: Timer List entries are ordered by next approaching expiry
Existing countdown timers SHALL be listed in ascending order of time remaining (soonest expiry first). Stopwatches SHALL appear after countdown timers, ordered by elapsed time descending (longest running first). The "New Timer" entry is always first regardless of ordering.

#### Scenario: Multiple countdown timers sorted by time remaining
- **WHEN** two countdown timers exist, one with 5 minutes remaining and one with 2 minutes remaining
- **THEN** the 2-minute timer appears above the 5-minute timer in the list

#### Scenario: Stopwatches appear after countdown timers
- **WHEN** both a countdown timer and a stopwatch exist
- **THEN** the countdown timer appears above the stopwatch in the list

---

### Requirement: Up and Down scroll through Timer List entries
The Up and Down buttons SHALL scroll the selection through the list of timers.

#### Scenario: Down scrolls selection downward
- **WHEN** the user presses Down on the Timer List
- **THEN** the selection moves to the next timer entry below

#### Scenario: Up scrolls selection upward
- **WHEN** the user presses Up on the Timer List
- **THEN** the selection moves to the previous timer entry above

#### Scenario: Selection wraps or stops at boundaries
- **WHEN** the user presses Down on the last entry
- **THEN** the selection does not move past the last entry
- **WHEN** the user presses Up on the first entry (New Timer)
- **THEN** the selection does not move above the New Timer entry

---

### Requirement: Select on existing timer opens that timer's running view
Pressing Select on an existing timer entry in the list SHALL open that timer in the normal running timer view. The implicit new timer SHALL be discarded (not saved).

#### Scenario: Select opens existing timer
- **WHEN** the user scrolls to an existing timer entry
- **AND** presses Select
- **THEN** the main timer window opens showing that specific timer
- **AND** the implicit new timer is not saved

---

### Requirement: Select on New Timer entry enters edit mode for the new timer
Pressing Select on the "New Timer" entry SHALL open the main timer window in edit mode for the new implicit timer.

#### Scenario: Select on New Timer opens edit mode
- **WHEN** the "New Timer" entry is selected
- **AND** the user presses Select
- **THEN** the main timer window opens in `ControlModeNew` (edit mode) for the new timer which continues counting

---

### Requirement: Hold Down on a list entry deletes that timer
Holding the Down button while an existing timer entry is selected SHALL delete that timer and remove it from the list. The other timers are unaffected.

#### Scenario: Hold Down deletes selected timer
- **WHEN** the user holds Down on an existing timer entry in the Timer List
- **THEN** that timer slot is removed
- **AND** the remaining timers remain unchanged
- **AND** the list refreshes to show the updated set of timers

#### Scenario: Hold Down on New Timer entry quits the app
- **WHEN** the "New Timer" entry is selected
- **AND** the user holds Down
- **THEN** the app quits and new timer is not saved

---

### Requirement: Hold Down inside an open timer deletes only that timer and exits
When a timer is open in the main timer window and the user holds Down, only that specific timer SHALL be deleted. The app SHALL exit to the watchface. Other timers are unaffected.

#### Scenario: Hold Down deletes only the open timer and exits
- **WHEN** the user holds Down inside the running timer view
- **THEN** only that timer is deleted
- **AND** the app exits to the watchface
- **AND** other running timers are unaffected

---

### Requirement: Back button exits the app from any screen
Pressing the Back button from any screen (Timer List or individual timer view) SHALL exit the app and return the user to the watchface.

#### Scenario: Back on Timer List exits app
- **WHEN** the Timer List is open
- **AND** the user presses Back
- **THEN** the app exits to the watchface

#### Scenario: Back on individual timer exits app
- **WHEN** an individual timer is open
- **AND** the user presses Back
- **THEN** the app exits to the watchface

---

### Requirement: Timer List auto-backgrounds after 30 seconds of inactivity
If no button is pressed for 30 seconds while the Timer List window is visible, the app SHALL automatically go to the background. The implicit new timer SHALL be saved as a stopwatch before backgrounding.

#### Scenario: Auto-background on idle
- **WHEN** the Timer List is opened
- **AND** no button is pressed for 30 consecutive seconds
- **THEN** the app saves the implicit new stopwatch
- **AND** the app goes to the background

#### Scenario: Any button press cancels auto-background
- **WHEN** the Timer List is open
- **AND** the user presses any button
- **THEN** the 30-second idle countdown is discarded and the app remains open

---

### Requirement: Multiple Timers setting toggle in settings page
The settings page SHALL include a "Multiple Timers" toggle that enables or disables the multi-timer behaviour. The default value SHALL be `true` (enabled).

#### Scenario: Setting defaults to enabled
- **WHEN** the app is launched for the first time (no prior settings)
- **THEN** `multiple_timers_enabled` is `true`

#### Scenario: Setting toggle disables Timer List behaviour
- **WHEN** `multiple_timers_enabled` is set to `false`
- **THEN** the app opens directly to the single running timer view regardless of how many timers are saved
