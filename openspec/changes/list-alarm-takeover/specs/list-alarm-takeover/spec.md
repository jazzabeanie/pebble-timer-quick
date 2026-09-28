## ADDED Requirements

### Requirement: A countdown that ends while the Timer List is open is held and marked

While the Timer List window is open, the app SHALL watch every countdown timer
that was running with time left when the list opened, and every saved held
alarm. The Timer List counts as busy: when a watched countdown reaches zero
while the list is open, the app SHALL hold its alarm and SHALL NOT close the
list. Within one list refresh (500 ms) of the countdown reaching zero, whatever
row is selected, the app SHALL:

- mark that timer's row with a large alarm icon that is clearly visible on
  both the selected and the unselected row, and
- vibrate five short pulses in a row, once for that alarm. This pattern SHALL
  be different from the single short pulse for a new timer and from the three
  vibrations of the slot-limit warning.

While the list is open, a held alarm SHALL NOT start its alarm vibration. This
includes slot 0, which the main window under the list checks. The held timer's
end time, length, and base length SHALL NOT change.

#### Scenario: The only saved countdown (slot 0) ends while the list is open

- **WHEN** the user opens the app while the only saved countdown (slot 0) has
  about 20 seconds left
- **AND** the Timer List is shown
- **AND** the countdown reaches zero while the list is still open
- **THEN** the Timer List stays open
- **AND** within one list refresh, the timer's row shows the alarm icon and the
  watch vibrates five short pulses
- **AND** the alarm vibration does not start

#### Scenario: The ending timer is not slot 0

- **WHEN** two countdowns are saved: a long one in slot 0 and a short one in
  slot 1
- **AND** the short one reaches zero while the Timer List is open
- **THEN** the short timer's row shows the alarm icon and the watch vibrates
  five short pulses
- **AND** the long timer in slot 0 is not changed and keeps counting down

#### Scenario: The ending timer's list row is not its slot number

- **WHEN** the list sorts the timers so that the ending timer's row is not the
  same as its slot number (for example, the short timer in slot 1 is shown in
  the first timer row, above the long timer in slot 0)
- **AND** the short timer reaches zero while the Timer List is open
- **THEN** the alarm icon shows on the short timer's row, not on the row at the
  same position as its slot number

#### Scenario: Two countdowns end in the same refresh

- **WHEN** two watched countdowns both reach zero before the next list refresh
- **THEN** both rows show the alarm icon
- **AND** the watch vibrates the five short pulses once

#### Scenario: A deleted countdown is not marked

- **WHEN** the user deletes a watched countdown from the list (hold Down)
- **THEN** no row is marked and there is no vibration when its end time passes
- **AND** the other watched countdowns are still watched

#### Scenario: A delete that moves the ending timer to a lower slot

- **WHEN** a long countdown is in slot 0 and a short countdown is in slot 1
- **AND** the user deletes the long countdown from the list, so the short
  countdown moves to slot 0
- **AND** the short countdown then reaches zero while the list is open
- **THEN** the short countdown's row shows the alarm icon

#### Scenario: The list opens with a saved held alarm

- **WHEN** a saved held alarm exists and the Timer List opens
- **THEN** the held timer's row shows the alarm icon when the list opens
- **AND** the watch vibrates five short pulses when the list opens

---

### Requirement: A held alarm in the Timer List takes over when the user leaves the list

When the user leaves the Timer List while one or more alarms are held, a held
alarm SHALL take over: the list closes, and the main window shows that timer as
the active timer in Counting mode, with its alarm vibrating for its full normal
time and its screen showing the real time since it ended. Unless a rule below
names the timer, the held alarm that ended first SHALL take over. Each way to
leave the list SHALL act as follows:

- Select on a held timer's row: that timer's alarm takes over.
- Select on another existing timer's row: the held alarm takes over instead of
  the selected timer. The selected timer SHALL NOT change and SHALL NOT show
  first.
