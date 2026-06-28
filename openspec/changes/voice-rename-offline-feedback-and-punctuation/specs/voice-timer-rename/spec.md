## ADDED Requirements

### Requirement: Starting a voice rename while disconnected gives the user feedback

When the user initiates a voice rename and the watch is not connected to the phone, the system SHALL show clear feedback indicating a phone connection is required, and SHALL NOT silently fail or leave the user without explanation. The connection state SHALL be checked via `connection_service_peek_pebble_app_connection()` before a dictation session is started. The feedback SHALL consist of a no-phone-connected icon shown for approximately 1 second and three short vibration pulses.

#### Scenario: Rename attempted while phone is disconnected

- **WHEN** the user holds the Up and Back buttons in `ControlModeEditSec` to start a voice rename
- **AND** the watch is not connected to the phone (e.g. airplane mode)
- **THEN** the system shows a no-phone-connected icon
- **AND** the watch emits three short vibration pulses
- **AND** no dictation session is started
- **AND** the timer's name is unchanged

#### Scenario: Rename proceeds normally while phone is connected

- **WHEN** the user holds the Up and Back buttons in `ControlModeEditSec` to start a voice rename
- **AND** the watch is connected to the phone
- **THEN** the dictation session starts as usual and no connection feedback is shown

#### Scenario: Disconnected feedback auto-dismisses

- **WHEN** the no-phone-connected icon is shown
- **THEN** it disappears automatically after approximately 1 second
- **AND** the watch returns to `ControlModeEditSec` with the timer name unchanged

## MODIFIED Requirements

### Requirement: A successful transcription replaces the timer's name

When the dictation session completes with `DictationSessionStatusSuccess`, the system SHALL update the active timer's name with the transcribed text, truncated to fit the 19-character name field and trimmed of all leading and trailing non-alphanumeric characters (whitespace, punctuation, and symbols), and persist the change.

#### Scenario: Short transcription is saved as-is

- **WHEN** the user speaks "pasta" and the transcription succeeds
- **THEN** the active timer's name is set to "pasta"
- **AND** the name persists after the app is closed and reopened

#### Scenario: Long transcription is truncated at a word boundary

- **WHEN** the user speaks "slow roasted chicken thighs" and the transcription is "slow roasted chicken thighs"
- **AND** the full text exceeds 19 characters
- **THEN** the name is set to "slow roasted" (last word that keeps total ≤ 19 chars), not a mid-word cut

#### Scenario: Single word exceeding 19 characters is hard-truncated

- **WHEN** the transcription is a single token longer than 19 characters (e.g., "superlongwordexample")
- **THEN** the name is set to the first 19 characters of the transcription

#### Scenario: Leading and trailing whitespace is trimmed

- **WHEN** the transcription contains leading or trailing whitespace (e.g., "  pasta  ")
- **THEN** the saved name is "pasta" with no surrounding spaces

#### Scenario: Leading and trailing punctuation is trimmed

- **WHEN** the transcription contains leading or trailing punctuation or symbols (e.g., "...pasta!" or "\"pasta\".")
- **THEN** the saved name is "pasta" with no surrounding non-alphanumeric characters
- **AND** interior non-alphanumeric characters are preserved (e.g., "mac & cheese" stays "mac & cheese")

#### Scenario: Transcription with no alphanumeric characters yields an empty name

- **WHEN** the transcription contains only non-alphanumeric characters (e.g., "?!.")
- **THEN** the saved name is empty after trimming
