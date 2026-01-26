# Specification: Button Icon Tests

## Overview
This specification defines functional tests for verifying that icons appear beside buttons in every app state where a button has functionality. Tests use pixel-based screenshot comparison against per-icon reference masks, following the same approach used for repeat indicator detection.

Some icons already exist (alarm state icons: silence, pause, snooze). Most do not yet exist and their tests are expected to fail (`xfail`) until the corresponding icons are implemented.

**Keywords:** button icons, icon tests, screenshot comparison, pixel mask, reference image, action bar, silence icon, pause icon, snooze icon, repeat icon, play icon, direction icon, functional tests

## Requirements

### 1. Icon Regions (Basalt 144x168)

Each physical button has a **standard icon region** on the screen. Long press actions have a **long-press sub-region** that is smaller and inset toward the screen center within the standard region.

The icon regions below are defined as PIL crop tuples `(left, top, right, bottom)`, derived from the existing icon positions in `drawing.c`.

#### Standard Press Regions

| Button | Screen Position | Current Icon Rect (drawing.c) | Crop Region |
|--------|----------------|-------------------------------|-------------|
| Back | Top-left | GRect(5, 10, 25, 25) | `(0, 5, 35, 40)` |
| Up | Top-right | GRect(114, 10, 25, 25) | `(109, 5, 144, 40)` |
| Select | Mid-right | GRect(127, 76, 15, 15) | `(122, 71, 144, 96)` |
| Down | Bottom-right | GRect(114, 133, 25, 25) | `(109, 128, 144, 163)` |

#### Long Press Sub-Regions

Long press indicators should be small icons positioned slightly inside the standard icon region, toward the center of the screen. These sub-regions are inset from the inner edges of the standard crop region.

| Button | Standard Crop | Long-Press Sub-Region |
|--------|--------------|----------------------|
| Up | `(109, 5, 144, 40)` | `(109, 25, 127, 40)` |
| Select | `(122, 71, 144, 96)` | `(122, 81, 136, 96)` |
| Down | `(109, 128, 144, 163)` | `(109, 128, 127, 143)` |

**Note:** Long press sub-regions are estimates. They should be refined when long-press icons are actually implemented. The Back button has no long-press handler in most states, so no long-press sub-region is defined for it.

### 2. Test Infrastructure

- **Location:** `test/functional/test_button_icons.py`
- **Reuses:** `conftest.py` fixtures (`persistent_emulator`, `_setup_test_environment`)
- **Reference masks:** Stored in `test/functional/screenshots/` as `ref_basalt_<icon_name>_mask.png`

#### Detection Method

For each icon test:
1. Enter the target app state via button presses
2. Capture a screenshot
3. Crop the relevant icon region
4. **Existing icons (pass):** Compare the cropped region's white pixel mask against a stored reference mask PNG (exact match, same as `matches_indicator_reference()` in existing tests)
5. **Non-existing icons (xfail):** Count non-background pixels in the crop region. Assert the count exceeds a threshold (e.g., 20 pixels). The test is marked `@pytest.mark.xfail` and will fail until the icon is implemented.

#### Helper Functions

- `crop_icon_region(img, region)` - Crop a screenshot to the given region tuple
- `has_icon_content(img, region, threshold=20)` - Returns True if the cropped region has ≥ threshold non-background pixels. Background is determined by the dominant color in the region (e.g., green on basalt).
- `matches_icon_reference(img, region, ref_name)` - Crops the region and compares the non-background pixel mask against a stored reference PNG in `screenshots/icon_refs/`. Returns True if masks match.

### 3. Test Cases

Tests are organized by app state. Each button with functionality in that state gets its own test function for granular `xfail` tracking. All tests target basalt only.

---

#### 3.1 Alarm/Vibrating State

Enter state by: Setting a short timer (e.g., 4 seconds via the `short_timer` pattern from `timer-workflow-tests.md`), waiting for it to complete and start vibrating.

| Test Function | Button | Icon | Expected |
|---------------|--------|------|----------|
| `test_alarm_back_icon_silence` | Back | Silence icon (25x25) | **pass** - icon exists and is drawn |
| `test_alarm_up_icon_repeat` | Up | Repeat/reset icon (25x25) | **xfail** - resource exists (`IMAGE_REPEAT_ICON`) but drawing is commented out at `drawing.c:446-447` |
| `test_alarm_select_icon_pause` | Select | Pause icon (15x15) | **pass** - icon exists and is drawn |
| `test_alarm_down_icon_snooze` | Down | Snooze icon (25x25) | **pass** - icon exists and is drawn |

**Reference masks needed:** `ref_basalt_silence_mask.png`, `ref_basalt_pause_mask.png`, `ref_basalt_snooze_mask.png`

**Setup for alarm tests:**
1. Reset app (hold Down)
2. Set a 4-second timer (press Select 4 times in ControlModeEditSec, or use the short timer pattern)
3. Wait for timer to complete and enter vibrating state
4. Take screenshot
5. Verify icon regions

---

#### 3.2 ControlModeNew (Setting New Timer)

Enter state by: App launches in this state by default (after reset). Header shows "New".

| Test Function | Button | Expected Icon | Expected |
|---------------|--------|---------------|----------|
| `test_new_back_icon` | Back | +1hr indicator | **xfail** |
| `test_new_up_icon` | Up | +20min indicator | **xfail** |
| `test_new_select_icon` | Select | +5min indicator | **xfail** |
| `test_new_down_icon` | Down | +1min indicator | **xfail** |
| `test_new_long_up_direction_toggle` | Long Up | Direction toggle indicator | **xfail** - verify screen changes after long press Up (no icon exists, `is_reverse_direction` has no visual representation in `drawing.c`) |
| `test_new_long_select_icon` | Long Select | Reset indicator | **xfail** |
| `test_new_long_down_icon` | Long Down | Quit indicator | **xfail** |