- Select on the "New Timer" row: the main window opens in New mode, as before.
  New mode is busy, so the alarm stays held and takes over when the new timer
  is set (the edit ends).
- Back: the held alarm takes over instead of the app exiting.
- The 30-second idle timeout: the held alarm takes over instead of the app
  going to the background.
- Hold Down on the "New Timer" row: the implicit new timer is discarded, as
  before, and the held alarm takes over instead of the app exiting.
- Hold Down on a held timer's row: that timer and its alarm are deleted, as
  before. The list stays open, and the other held alarms stay held and marked.
- Hold Down on the "Delete all" row: every timer is deleted, and the app exits,
  as before.

The other held alarms SHALL stay held after a takeover and take over in turn
when the user is free.

#### Scenario: Select on another timer

- **WHEN** an alarm is held in the Timer List
- **AND** the user selects a different existing timer
- **THEN** the held timer's alarm shows, vibrating
- **AND** the selected timer is not changed

#### Scenario: Select on the held timer

- **WHEN** an alarm is held in the Timer List
- **AND** the user selects the held timer's row
- **THEN** that timer's alarm shows, vibrating

#### Scenario: Select on New Timer

- **WHEN** an alarm is held in the Timer List
- **AND** the user selects "New Timer"
- **THEN** the main window opens in New mode, and the alarm stays held
- **AND** when the user has set the new timer and the edit ends, the held
  alarm takes over, vibrating

#### Scenario: Back

- **WHEN** an alarm is held in the Timer List
- **AND** the user presses Back
- **THEN** the app does not exit
- **AND** the held timer's alarm shows, vibrating

#### Scenario: Idle

- **WHEN** an alarm is held in the Timer List
- **AND** the user presses no button for 30 seconds
- **THEN** the app does not go to the background
- **AND** the held timer's alarm shows, vibrating

#### Scenario: Hold Down on New Timer

- **WHEN** an alarm is held in the Timer List
- **AND** the user holds Down on the "New Timer" row
- **THEN** the app does not exit
- **AND** the held timer's alarm shows, vibrating

#### Scenario: Hold Down on the held timer

- **WHEN** an alarm is held in the Timer List
- **AND** the user holds Down on the held timer's row
- **THEN** that timer is deleted and its alarm does not show
- **AND** the list stays open

#### Scenario: Two alarms held in the list

- **WHEN** two alarms are held in the Timer List
- **AND** the user presses Back
- **THEN** the one that ended first takes over
- **AND** after the user silences it, the second one takes over

---

### Requirement: Countdowns that ended before the list opened are not held

A countdown that had reached zero before the app opened and is not a saved
held alarm, or that was paused, when the Timer List opened SHALL NOT be held or
marked, and SHALL NOT vibrate. The list SHALL behave as before for such timers.

#### Scenario: Overdue countdown at launch

- **WHEN** a saved countdown ended before the app was opened, and it is not a
  saved held alarm (for example, the user silenced its alarm and then closed
  the app)
- **AND** the user opens the app and the Timer List is shown
- **THEN** its row shows no alarm icon and the watch does not vibrate
- **AND** Back exits the app as before

#### Scenario: Paused countdown

- **WHEN** a saved countdown is paused
- **AND** the Timer List is open
- **THEN** the paused countdown is never marked

---

### Requirement: The implicit new timer follows the button that leaves the list

When a held alarm takes over from the Timer List, the implicit "New Timer" slot
created when the list opened SHALL be kept or discarded by the same rule as
before for the button that left the list. Back and the idle timeout SHALL keep
it as a running stopwatch (chrono) that counts from the moment the list opened.
Select on an existing timer and hold Down on the "New Timer" row SHALL discard
it.

#### Scenario: Back keeps the New Timer slot

- **WHEN** an alarm is held in the Timer List and the user presses Back
- **THEN** the implicit new timer is still saved as a running stopwatch
- **AND** the next time the Timer List opens it shows that stopwatch as an entry

#### Scenario: Select on another timer discards the New Timer slot

