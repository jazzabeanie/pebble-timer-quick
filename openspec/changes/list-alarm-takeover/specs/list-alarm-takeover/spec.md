## ADDED Requirements

### Requirement: A countdown that ends while the Timer List is open opens its alarm screen

While the Timer List window is open, the app SHALL watch every countdown timer
that was running with time left when the list opened. When a watched countdown
reaches zero, the app SHALL close the Timer List and show that timer in the main
window in Counting mode, as the active timer, with its alarm vibrating. This
SHALL happen within one list refresh (500 ms) of the countdown reaching zero,
whatever row is selected in the list.

#### Scenario: The only saved countdown (slot 0) ends while the list is open

- **WHEN** the user opens the app while the only saved countdown (slot 0) has
  about 20 seconds left
- **AND** the Timer List is shown
- **AND** the countdown reaches zero while the list is still open
- **THEN** the Timer List closes within one list refresh
- **AND** the main window shows that timer in Counting mode
- **AND** the alarm vibrates
- **AND** the next button press after the guard window goes to the alarm
  screen, not to the Timer List (Down snoozes the alarm)

#### Scenario: The ending timer is not slot 0

- **WHEN** two countdowns are saved: a long one in slot 0 and a short one in
  slot 1
- **AND** the short one reaches zero while the Timer List is open
- **THEN** the alarm vibrates
- **AND** the short timer becomes the active timer and its alarm screen shows
- **AND** the long timer in slot 0 is not changed and keeps counting down

#### Scenario: The ending timer's list row is not its slot number

- **WHEN** the list sorts the timers so that the ending timer's row is not the
  same as its slot number (for example, the short timer in slot 1 is shown in
  the first timer row, above the long timer in slot 0)
- **AND** the short timer reaches zero while the Timer List is open
- **THEN** the timer that opens is the one that reached zero (its length and
  remaining time are shown), not the timer at the same row or slot number

#### Scenario: The selected row does not matter

- **WHEN** the user has moved the list selection to a different timer row, or
  to the "New Timer" row
- **AND** a watched countdown reaches zero
- **THEN** the timer that reached zero opens, not the selected one

#### Scenario: Two countdowns end in the same refresh

- **WHEN** two watched countdowns both reach zero before the next list refresh
- **THEN** the app opens the countdown that reached zero first

#### Scenario: A deleted countdown is not opened

- **WHEN** the user deletes a watched countdown from the list (hold Down)
- **THEN** that timer does not open when its end time passes
- **AND** the other watched countdowns are still watched

#### Scenario: A delete that moves the ending timer to a lower slot

- **WHEN** a long countdown is in slot 0 and a short countdown is in slot 1
- **AND** the user deletes the long countdown from the list, so the short
  countdown moves to slot 0
- **AND** the short countdown then reaches zero while the list is open
- **THEN** the short countdown opens with its alarm vibrating

---

### Requirement: Countdowns that ended before the list opened do not take over

A countdown that had reached zero more than 5 seconds before the app opened, or
that was paused, when the Timer
List opened SHALL NOT close the list. The list SHALL behave as before for such
timers.

#### Scenario: Overdue countdown at launch

- **WHEN** a saved countdown ended more than 5 seconds before the app was opened
- **AND** the user opens the app and the Timer List is shown
- **THEN** the Timer List stays open

#### Scenario: Paused countdown

- **WHEN** a saved countdown is paused
- **AND** the Timer List is open
- **THEN** the paused countdown never closes the list

---

### Requirement: The implicit new timer is kept as a stopwatch on takeover

When the Timer List closes because a countdown ended, the implicit "New Timer"
slot created when the list opened SHALL NOT be discarded. It SHALL stay saved
as a running stopwatch (chrono) that counts from the moment the list opened.

#### Scenario: New Timer slot kept

- **WHEN** a countdown ends while the Timer List is open
- **THEN** the implicit new timer is still saved as a running stopwatch
- **AND** the next time the Timer List opens it shows that stopwatch as an entry

