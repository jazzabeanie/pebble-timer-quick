## Purpose

Ignore button presses that begin just after an alarm shows (a wakeup launch, an alarm takeover, or an alarm start), so that a press already in progress cannot act on the alarm before the user has seen it.

## Requirements

### Requirement: Presses that begin just after a wakeup launch are ignored

When the app is launched by a wakeup event (launch reason `APP_LAUNCH_WAKEUP`),
the app SHALL ignore every button press whose press-down occurs within
`WAKEUP_INPUT_GUARD_MS` (400 ms) of app launch. An ignored press SHALL NOT
trigger any action on any of the four buttons (Back, Up, Select, Down),
including its single-click, long-click, multi-click, and raw press-down
actions, even if a handler for that press would fire after the 400 ms window.

#### Scenario: Press within the window is ignored

- **WHEN** the app is launched by an alarm wakeup
- **AND** the user presses and releases Select 100 ms after launch
- **THEN** the press has no effect
- **AND** the alarm keeps vibrating

#### Scenario: Press late in the window is ignored

- **WHEN** the app is launched by an alarm wakeup
- **AND** the user presses Down 350 ms after launch
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
- **AND** the user presses Down 500 ms after launch
- **THEN** the alarm is snoozed as usual

#### Scenario: A later press after an ignored press works

- **WHEN** a press that began inside the window has been ignored
- **AND** the user presses the same button again after the window
- **THEN** that press acts normally

---

### Requirement: The guard starts at every alarm start

Whenever a countdown's alarm starts while the app is open, the app SHALL start
the 400 ms guard window at the alarm start, with the same rules as at a wakeup
launch. This SHALL apply however the app was launched, and to every alarm
start: the alarm of the countdown already on screen, an alarm that starts soon
after a wakeup launch (the wakeup time is rounded down to whole seconds, so the
app can open before the alarm starts), and a snoozed or repeated timer that
reaches zero again. A button that is held down at the alarm start SHALL be
ignored on release.

#### Scenario: App opens early, press just after the alarm is ignored

- **WHEN** the app is launched by an alarm wakeup 800 ms before the alarm starts
- **AND** the user presses Down 100 ms after the alarm starts
- **THEN** the press has no effect
- **AND** the alarm keeps vibrating

#### Scenario: The on-screen timer's own alarm is guarded

- **WHEN** the user launches the app from the menu
- **AND** the countdown on screen reaches zero while the app is open
- **AND** the user presses Down 100 ms after the alarm starts
- **THEN** the press has no effect
- **AND** the alarm keeps vibrating

#### Scenario: A snoozed alarm that rings again is guarded

- **WHEN** the user snoozes an alarm and the app stays open
- **AND** the snoozed timer reaches zero again
- **AND** the user presses Back 100 ms after the alarm starts
- **THEN** the app stays open
- **AND** the alarm keeps vibrating

#### Scenario: Press held at the alarm start is ignored

- **WHEN** the user is holding Down as the countdown on screen reaches zero
- **AND** the user then releases Down
- **THEN** the alarm is not snoozed and keeps vibrating

#### Scenario: Press after the window at an alarm start works

- **WHEN** the countdown on screen reaches zero while the app is open
- **AND** the user presses Down 500 ms after the alarm starts
- **THEN** the alarm is snoozed as usual

---

### Requirement: The guard applies only when an alarm shows

The input guard SHALL start only when an alarm shows. That is one of:

- a wakeup launch;
- an alarm takeover, from the Timer List or from the main window, including
  a held alarm that takes over when the user leaves the Timer List
  (`list-alarm-takeover`);
- an alarm start (see "The guard starts at every alarm start").

For every other launch or event (for example a user launch from the menu or a
quick launch, with no alarm to show), button presses SHALL be handled
immediately, as before.

#### Scenario: User launch is not guarded

- **WHEN** the user launches the app from the menu, and the Timer List shows
  (with or without a marked held alarm)
- **AND** presses Down 100 ms after launch
- **THEN** the press acts normally

#### Scenario: A takeover is guarded

- **WHEN** an alarm is held in the Timer List, and the user presses Back, so
  its alarm screen opens
- **AND** the user presses Back 100 ms later
- **THEN** the app stays open
- **AND** the alarm keeps vibrating

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
