## MODIFIED Requirements

### Requirement: A timer's name is the mnemonic name by default but may be replaced by a user-provided voice name
Once assigned, a timer's mnemonic name is the default name and SHALL persist unless the user explicitly replaces it via voice dictation (when `voice_naming_enabled` is true and the platform is emery). After a successful voice rename, the new name persists in place of the mnemonic name and is itself immutable until replaced again by another successful voice dictation.

#### Scenario: Name unchanged after editing a stopwatch's length (no voice rename)
- **WHEN** a stopwatch named "dry mouse" is created at 14:30
- **AND** the user later edits the timer's length (e.g., sets it to 5 minutes) without performing a voice rename
- **THEN** the timer's name remains "dry mouse"

#### Scenario: Name unchanged after converting stopwatch to countdown (no voice rename)
- **WHEN** a stopwatch named "noisy moon" is created at 20:32
- **AND** the user edits the timer length so it now runs as a countdown without performing a voice rename
- **THEN** the timer's name remains "noisy moon"

#### Scenario: Name unchanged after pausing and restarting (no voice rename)
- **WHEN** a timer named "whitish honeybee" is created
- **AND** the timer is paused, edited, and restarted multiple times without performing a voice rename
- **THEN** the timer's name remains "whitish honeybee" throughout

#### Scenario: Voice rename replaces the mnemonic name
- **WHEN** a timer is named "dry mouse" (its mnemonic default)
- **AND** the user performs a successful voice rename in edit mode, speaking "pasta"
- **THEN** the timer's name is "pasta"
- **AND** the name persists after the app is closed and reopened

#### Scenario: Second voice rename replaces the first voice name
- **WHEN** a timer's name is "pasta" (from a prior voice rename)
- **AND** the user performs another successful voice rename, speaking "chicken"
- **THEN** the timer's name is "chicken"
