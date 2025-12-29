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

## Building instructions for LLMs

After making code changes, do not active the conda environment. Just run build with
`/home/jared/Workspace/pebble-timer-quick/conda-env/bin/pebble build`, then do
nothing. Don't commit to git either