- **WHEN** an alarm is held in the Timer List and the user selects another
  existing timer
- **THEN** the implicit new timer is discarded, as before

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

- **WHEN** a saved countdown ended before the app opened, and it is not a saved
  held alarm
- **AND** the main window shows another timer
- **THEN** the overdue countdown does not take over

---

### Requirement: A countdown that ends while the user is busy is held

When a watched countdown reaches zero while the user is busy (the Timer List
is open, the active timer is alarming, or the main window is in New mode or an
edit mode), the app SHALL hold its alarm. A held alarm SHALL NOT vibrate, change the screen, or change the
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
before the wakeup, the held alarms SHALL still be held: marked in the Timer
List, or taking over in the main window when the user is free.

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
- **THEN** the Timer List shows, with the held timer's row marked
- **AND** the watch vibrates five short pulses

---

### Requirement: An alarm stays pending until it has rung and stopped

An ended countdown's alarm SHALL stay pending until its vibration has started
and then stopped: the user silences or snoozes it with a press that the input
guard allows (on aplite, which has no guard, any press), or it stops on its own after its normal vibration time. A takeover
or a launch that shows the alarm SHALL NOT, by itself, end the pending state.
This SHALL apply to the active timer's own alarm and to an alarm that took over.
If the app closes while the active timer's alarm is pending, the app SHALL treat
it as a held alarm: it SHALL wake up about 10 seconds after the exit and show
that alarm, with its alarm vibrating for its full normal time and its screen
showing the real time since it ended.

#### Scenario: Another app opens during a takeover alarm

- **WHEN** a countdown takes over from the Timer List and its alarm vibrates
- **AND** another app opens 2 seconds later, before the user presses a button
- **THEN** the app wakes up about 10 seconds after it closed
- **AND** that timer is the active timer and its alarm vibrates for its full time
- **AND** its screen shows the real time since it ended

#### Scenario: The app closes before the alarm starts to vibrate

- **WHEN** a wakeup launch opens an ended countdown's alarm
- **AND** the app closes before the vibration starts
- **THEN** the app wakes up about 10 seconds later and shows that alarm

#### Scenario: The active timer's own alarm

- **WHEN** only one countdown is saved, and it is the active timer
- **AND** its alarm vibrates
- **AND** another app opens before the user presses a button
- **THEN** the app wakes up about 10 seconds later and shows that alarm

#### Scenario: A press that the guard ignores does not end the pending state

- **WHEN** a countdown takes over and the user is already holding Back
- **AND** the guard ignores that press, and the system exit closes the app
- **THEN** the app wakes up about 10 seconds later and shows that alarm

#### Scenario: A silenced alarm is not pending

- **WHEN** the user silences a vibrating alarm with Select
- **AND** the app then closes by the system exit
- **THEN** the app does not wake up for that alarm

#### Scenario: An alarm that stops on its own is not pending

- **WHEN** an alarm vibrates for its full time and stops on its own
- **THEN** it is not pending
- **AND** it auto-snoozes as before, and its snoozed countdown is watched as
  usual

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

### Requirement: A user launch holds a saved held alarm

On a user launch, the app SHALL NOT open straight to a saved held alarm. It
SHALL open as usual, and each saved held alarm SHALL be held as if it had ended
while the app was open. If the Timer List shows, the held timers' rows are
marked and the watch vibrates five short pulses when the list opens. If the
Timer List does not show (the "Multiple Timers" setting is off), the main
window rules apply: the held alarm takes over at once if the user is free, or
it stays held while the main window is busy.

A countdown that has not ended at the launch SHALL be watched as usual. A
countdown that ended before the launch and is not a saved held alarm is
overdue at open.

#### Scenario: Open after a wakeup was missed

- **WHEN** a saved countdown in slot 1 ended 2 minutes ago while the app was
  closed, and its wakeup did not launch the app
- **AND** a 5 minute countdown is in slot 0
- **AND** the user opens the app
- **THEN** the Timer List shows, with the slot 1 row marked
- **AND** the watch vibrates five short pulses, and the alarm vibration does
  not start
