## ADDED Requirements

### Requirement: Presses that begin just after a wakeup launch are ignored

When the app is launched by a wakeup event (launch reason `APP_LAUNCH_WAKEUP`),
the app SHALL ignore every button press whose press-down occurs within 250 ms
of app launch. An ignored press SHALL NOT trigger any action on any of the four
buttons (Back, Up, Select, Down), including its single-click, long-click,
multi-click, and raw press-down actions, even if a handler for that press would
fire after the 250 ms window.

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
- **AND** the user presses Down 300 ms after launch
- **THEN** the alarm is snoozed as usual

#### Scenario: A later press after an ignored press works

- **WHEN** a press that began inside the window has been ignored
- **AND** the user presses the same button again after the window
- **THEN** that press acts normally

---

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

- **WHEN** the user launches the app from the menu
- **AND** a countdown alarm starts while the app is open
- **AND** the user presses Down 100 ms after the alarm starts
- **THEN** the alarm is snoozed as usual

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

### Requirement: The guard is not included on aplite

The input guard SHALL be active on every supported platform except aplite. On
aplite it SHALL be compiled out to save RAM, and button presses SHALL be
handled immediately on every launch, as before.

#### Scenario: Guard on other platforms

- **WHEN** the app runs on basalt and is launched by an alarm wakeup
- **AND** the user presses Select 100 ms after launch
- **THEN** the press has no effect

#### Scenario: No guard on aplite

- **WHEN** the app runs on aplite and is launched by an alarm wakeup
- **AND** the user presses Select 100 ms after launch
- **THEN** the press acts normally
