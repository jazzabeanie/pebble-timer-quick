## RENAMED Requirements

- FROM: `### Requirement: The guard applies only to wakeup launches`
- TO: `### Requirement: The guard applies only when the app opens to an alarm`

## MODIFIED Requirements

### Requirement: The guard restarts when the alarm starts after a wakeup launch

The wakeup time is rounded down to whole seconds, so the app can open before
the alarm starts. After a wakeup launch, the app SHALL restart the 250 ms guard
window when the alarm starts. The restart SHALL happen only at the first alarm
start after the wakeup launch.

#### Scenario: App opens early, press just after the alarm is ignored

- **WHEN** the app is launched by an alarm wakeup 800 ms before the alarm starts
- **AND** the user presses Down 100 ms after the alarm starts
- **THEN** the press has no effect
- **AND** the alarm keeps vibrating

#### Scenario: Alarm start after a user launch is not guarded

- **WHEN** the user launches the app from the menu, and no countdown ends
  within 5 seconds of the launch
- **AND** the countdown on screen later reaches zero while the app is open
- **AND** the user presses Down 100 ms after the alarm starts
- **THEN** the alarm is snoozed as usual

---

### Requirement: The guard applies only when the app opens to an alarm

The input guard SHALL start only when the app opens to an alarm. That is one of:

- a wakeup launch;
- a user launch that opens straight to a held alarm or to a countdown that
  ended in the last 5 seconds or ends in the next 5 seconds
  (`list-alarm-takeover`);
- an alarm takeover, from the Timer List or from the main window
  (`list-alarm-takeover`).

The guard SHALL NOT start when the countdown that is already on screen in the
main window reaches zero while the app is open. This includes a snoozed or
repeated alarm that rings again. For every other launch (for example a user
launch from the menu or a quick launch, with no timer near its end), button
presses SHALL be handled immediately, as before.

#### Scenario: User launch is not guarded

- **WHEN** the user launches the app from the menu, and no countdown ends
  within 5 seconds of the launch
- **AND** presses Select 100 ms after launch
- **THEN** the press acts normally

#### Scenario: User launch just after a countdown ended is guarded

- **WHEN** a saved countdown ended 3 seconds before the user opens the app
- **AND** the user presses Down 100 ms after launch
- **THEN** the press has no effect
- **AND** the alarm keeps vibrating

#### Scenario: A takeover is guarded

- **WHEN** a countdown ends while the Timer List is open, and its alarm screen
  opens
- **AND** the user presses Back 100 ms later
- **THEN** the app stays open
- **AND** the alarm keeps vibrating

#### Scenario: The on-screen timer's own alarm is not guarded

- **WHEN** the main window shows a countdown in Counting mode after a user
  launch
- **AND** that countdown reaches zero while the app is open
- **AND** the user presses Down 100 ms after the alarm starts
- **THEN** the alarm is snoozed as usual
