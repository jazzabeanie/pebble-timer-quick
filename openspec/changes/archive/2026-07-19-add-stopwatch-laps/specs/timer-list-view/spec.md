## MODIFIED Requirements

### Requirement: Hold Down on a list entry deletes that timer

Holding the Down button while an existing timer entry is selected SHALL delete
that timer and remove it from the list. The other timers are unaffected. After a
deletion the selection SHALL move to the **previous timer entry** (the one
directly above the deleted entry). If the previous entry is the "New Timer" row
(i.e. the deleted timer was the topmost timer), the selection SHALL instead stay
at that row position so the next timer below shifts up into the selection. If no
timers remain after the deletion, the "New Timer" row SHALL become selected. The
selection SHALL never land on the "Delete all" entry as a result of a deletion.
(On aplite the previous post-delete selection behavior is kept; the feature set
is compiled out there.)

#### Scenario: Hold Down deletes selected timer

- **WHEN** the user holds Down on an existing timer entry in the Timer List
- **THEN** that timer slot is removed
- **AND** the remaining timers remain unchanged
- **AND** the list refreshes to show the updated set of timers

#### Scenario: Deleting a timer selects the previous timer

- **WHEN** the user holds Down to delete a timer entry whose entry above is
  another timer (not the "New Timer" row)
- **THEN** the timer entry directly above the deleted one becomes selected
- **AND** the timer that was below the deleted one is not auto-selected

#### Scenario: Deleting the topmost timer keeps the position

- **WHEN** the user holds Down to delete the topmost timer entry (the entry
  directly below the "New Timer" row)
- **AND** at least one other timer remains
- **THEN** the selection stays at that row position
- **AND** the next timer below shifts up into the selection
- **AND** the "New Timer" row does not become selected

#### Scenario: Deleting the only remaining timer selects New Timer

- **WHEN** the user holds Down to delete the only remaining timer entry
- **THEN** the "New Timer" row becomes selected

#### Scenario: Deletion never selects the Delete all entry

- **WHEN** the user holds Down to delete any timer entry
- **THEN** the selection does not land on the "Delete all" entry

#### Scenario: Hold Down on New Timer entry quits the app

- **WHEN** the "New Timer" entry is selected
- **AND** the user holds Down
- **THEN** the app quits and new timer is not saved

### Requirement: Back button exits the app from any screen

Pressing the Back button from any screen (Timer List or individual timer view)
SHALL exit the app and return the user to the watchface, **except** while the
lap flash is active after recording a lap. In that window Back opens the
recorded lap instead of exiting, as defined by the `stopwatch-laps` capability.

#### Scenario: Back on Timer List exits app

- **WHEN** the Timer List is open
- **AND** the user presses Back
- **THEN** the app exits to the watchface

#### Scenario: Back on individual timer exits app

- **WHEN** an individual timer is open
- **AND** no lap flash is active
- **AND** the user presses Back
- **THEN** the app exits to the watchface

#### Scenario: Back during the lap flash does not exit

- **WHEN** an individual timer is open and the lap flash is active
- **AND** the user presses Back
- **THEN** the app does not exit and the recorded lap becomes the active timer

## ADDED Requirements

### Requirement: Timer List scrolls when entries exceed the screen

The Timer List SHALL scroll its viewport so that any entry can be reached when
the number of entries exceeds what fits on screen, keeping the selected entry
visible.

#### Scenario: Scrolling reveals off-screen entries

- **WHEN** more timer entries exist than fit on the screen
- **AND** the user scrolls the selection toward an off-screen entry
- **THEN** the viewport scrolls to keep the selected entry visible

#### Scenario: Selected entry stays visible

- **WHEN** the selection moves to an entry not currently in view
- **THEN** the list scrolls so the selected entry is shown

---

### Requirement: Timer List includes a pinned "Delete all" entry

The Timer List SHALL always display a "Delete all" entry pinned at the very
bottom of the list, regardless of whether the lap feature is enabled. (Not on
aplite, where the feature set is compiled out and the previous list behavior is
unchanged; see the design's aplite section.)

#### Scenario: Delete all entry is present at the bottom

- **WHEN** the Timer List window is displayed
- **THEN** a "Delete all" entry appears as the last entry in the list

#### Scenario: Hold Down on Delete all removes every timer and exits

- **WHEN** the "Delete all" entry is selected
- **AND** the user holds Down
- **THEN** all timers are removed
- **AND** the app exits to the watchface

#### Scenario: Select on Delete all shows an instruction message

- **WHEN** the "Delete all" entry is selected
- **AND** the user presses Select
- **THEN** a brief message is shown instructing the user to hold the Down button
  to clear all timers
- **AND** no timers are removed
