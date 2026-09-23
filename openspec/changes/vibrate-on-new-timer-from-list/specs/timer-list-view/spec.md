## MODIFIED Requirements

### Requirement: Select on New Timer entry enters edit mode for the new timer
Pressing Select on the "New Timer" entry SHALL open the main timer window in edit mode for the new implicit timer. The watch SHALL give one short vibration to confirm that the new timer has started, the same as when a new timer is started by a button press elsewhere. Opening the Timer List and selecting an existing timer SHALL NOT vibrate.

#### Scenario: Select on New Timer opens edit mode
- **WHEN** the "New Timer" entry is selected
- **AND** the user presses Select
- **THEN** the main timer window opens in `ControlModeNew` (edit mode) for the new timer which continues counting

#### Scenario: Select on New Timer vibrates once
- **WHEN** the "New Timer" entry is selected
- **AND** the user presses Select
- **THEN** the watch gives one short vibration

#### Scenario: Opening the Timer List does not vibrate
- **WHEN** the app launches into the Timer List
- **AND** the implicit new timer leaves more than 3 free slots
- **THEN** the watch does not vibrate

#### Scenario: Select on an existing timer does not vibrate
- **WHEN** an existing timer entry is selected
- **AND** the user presses Select
- **THEN** the existing timer opens and the watch does not vibrate
