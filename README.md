# pebble-timer-quick

QuickTimer is a timer app for the Pebble Smartwatch, intended to be the fastest
way to start a timer or stopwatch. Made for people that think needing 5 seconds
to set a countdown timer or stopwatch is far too long. With QuickTimer, rest
assured that you are not fiddling away precious moments of your life.

QuickTimer starts counting as soon as you open the app. First press the button,
then think how long the timer needs to be. If you want a timer for 1 minute
and it takes you 6 seconds to start the timer, then your timer will be off by
10%, and that can be life or death. If you like your soft boiled eggs cooked
for exactly 6 minutes and 20 seconds, QuickTimer will help you get the gooey
texture you desire.

QuickTimer works by pressing buttons to increment the countdown timer by set
amounts (1, 5, 20, 60). Once you get used to this, you can set a timer without
even looking at your watch. Here's how it works:

- Open the app
- You enter new timer mode where each button press adds a given amount of minutes
  to the total countdown time
- After 3 seconds of inactivity your timer is set
- If you don't press anything, QuickTimer goes into stopwatch mode instead
- Once you are in counting mode, you can edit your timer, restart your timer,
  or you can enable repeat timers
- Timers that are in alarm can be repeated, snoozed for 5 minutes, or silenced
  to become post timer stopwatches.