---

### Requirement: A countdown that ends while the main window shows another timer takes over

While the main window is open, the app SHALL watch every countdown that is not
the active timer and was seen running with time left. When one reaches zero and
the user is not busy (the active timer is not alarming, and the main window is in
Counting mode), the app SHALL make it the active timer and show its alarm screen
with its alarm vibrating, at its end time. The timer that was on screen SHALL
keep running, and if it is a countdown with time left, it SHALL be watched too.

#### Scenario: Another timer ends while a timer counts down on screen

- **WHEN** the main window shows a 5 min countdown in Counting mode
- **AND** a 30 s countdown in another slot reaches zero
- **THEN** the 30 s timer becomes the active timer at its end time
- **AND** its alarm screen shows and the alarm vibrates
- **AND** the 5 min countdown keeps running

#### Scenario: The previous timer is watched after the takeover

- **WHEN** a takeover has moved the screen away from a countdown with time left
- **AND** that countdown later reaches zero while the new timer is not alarming
- **THEN** it takes over and its alarm vibrates

#### Scenario: A timer that was overdue at launch does not take over

- **WHEN** a saved countdown ended more than 5 seconds before the app opened
- **AND** the main window shows another timer
- **THEN** the overdue countdown does not take over

---

### Requirement: A countdown that ends while the user is busy is held

When a watched countdown reaches zero while the user is busy (the active timer
is alarming, or the main window is in New mode or an edit mode), the app SHALL
hold its alarm. A held alarm SHALL NOT vibrate, change the screen, or change the
held timer's end time, length, or base length. The held alarm SHALL take over
as soon as the user is no longer busy: when the current alarm is silenced,
snoozed, or stops vibrating on its own, or when an edit mode ends. The alarm
screen SHALL show the real time since the held timer ended. A held alarm SHALL
vibrate for its full normal time, counted from when it is shown.

#### Scenario: Another timer ends during an alarm

- **WHEN** the active timer's alarm is vibrating
- **AND** another countdown reaches zero
- **THEN** the screen still shows the first alarm
- **AND** the second timer's length is not changed

#### Scenario: The held alarm takes over when the first is silenced

- **WHEN** an alarm is held behind a vibrating alarm
- **AND** the user presses Select to silence the vibrating alarm
- **THEN** the held timer becomes the active timer and its alarm vibrates
- **AND** its screen shows the real time since it ended

#### Scenario: Up on the alarm opens the edit screen, not the held alarm

- **WHEN** an alarm is held behind a vibrating alarm
- **AND** the user presses Up on the vibrating alarm
- **THEN** the vibrating alarm is silenced and its edit screen shows
- **AND** the held alarm does not take over while that edit screen shows
- **AND** when the edit ends, the held alarm takes over

#### Scenario: Another timer ends while editing

- **WHEN** the main window is in EditSec mode
- **AND** another countdown reaches zero
- **THEN** the edit screen stays
- **AND** when the edit expires to Counting, the held alarm takes over

#### Scenario: Held longer than the vibration time

- **WHEN** an alarm has been held for 45 seconds
- **AND** the user becomes free
- **THEN** the held alarm vibrates when it is shown, and does not auto-snooze at
  once
- **AND** its screen shows about 0:45 since it ended

#### Scenario: Two alarms held

- **WHEN** two watched countdowns end while the user is busy
- **AND** the user becomes free
- **THEN** the one that ended first takes over
- **AND** the other stays held until the user is free again, then takes over

#### Scenario: The current alarm stops on its own

- **WHEN** an alarm is held behind a vibrating alarm
- **AND** the user does not press a button until the vibrating alarm stops on
  its own
- **THEN** the held alarm takes over when the first alarm stops

---

### Requirement: A held alarm rings after the app exits

