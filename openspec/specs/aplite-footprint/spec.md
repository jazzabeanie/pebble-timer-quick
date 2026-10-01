## Purpose

Keep the app inside aplite's 24 KB app region with enough heap to run, without any loss of alarm delivery: which features aplite leaves out, what it does in their place, and the rule that a full heap never stops the app.

## Requirements

### Requirement: The aplite release build fits its app region with a minimum heap

The aplite release build SHALL link inside its 24 KB (24576 byte) app region.
Its free heap, as the build reports it (`Free RAM available (heap)`), SHALL be
at least 1600 bytes.
The app SHALL start and show its windows on aplite with no `App fault` and no
failed allocation in the logs.

#### Scenario: The build links for every platform

- **WHEN** `pebble build` runs with no test option
- **THEN** the build finishes for aplite and for every other target platform
- **AND** the aplite build reports a free heap of 1600 bytes or more

#### Scenario: The app runs on aplite

- **WHEN** the aplite release build opens on the aplite emulator with saved
  timers, and the Timer List shows a row with a held alarm
- **THEN** the logs show no `App fault` and no failed allocation

---

### Requirement: Alarm-delivery code is never the code that is trimmed

Every part of the alarm delivery SHALL stay in the aplite build: the alarm
watch, the held alarm and its takeover in the main window and in the Timer List
(including the list's alarm icon and five-pulse vibration), the next-event
wakeup with its backups, the pending alarm that rings again after an exit, the
launch rule, and the auto-quit rule. A trim for aplite SHALL only remove or
reduce features that cannot stop a timer from ringing. The input guard stays
compiled out on aplite, as the `wakeup-input-guard` capability says.

#### Scenario: A countdown ends in the Timer List on aplite

- **WHEN** the app runs on aplite and a countdown ends while the Timer List is
  open
- **THEN** its row shows the alarm icon and the watch vibrates five short pulses
- **AND** when the user presses Back, the main window shows that timer's alarm,
  vibrating

#### Scenario: A non-active countdown ends while the app is closed on aplite

- **WHEN** the app runs on aplite and closes while the timer on screen ends
  later than a countdown in another slot
- **THEN** the app wakes up at the end of that other countdown and shows its
  alarm

---

### Requirement: Test log output is a build option on aplite

The aplite release build SHALL NOT contain or send the test log output (the
`TEST_STATE` lines of `TEST_LOG` and `test_log_state()`). A test build, made
with the test build option, SHALL contain and send it on every platform. On
every platform except aplite, the release build SHALL keep the test log output,
as before. The app's behavior SHALL be the same with and without the test log
output.

#### Scenario: Aplite release build has no test logs

- **WHEN** the aplite release build is made
- **THEN** its binary contains no `TEST_STATE` text

#### Scenario: Test build has the logs

- **WHEN** a test build runs on an emulator and the app starts
- **THEN** the app logs `TEST_STATE:init`

#### Scenario: Other platforms keep the logs in the release build

- **WHEN** the basalt release build runs and the app starts
- **THEN** the app logs `TEST_STATE:init`

---

### Requirement: Aplite runs with the default settings

On aplite the app SHALL NOT open the phone message inbox and SHALL NOT request
or receive settings from the phone. It SHALL use the default value of every
setting, or the saved value if saved settings exist on the watch. On every
other platform, settings sync SHALL work as before.

#### Scenario: Aplite uses the defaults

- **WHEN** the app starts on aplite with no saved settings
- **THEN** every setting has its default value ("Multiple Timers" is on)
- **AND** the app does not try to open the phone message inbox

#### Scenario: Other platforms still receive settings

- **WHEN** the app runs on basalt and the phone sends a new value for a setting
- **THEN** the app stores the value and uses it

---

### Requirement: Aplite has no button hint icons

On aplite the app SHALL NOT load or draw the button hint icons: the icons at
the screen edges that show what each button does, and the icons shown during an
alarm. The buttons SHALL do the same as on the other platforms. The alarm icon
of the Timer List is alarm delivery and SHALL stay on aplite. On every other
platform the button hint icons SHALL work as before.

#### Scenario: No icon loads fail on aplite

- **WHEN** the app starts on aplite and the user goes through New mode, an
  edit mode, Counting mode, and an alarm
- **THEN** no button hint icon is drawn
- **AND** the logs show no failed image load

#### Scenario: The list alarm icon stays

- **WHEN** the app runs on aplite and the Timer List shows a held alarm
- **THEN** the held timer's row shows the alarm icon

#### Scenario: Other platforms keep the icons

- **WHEN** the app runs on basalt in New mode
- **THEN** the button hint icons show as before

---

### Requirement: A full heap does not stop the app

An animation SHALL NOT stop the app when the heap is full. If the memory for an
animation cannot be allocated, the animated value SHALL go to its end value at
once and the app SHALL go on. A new animation of a text field SHALL replace the
field's running animation, so that quick screen changes do not add up heap use.
This applies to every platform.

#### Scenario: Quick screen changes on aplite

- **WHEN** the app runs on aplite and the user presses buttons in quick
  succession so that the time layout changes several times in one second
- **THEN** the app keeps running
- **AND** the logs show no `App fault`

#### Scenario: The allocation of an animation fails

- **WHEN** an animation starts and its memory cannot be allocated
- **THEN** the animated value has its end value
- **AND** the app keeps running
