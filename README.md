# pebble-timer-quick

QuickTimer is a timer app for the Pebble Smartwatch, intended to be the fastest
way to start a timer or stopwatch. If you think that needing 5 seconds to set a
countdown timer is far too long, then QuickTimer is for you. With QuickTimer,
rest assured that you are not wasting precious moments of your life.

QuickTimer starts counting as soon as you open the app. As soon as you know
that you need a countdown timer, open the app and then think how long that
timer needs to be. If you want a timer for 1 minute and it takes you 6 seconds
to start the timer, then your timer will be off by 10%, and that can be life or
death. If you like your soft boiled eggs cooked for exactly 6 minutes and 20 seconds,
QuickTimer will help you get the gooey texture you desire.

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

Based on [YclepticStudios/pebble-timer-plus](https://github.com/YclepticStudios/pebble-timer-plus).

The following screenshots are actually from the original pebble-timer-plus, but
QuickTimer looks a lot like that.

![Timer+ Pebble](https://github.com/YclepticStudios/pebble-timer-plus/blob/master/assets/screenshots/chalk-animated.gif)
![Timer+ Pebble](https://github.com/YclepticStudios/pebble-timer-plus/blob/master/assets/screenshots/basalt-animated.gif)
![Timer+ Pebble](https://github.com/YclepticStudios/pebble-timer-plus/blob/master/assets/screenshots/aplite-animated.gif)

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

If installing to the emulator fails:

- build and install the pebble-demo, or some other project taht you know works
- `pebble clean`
- `uv pip install --upgrade --reinstall pebble-tool`
- `rm -rf ~/.pebble-sdk`
- `pebble sdk install latest`

Other resources that might be helpful if the above fails:

- https://www.reddit.com/r/pebble/comments/1ih3umk/current_pebble_development_options/
- [Rebble hackathon VM](https://rebble.io/hackathon-002/vm/)
- I can't seem to find the option to enable the developer connection mode in the app on iOS
- https://github.com/richinfante/rebbletool
- https://developer.repebble.com/sdk/cloud

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

LLMs run tests like so: 

```
cd test/functional && ../../conda-env/bin/python -m pytest test_repeat_counter_visibility.py -v --platform=basalt 2>&1
```

## Instructions for Agents

After making code changes, do not active the conda environment. Just run build with
`/home/jared/Workspace/pebble-timer-quick/conda-env/bin/pebble build`, then do
nothing. Don't commit to git either