Back SHALL NOT exit the app while an alarm is held (during an alarm, Back
silences it, and the held alarm then takes over). Hold Down, which deletes the
active timer and exits, SHALL instead show the held alarm that ended first,
when one is held. If the app closes by any other path while one or more alarms
are held, the app SHALL wake up about 10 seconds after the exit and show the held
alarm that ended first,
with its alarm vibrating for its full normal time and its screen showing the
real time since it ended. The other held alarms SHALL stay held after that
launch and take over in turn when the user is free. If the user reopens the app
before the wakeup, the held alarms SHALL still take over.

#### Scenario: Hold Down while an alarm is held

- **WHEN** an alarm is held behind a vibrating alarm
- **AND** the user holds Down
- **THEN** the vibrating timer is deleted
- **AND** the app does not exit
- **AND** the held timer's alarm shows and vibrates

#### Scenario: System exit while an alarm is held

- **WHEN** an alarm is held behind a vibrating alarm
- **AND** the app closes by the system exit (hold Back)
- **THEN** the app wakes up about 10 seconds later
- **AND** the held timer is the active timer and its alarm vibrates
- **AND** its screen shows the real time since it ended

#### Scenario: Exit with two held alarms

- **WHEN** two alarms are held and the app closes by the system exit
- **THEN** the app wakes up with the alarm that ended first
- **AND** after the user silences it, the second held alarm takes over

#### Scenario: Reopen before the wakeup

- **WHEN** an alarm is held and the app closes by the system exit
- **AND** the user reopens the app 3 seconds later
- **THEN** the app opens straight to the held alarm

---

### Requirement: Each exit schedules the next alarm event of any timer, with backups

When the app closes, it SHALL schedule one wakeup for the next alarm event of
any timer: the earliest of a held alarm (at about 10 seconds after the exit)
and the end of any running countdown, whether it is the active timer or not. It
SHALL save the other pending alarms so that they are watched or held after the
next launch. It SHALL also schedule two backup wakeups, 2 minutes and 4 minutes
after the first, for the same timer. Each backup SHALL be scheduled even if an
earlier wakeup cannot be scheduled. Any launch of the app SHALL cancel the
backups.

#### Scenario: A non-active countdown ends while the app is closed

- **WHEN** the app closes while the timer on screen ends in 10 minutes and
  another countdown ends in 3 minutes
- **THEN** the app wakes up at the 3 minute countdown's end and shows its alarm
- **AND** the 10 minute countdown still rings at its end

#### Scenario: Two countdowns end close together while the app is closed

- **WHEN** the app closes with two countdowns that end 20 seconds apart
- **THEN** the app wakes up for the first one
- **AND** the second one takes over or is held at its end

#### Scenario: The first wakeup fires

- **WHEN** the app closes with a countdown running
- **AND** the countdown's wakeup opens the app at its end
- **THEN** the backup wakeups are cancelled and do not open the app again

#### Scenario: The first wakeup cannot be scheduled

- **WHEN** another app has a wakeup within 1 minute of the countdown's end
- **AND** the app closes with that countdown running
- **THEN** the app wakes up 2 minutes after the countdown's end
- **AND** the alarm vibrates for its full time and shows about 2:00 since the
  end

#### Scenario: The first two wakeups cannot be scheduled

- **WHEN** other apps have wakeups within 1 minute of the countdown's end and
  of 2 minutes after it
- **AND** the app closes with that countdown running
- **THEN** the app wakes up 4 minutes after the countdown's end
- **AND** the alarm shows about 4:00 since the end

#### Scenario: A held alarm and a countdown ending soon

- **WHEN** an alarm is held and the active countdown ends 30 seconds after the
  app closes by the system exit
- **THEN** the app wakes up for the held alarm
- **AND** the countdown still rings at its end

---

### Requirement: The auto-quit timer never closes the app during an alarm

The app SHALL start its auto-quit timer after an edit only when the countdown's
time left (not its full length) is more than 20 minutes. The app SHALL NOT quit
because of its auto-quit timer while the active timer's alarm vibrates or while
an alarm is held. Any takeover SHALL cancel the auto-quit timer.