**Direction toggle test (`test_new_long_up_direction_toggle`):**
1. Enter ControlModeNew
2. Take screenshot (baseline)
3. Long press Up (toggles `is_reverse_direction`)
4. Take screenshot
5. Assert screenshots differ (the screen changed in some way)
6. Optionally, also crop the long-press Up sub-region and check for icon content

---

#### 3.3 ControlModeEditSec (Editing Seconds)

Enter state by: From ControlModeCounting while paused at 0:00, long press Select to enter ControlModeEditSec.

| Test Function | Button | Expected Icon | Expected |
|---------------|--------|---------------|----------|
| `test_editsec_back_icon` | Back | +30s indicator | **xfail** |
| `test_editsec_up_icon` | Up | +20s indicator | **xfail** |
| `test_editsec_select_icon` | Select | +5s indicator | **xfail** |
| `test_editsec_down_icon` | Down | +1s indicator | **xfail** |
| `test_editsec_long_up_direction_toggle` | Long Up | Direction toggle indicator | **xfail** |

---

#### 3.4 ControlModeCounting (Timer Running)

Enter state by: Set a timer in ControlModeNew, wait 3 seconds for auto-transition.

| Test Function | Button | Expected Icon | Expected |
|---------------|--------|---------------|----------|
| `test_counting_back_icon` | Back | Exit/background indicator | **xfail** |
| `test_counting_up_icon` | Up | Edit indicator | **xfail** |
| `test_counting_select_icon` | Select | Pause indicator | **xfail** |
| `test_counting_down_icon` | Down | Details/refresh indicator | **xfail** |
| `test_counting_long_up_icon` | Long Up | Enable repeat indicator | **xfail** |
| `test_counting_long_select_icon` | Long Select | Restart indicator | **xfail** |
| `test_counting_long_down_icon` | Long Down | Quit indicator | **xfail** |

---

#### 3.5 ControlModeCounting + Paused

Enter state by: Set a timer, wait for counting mode, press Select to pause.

| Test Function | Button | Expected Icon | Expected |
|---------------|--------|---------------|----------|
| `test_paused_select_icon_play` | Select | Play icon | **xfail** - `IMAGE_PLAY_ICON` resource exists (`music_icon_play.png`) but is never drawn |

**Note:** Other buttons (Back, Up, Down) have the same functions as ControlModeCounting, so only the Select button (which changes from Pause to Play) needs a separate paused-state test.

---

#### 3.6 ControlModeCounting + Chrono (Counting Up)

Enter state by: Let a timer complete, silence the alarm with Back, app enters chrono mode counting up.

| Test Function | Button | Expected Icon | Expected |
|---------------|--------|---------------|----------|
| `test_chrono_select_icon` | Select | Pause indicator | **xfail** |
| `test_chrono_long_select_icon` | Long Select | Reset indicator | **xfail** |

**Note:** Other buttons either share behavior with standard Counting mode or have no function in chrono mode (e.g., long Up has no effect per spec 2.6).

---

#### 3.7 ControlModeEditRepeat

Enter state by: Set a timer, wait for counting mode, long press Up to enable repeat.

| Test Function | Button | Expected Icon | Expected |
|---------------|--------|---------------|----------|
| `test_editrepeat_back_icon` | Back | Reset count indicator | **xfail** |
| `test_editrepeat_up_icon` | Up | +20 repeats indicator | **xfail** |
| `test_editrepeat_select_icon` | Select | +5 repeats indicator | **xfail** |
| `test_editrepeat_down_icon` | Down | +1 repeat indicator | **xfail** |

---

### 4. Reference Mask Generation

For icons that currently exist (silence, pause, snooze), reference masks must be generated before tests can pass:

1. Run the app on basalt emulator
2. Trigger the alarm state
3. Take a screenshot
4. Crop each icon region
5. Create a binary mask: white (255) where non-background pixels exist, black (0) elsewhere
6. Save as `ref_basalt_<name>_mask.png` in the `test/functional/screenshots/icon_refs/` subdirectory

These reference masks should be committed to the repository in the `screenshots/icon_refs/` subdirectory.

### 5. Test Execution

```bash
# Run all button icon tests on basalt
cd test/functional
python -m pytest test_button_icons.py -v

# Run only alarm state tests (expected to mostly pass)
python -m pytest test_button_icons.py -v -k "alarm"

# Run only xfail tests to check progress on new icons
python -m pytest test_button_icons.py -v -k "xfail"

# Save screenshots for debugging
python -m pytest test_button_icons.py -v --save-screenshots
```

## Dependencies

- **functional-tests-emulator.md** (spec #4): Test infrastructure, conftest.py fixtures, emulator helper
- **repeating-timer.md** (spec #6): Pixel-based detection pattern (`has_repeat_indicator`, `matches_indicator_reference`)
- **Pebble SDK**, **Pillow**, **numpy**

## File Structure

```
test/functional/
├── test_button_icons.py          # New: all button icon tests
├── screenshots/
│   ├── ref_basalt_2x_mask.png    # Existing: repeat indicator reference
│   └── icon_refs/                # New: button icon reference masks
│       ├── ref_basalt_silence_mask.png
│       ├── ref_basalt_pause_mask.png
│       └── ref_basalt_snooze_mask.png
```

## Status

- **Status:** Not Started
- **Tests:** NA

## Progress
- 2026-01-27: Spec created.
