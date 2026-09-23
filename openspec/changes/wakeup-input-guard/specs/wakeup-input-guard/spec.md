## ADDED Requirements

### Requirement: Presses that begin just after a wakeup launch are ignored

When the app is launched by a wakeup event (launch reason `APP_LAUNCH_WAKEUP`),
the app SHALL ignore every button press whose press-down occurs within 300 ms
of app launch. An ignored press SHALL NOT trigger any action on any of the four
buttons (Back, Up, Select, Down), including its single-click, long-click,
multi-click, and raw press-down actions, even if a handler for that press would
fire after the 300 ms window.

#### Scenario: Press within the window is ignored

- **WHEN** the app is launched by an alarm wakeup
- **AND** the user presses and releases Select 100 ms after launch
- **THEN** the press has no effect
- **AND** the alarm keeps vibrating

#### Scenario: Back within the window does not exit or silence

- **WHEN** the app is launched by an alarm wakeup
- **AND** the user presses Back 100 ms after launch
- **THEN** the app stays open
- **AND** the alarm keeps vibrating

#### Scenario: Long press that starts in the window is ignored

- **WHEN** the app is launched by an alarm wakeup
- **AND** the user presses Select 200 ms after launch and holds it past the
  long-press threshold
- **THEN** no long-press action occurs
- **AND** the timer is not restarted or reset

#### Scenario: Press held from before launch is ignored

- **WHEN** a button is already held down as the app is launched by an alarm
  wakeup
- **AND** the user then releases it
- **THEN** the release triggers no action

#### Scenario: Press after the window works normally

- **WHEN** the app is launched by an alarm wakeup
- **AND** the user presses Down 400 ms after launch
- **THEN** the alarm is snoozed as usual

#### Scenario: A later press after an ignored press works

- **WHEN** a press that began inside the window has been ignored
- **AND** the user presses the same button again after the window
- **THEN** that press acts normally

---

### Requirement: The guard applies only to wakeup launches

The input guard SHALL apply only when the launch reason is a wakeup event. For
every other launch reason (for example a user launch from the menu or a quick
launch), button presses SHALL be handled immediately, as before.

#### Scenario: User launch is not guarded

- **WHEN** the user launches the app from the menu
- **AND** presses Select 100 ms after launch
- **THEN** the press acts normally

---

### Requirement: The guard is available on all platforms

The input guard SHALL be active on every supported platform, including aplite.

#### Scenario: Guard on aplite

- **WHEN** the app runs on aplite and is launched by an alarm wakeup
- **AND** the user presses Select 100 ms after launch
- **THEN** the press has no effect
