## MODIFIED Requirements

### Requirement: A successful transcription replaces the timer's name
When the dictation session completes with `DictationSessionStatusSuccess`, the system SHALL update the active timer's name with the transcribed text, truncated to fit the 19-character name field and trimmed of all leading and trailing non-alphanumeric characters (whitespace, punctuation, and symbols), and persist the change. The system SHALL emit a single short vibration pulse at the moment the transcription is applied, so the user knows the rename completed without having to look at the watch.

#### Scenario: Short transcription is saved as-is
- **WHEN** the user speaks "pasta" and the transcription succeeds
- **THEN** the active timer's name is set to "pasta"
- **AND** the watch emits a single short vibration pulse
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

### Requirement: A failed or cancelled dictation leaves the timer name unchanged and is signalled distinctly
When the dictation session ends with any status other than `DictationSessionStatusSuccess`, the system SHALL NOT modify the timer's name.

The system SHALL emit three short vibration pulses for failures that end without the user dismissing the dictation UI themselves — `FailureSystemAborted`, `FailureNoSpeechDetected`, `FailureConnectivityError`, `FailureDisabled`, `FailureInternalError`, and `FailureRecognizerError`. This pattern SHALL be distinguishable by feel from the single short pulse used for success, so the user knows whether the rename landed without looking at the watch.

The system SHALL remain silent when the user exited the dictation UI themselves — `FailureTranscriptionRejected` and `FailureTranscriptionRejectedWithError` — because in both cases the user was already looking at the watch and knows the rename did not happen.

#### Scenario: User rejects the transcription
- **WHEN** the user rejects the transcription and exits the dictation UI (`DictationSessionStatusFailureTranscriptionRejected`)
- **THEN** the timer's name remains what it was before the session started
- **AND** no vibration is emitted

#### Scenario: User dismisses a transcription error
- **WHEN** the user exits the dictation UI after a transcription error (`DictationSessionStatusFailureTranscriptionRejectedWithError`)
- **THEN** the timer's name is unchanged
- **AND** no vibration is emitted

#### Scenario: Transcription aborted by the system
- **WHEN** the dictation session ends with `DictationSessionStatusFailureSystemAborted`
- **THEN** the timer's name is unchanged
- **AND** the watch emits three short vibration pulses

#### Scenario: No speech detected
- **WHEN** the dictation session ends with `DictationSessionStatusFailureNoSpeechDetected`
- **THEN** the timer's name is unchanged
- **AND** the watch emits three short vibration pulses

#### Scenario: Connectivity error
- **WHEN** the dictation session ends with `DictationSessionStatusFailureConnectivityError`
- **THEN** the timer's name is unchanged
- **AND** the watch emits three short vibration pulses

#### Scenario: Success and failure feel different
- **WHEN** a transcription succeeds
- **THEN** exactly one short pulse is emitted and never the three-pulse pattern
- **AND WHEN** a dictation attempt ends in a non-user-exit failure status
- **THEN** exactly three short pulses are emitted and never the single-pulse pattern

## REMOVED Requirements

### Requirement: The dictation session presents a confirmation dialog before committing
**Reason**: The SDK exposes no callback for "transcription ready, awaiting confirmation", so the requested vibration cannot be emitted while the built-in confirmation screen is up. Disabling the confirmation dialog makes the result callback fire as soon as the transcription is ready, which is where the vibration now happens.

**Migration**: `dictation_session_enable_confirmation` is called with `false`. A successful transcription commits immediately with a short vibration; the user corrects a wrong transcription by repeating the rename gesture. SDK error dialogs (`dictation_session_enable_error_dialogs`) remain enabled and are unaffected.