- **AND** when the user presses Back, the slot 1 alarm shows, vibrating, with
  about 2:00 since it ended

#### Scenario: Open after a wakeup was missed, Multiple Timers off

- **WHEN** the "Multiple Timers" setting is off
- **AND** a saved countdown in slot 1 ended 2 minutes ago while the app was
  closed, and its wakeup did not launch the app
- **AND** the user opens the app, and the main window shows slot 0 in Counting
  mode
- **THEN** the slot 1 alarm takes over at once, vibrating

#### Scenario: Open 3 seconds before a countdown ends

- **WHEN** two countdowns are saved, and one of them ends 3 seconds after the
  user opens the app
- **THEN** the Timer List shows as usual
- **AND** when the countdown ends, its row is marked and the watch vibrates
  five short pulses, and the list stays open

#### Scenario: A silenced alarm does not reopen

- **WHEN** an alarm wakes the app, and the user silences it and closes the app
- **AND** the user opens the app again 3 seconds later
- **THEN** the app opens as usual (the Timer List shows as before, with no
  marked row)

---

### Requirement: The input guard starts when the alarm takes over

On every platform except aplite, when a countdown takes over (from the Timer
List or from the main window), the app SHALL ignore every
button press whose press-down occurs within `WAKEUP_INPUT_GUARD_MS` (400 ms) of
the takeover, and every press that was already held down at the takeover. This
uses the same rules as the wakeup input guard: an ignored press triggers no
single-click, long-click, multi-click, or raw press-down action, and the alarm
keeps vibrating.

#### Scenario: Press held from the list is ignored

- **WHEN** an alarm is held in the Timer List
- **AND** the user holds Down on the "New Timer" row, and the held alarm takes
  over
- **AND** the user then releases Down
- **THEN** the alarm is not snoozed and keeps vibrating

#### Scenario: Press just after the takeover is ignored

- **WHEN** a held alarm takes over from the Timer List (the user pressed Back)
- **AND** the user presses Back 100 ms later
- **THEN** the app stays open and the alarm keeps vibrating

#### Scenario: Press after the guard window works

- **WHEN** a countdown ends and its alarm screen opens
- **AND** the user presses Down 600 ms later
- **THEN** the alarm is snoozed as usual

---

### Requirement: The takeover is included on every platform

The alarm takeover, the held alarm (including the Timer List's alarm icon and
five-pulse vibration), the next-event wakeup with its backups, the launch
rule, the pending alarm, and the auto-quit fix SHALL be active on every
supported platform, including aplite. No timer SHALL fail to ring on aplite
because a part of this change is left out there. The input guard is the only
exception: it SHALL stay compiled out on aplite, as the `wakeup-input-guard`
capability says. On aplite, every press at a takeover SHALL act at once, and
every press SHALL count as the user dealing with a pending alarm.

#### Scenario: Takeover on aplite

- **WHEN** the app runs on aplite and a countdown ends while the Timer List is open
- **THEN** within one list refresh, its row shows the alarm icon and the watch
  vibrates five short pulses
- **AND** when the user presses Back, the main window shows that timer's
  alarm, vibrating

#### Scenario: A non-active countdown ends on aplite while the app is closed

- **WHEN** the app runs on aplite and closes while the timer on screen ends in
  10 minutes and another countdown ends in 3 minutes
- **THEN** the app wakes up at the 3 minute countdown's end and shows its alarm

#### Scenario: No guard at a takeover on aplite

- **WHEN** the app runs on aplite and a countdown takes over
- **AND** the user presses Down 100 ms later
- **THEN** the alarm is snoozed

#### Scenario: A Down held across a takeover on aplite

- **WHEN** the app runs on aplite and an alarm is held in the Timer List
- **AND** the user holds Down on the "New Timer" row, and the held alarm takes
  over
- **AND** the user then releases Down
- **THEN** the timer that took over is not deleted or snoozed
- **AND** the app does not exit
