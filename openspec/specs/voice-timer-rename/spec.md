### Requirement: Voice rename is available in edit mode when enabled and on a microphone-capable device
When the `voice_naming_enabled` setting is true and the app is running on a microphone-capable platform (emery), the system SHALL allow the user to initiate a voice dictation session from `ControlModeEditSec` by simultaneously holding the Up and Back buttons.

#### Scenario: Feature is available when setting is enabled on emery
- **WHEN** the user is in `ControlModeEditSec`
- **AND** `voice_naming_enabled` is `true`
- **AND** the platform is emery
- **THEN** holding Up and Back simultaneously opens the dictation session UI

#### Scenario: Feature does nothing when setting is disabled
- **WHEN** the user is in `ControlModeEditSec`
- **AND** `voice_naming_enabled` is `false`
- **AND** the platform is emery
- **THEN** holding Up and Back simultaneously does NOT open the dictation session; Up and Back retain their normal individual behaviors

#### Scenario: Feature is absent on non-microphone platforms
- **WHEN** the app is compiled for a non-emery platform (aplite, basalt, chalk, diorite, gabbro)
- **THEN** no voice-rename code is compiled in and holding Up + Back has no special effect

---

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

---

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

---

### Requirement: A failed or cancelled dictation leaves the timer name unchanged
When the dictation session ends with any status other than `DictationSessionStatusSuccess`, the system SHALL NOT modify the timer's name.

#### Scenario: User cancels dictation
- **WHEN** the user dismisses the dictation UI without speaking
- **THEN** the timer's name remains what it was before the session started

#### Scenario: No speech detected
- **WHEN** the dictation session ends with `DictationSessionStatusFailureNoSpeechDetected`
- **THEN** the timer's name is unchanged

#### Scenario: Connectivity error
- **WHEN** the dictation session ends with `DictationSessionStatusFailureConnectivityError`
- **THEN** the timer's name is unchanged

---

### Requirement: The dictation session presents a confirmation dialog before committing
The system SHALL enable the SDK's built-in confirmation dialog (`dictation_session_enable_confirmation`) so the user can review and accept or re-record the transcription before it is applied to the timer name.

#### Scenario: User accepts transcription in confirmation dialog
- **WHEN** the dictation UI shows the transcription "pasta" and the user confirms
- **THEN** the timer's name is set to "pasta"

#### Scenario: User re-records in confirmation dialog
- **WHEN** the dictation UI shows a transcription and the user chooses to re-record
- **THEN** a new dictation attempt begins and the original name is still unchanged

---

### Requirement: The voice naming feature is controlled by a settings toggle
The system SHALL expose a `Voice Naming (Pebble 2 only)` toggle in the app's settings page. The default value SHALL be `false` (disabled).

#### Scenario: Setting defaults to disabled
- **WHEN** the app is installed for the first time with no stored settings
- **THEN** `voice_naming_enabled` is `false`

#### Scenario: Setting persists after saving
- **WHEN** the user enables "Voice Naming" in the settings page and saves
- **THEN** `voice_naming_enabled` is `true` and voice rename is active in edit mode

#### Scenario: Setting persists across app restart
- **WHEN** `voice_naming_enabled` is `true` and the app is closed and reopened
- **THEN** `voice_naming_enabled` remains `true`