Based on [YclepticStudios/pebble-timer-plus](https://github.com/YclepticStudios/pebble-timer-plus).

![New Timer instructions](https://github.com/jazzabeanie/pebble-timer-quick/blob/master/instructions_new_timer.png?raw=true)
![Counting Timer instructions](https://github.com/jazzabeanie/pebble-timer-quick/blob/master/instructions_counting_timer.png?raw=true)

## Buttons

### New timer mode

- Back: Add 1 hour
- Up: Add 20 mins
- Select: Add 5 mins
- Down: Add 1 min
- Hold Up: Toggle reverse direction (increments become decrements)
- Hold Select: Switch to EditSec mode (seconds granularity)
- Hold Down: Quit app and delete timer

After 3 seconds of inactivity, the timer is set and transitions to counting mode.

### EditSec mode (seconds granularity)

- Back: Add 60 seconds
- Up: Add 20 seconds
- Select: Add 5 seconds
- Down: Add 1 second
- Hold Up: Toggle reverse direction
- Hold Select: Switch back to New mode (minutes granularity)
- Hold Down: Quit app and delete timer

### EditRepeat mode

Entered by holding Up while in counting mode (countdown timers only).

- Back: Reset repeat count to 0
- Up: Add 20 repeats
- Select: Add 5 repeats
- Down: Add 1 repeat
- Hold Down: Quit app and delete timer

### Counting mode

- Up: Enter edit mode
- Select: Toggle play/pause
- Down: Extend high-refresh display rate
- Back: Quit app
- Hold Up: Toggle repeat mode on/off (countdown only)
- Hold Select (running): Restart timer to original length
- Hold Select (paused): Reset to 0:00 and enter EditSec mode
- Hold Down: Quit app and delete timer

### Alarm mode

When a countdown timer expires, it enters alarm mode (vibrating).

- Up: Silence alarm and enter edit mode
- Select: Silence alarm and toggle play/pause
- Down: Snooze (add 5 minutes)
- Back: Silence alarm (timer continues as stopwatch)
- Hold Up: Repeat timer (restart with original length)
- Hold Select: Restart timer from original length (running)
- Hold Down: Quit app and delete timer

## Quickness

The table below compares the number of button presses required to set timers in
QuickTimer versus in the default Pebble timer.

```
| Timer Amount | QuickTimer | Default Pebble Timer |
|--------------|------------|----------------------|
| 1 min        | 2          |  5                   |
| 2 min        | 3          |  6                   |
| 3 min        | 4          |  7                   |
| 4 min        | 4          |  8                   |
| 5 min        | 2          |  5+                  |
| 6 min        | 3          |  5+                  |
| 7 min        | 4          |  5+                  |
| 8 min        | 5          |  5+                  |
| 9 min        | 5          |  5+                  |
| 10 min       | 3          |  5+                  |
| 11 min       | 4          |  5+                  |
| 12 min       | 5          |  5+                  |
| 13 min       | 6          |  5+                  |
| 14 min       | 5          |  5+                  |
| 15 min       | 4          |  5+                  |
| 16 min       | 5          |  5+                  |
| 17 min       | 6          |  5+                  |
| 18 min       | 5          |  5+                  |
| 19 min       | 4          |  5+                  |
| 20 min       | 2          |  5+                  |
| 25 min       | 3          |  5+                  |
| 30 min       | 4          |  5+                  |
| 35 min       | 5          |  5+                  |
| 40 min       | 3          |  5+                  |
| 45 min       | 4          |  5+                  |
| 50 min       | 5          |  5+                  |
| 55 min       | 4          |  5+                  |
| 59 min       | 4          |  5                   |
| 60 min       | 2          |  5                   |
| stopwatch    | 1          |  x                   |
```

## Building

- install SDK almost according to https://developer.repebble.com/sdk/
  - install node
  - `sudo apt install libsdl1.2debian libfdt1`
  - `brew install uv`
- create virtual env `conda create --prefix conda-env python=3.10` and activate it with `conda activate conda-env`, although i think it works up to python 3.13
- `uv pip install pebble-tool`
- `pebble sdk install latest`
- `pebble build`
- `pebble install --emulator basalt`

Once it's set up, just run:

- `conda activate conda-env`
- `pebble build`
- `pebble install --emulator basalt`,

If you need to regenerate the placeholder button icon assets, run the generator script manually (it is not part of the standard build):

- `python tools/generate_icons.py`

If installing to the emulator fails:

- build and install the pebble-demo, or some other project that you know works
- `pebble clean`
- `uv pip install --upgrade --reinstall pebble-tool`
- `rm -rf ~/.pebble-sdk`
- `pebble sdk install latest`

## Tests

### Units Tests

Unit tests use [cmocka](https://cmocka.org/) and can be run without the Pebble SDK.

**Dependencies:** `gcc` and `make` (typically pre-installed on Linux; on Debian/Ubuntu: `sudo apt install build-essential`). The cmocka library is pre-installed in `vendor/cmocka_install/`.

To run all tests:

```bash
cd test
make test
```

To run a specific test suite:

```bash
# Run legacy timer logic tests
make test_timer

# Run main app logic tests (including bug fixes)
make test_main
```

To clean up test artifacts (removes the compiled binaries):

```bash
cd test
make clean
```

This is only needed if you're troubleshooting build issues and want a fresh rebuild. The Makefile automatically rebuilds when source files change, so cleaning is rarely necessary during normal development.

### Functional Tests

Functional tests run on the Pebble emulator to verify UI behavior and button interactions.

**Dependencies:**
- Python 3.10+ and the Pebble SDK (in conda-env)
- Python packages: `pip install -r requirements.txt`

Note: The tests use EasyOCR (deep learning-based) for text recognition, which provides better accuracy for the custom LECO 7-segment style font compared to traditional OCR engines like Tesseract. EasyOCR downloads its models (~100MB) on first run.

Test are moving to inspecting logs instead of relying on OCR. The `pebble logs` command needs ~1 second to connect. See `test_log_based.py`.

To run functional tests (runs on basalt by default):

```bash
./test/functional/run_pytest.sh
```

or

```bash
cd test/functional
python -m pytest test_create_timer.py -v
```

To run on a specific platform:

```bash
python -m pytest -v --platform=basalt
```

To run a specific file:

```bash
python -m pytest test_create_timer.py -v --platform=basalt
# or
python -m pytest ./test/functional/test_create_timer.py -v --platform=basalt
```

To run on ALL emulator platforms (aplite, basalt, chalk, diorite, emery):

```bash
python -m pytest test_create_timer.py -v --all-platforms
```

To save screenshots for debugging:

```bash
python -m pytest test_create_timer.py -v --save-screenshots
```

AI Agents run tests like so: 

```
cd test/functional && ../../conda-env/bin/python -m pytest test_repeat_counter_visibility.py -v --platform=basalt 2>&1
```