#### Scenario: A long timer with little time left

- **WHEN** an edit ends on a 21 minute countdown with 45 seconds left
- **THEN** the auto-quit timer does not start
- **AND** its alarm starts 45 seconds later and still vibrates 60 seconds after
  the edit ended

#### Scenario: More than 20 minutes left

- **WHEN** an edit ends on a 25 minute countdown with 21 minutes left
- **THEN** the app quits about 60 seconds later, as today

#### Scenario: 20 minutes or less left

- **WHEN** an edit ends on a 25 minute countdown with 19 minutes left
- **THEN** the app does not quit on its own

#### Scenario: A takeover before the auto-quit

- **WHEN** an edit ends on a countdown with more than 20 minutes left, which
  starts the auto-quit timer
- **AND** another timer takes over 10 seconds later
- **THEN** the app is still open 60 seconds after the edit ended

---

### Requirement: Opening the app near a timer's end opens that timer

On a user launch, if a saved held alarm exists, the app SHALL open straight to
the held alarm that ended first. Otherwise, if a running countdown ended in the
last 5 seconds or ends in the next 5 seconds, the app SHALL open straight to the
one that ends (or ended) first. In both cases the app SHALL NOT show the Timer
List, SHALL make that timer the active timer in Counting mode, and SHALL start
the input guard when its alarm starts (at launch, if it has already ended). This
SHALL apply whether the "Multiple Timers" setting is on or off.

#### Scenario: Open 3 seconds before a countdown ends

- **WHEN** a saved countdown ends 3 seconds after the user opens the app
- **THEN** the Timer List is not shown
- **AND** the main window shows that countdown in Counting mode
- **AND** its alarm vibrates when it ends
- **AND** a press 100 ms after the alarm starts is ignored

#### Scenario: Open 3 seconds after a countdown ended

- **WHEN** a saved countdown ended 3 seconds before the user opens the app
- **THEN** the Timer List is not shown
- **AND** the main window shows that timer's alarm, vibrating

#### Scenario: The due timer is not slot 0

- **WHEN** a 5 minute countdown is in slot 0 and a countdown in slot 1 ends 3
  seconds after the user opens the app
- **THEN** the slot 1 timer is the one shown

#### Scenario: Not near an end

- **WHEN** the nearest countdown ends 8 seconds after the user opens the app
- **THEN** the Timer List shows as before
- **AND** the list takeover opens the countdown when it ends

---

### Requirement: The input guard starts when the alarm takes over

When a countdown takes over (from the Timer List or from the main window), the
app SHALL ignore every
button press whose press-down occurs within `WAKEUP_INPUT_GUARD_MS` (250 ms) of
the takeover, and every press that was already held down at the takeover. This
uses the same rules as the wakeup input guard: an ignored press triggers no
single-click, long-click, multi-click, or raw press-down action, and the alarm
keeps vibrating.

#### Scenario: Press held from the list is ignored

- **WHEN** the user is holding Down in the Timer List
- **AND** a countdown ends and its alarm screen opens
- **AND** the user then releases Down
- **THEN** the alarm is not snoozed and keeps vibrating

#### Scenario: Press just after the takeover is ignored

- **WHEN** a countdown ends and its alarm screen opens
- **AND** the user presses Back 100 ms later
- **THEN** the app stays open and the alarm keeps vibrating

#### Scenario: Press after the guard window works

- **WHEN** a countdown ends and its alarm screen opens
- **AND** the user presses Down 600 ms later
- **THEN** the alarm is snoozed as usual

---

### Requirement: The takeover is not included on aplite

The alarm takeover and hold SHALL be active on every supported platform except
aplite. On aplite they SHALL be compiled out to save RAM, and the Timer List and
the main window SHALL behave as before.

#### Scenario: No takeover on aplite

- **WHEN** the app runs on aplite and a countdown ends while the Timer List is open
- **THEN** the Timer List stays open
