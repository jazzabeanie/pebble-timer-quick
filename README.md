# pebble-timer-plus
Timer+ is a beautiful, simple timer for the Pebble Smartwatch. It will run in the background, using the WakeUp api, 
so there is no need to keep the app open. Once the timer has gone off, or even while it is running, long pressing
the select button will reset the timer. Additionally, starting a timer from 0:00 will cause Timer+ to go into 
stopwatch mode.

![Timer+ Pebble](https://github.com/YclepticStudios/pebble-timer-plus/blob/master/assets/screenshots/chalk-animated.gif)
![Timer+ Pebble](https://github.com/YclepticStudios/pebble-timer-plus/blob/master/assets/screenshots/basalt-animated.gif)
![Timer+ Pebble](https://github.com/YclepticStudios/pebble-timer-plus/blob/master/assets/screenshots/aplite-animated.gif)

## Building and testing

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
- `pebble install --emulator basalt`

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

## Running Tests

Unit tests use [cmocka](https://cmocka.org/) and can be run without the Pebble SDK.

**Dependencies:** `gcc` and `make` (typically pre-installed on Linux; on Debian/Ubuntu: `sudo apt install build-essential`). The cmocka library is pre-installed in `vendor/cmocka_install/`.

To run the tests:

```bash
cd test
make test
```

This will compile and run the test suite for the timer logic.

To clean up test artifacts (removes the compiled `run_tests` binary):

```bash
cd test
make clean
```

This is only needed if you're troubleshooting build issues and want a fresh rebuild. The Makefile automatically rebuilds when source files change, so cleaning is rarely necessary during normal development.

## Running Functional Tests

Functional tests run on the Pebble emulator to verify UI behavior and button interactions.

**Dependencies:**
- Python 3.10+ and the Pebble SDK (in conda-env)
- Tesseract OCR engine: `sudo apt install tesseract-ocr`
- Python packages: `pip install -r requirements.txt`

To run functional tests (runs on basalt by default):

```bash
cd test/functional
python -m pytest test_create_timer.py -v
```

To run on a specific platform:

```bash
python -m pytest test_create_timer.py -v --platform=basalt
```

To run on ALL emulator platforms (aplite, basalt, chalk, diorite, emery):

```bash
python -m pytest test_create_timer.py -v --all-platforms
```

To save screenshots for debugging:

```bash
python -m pytest test_create_timer.py -v --save-screenshots
```

## Building instructions for LLMs

After making code changes, do not active the conda environment. Just run build with
`/home/jared/Workspace/pebble-timer-quick/conda-env/bin/pebble build`, then do
nothing. Don't commit to git either
