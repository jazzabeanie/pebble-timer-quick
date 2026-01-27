# Specification: Button Icons Implementation

## Overview
This specification details the implementation of visual icons for all button interactions in the application. Currently, many states rely on user memory or hidden shortcuts. This feature ensures that every active button has a corresponding icon on the screen, improving UX and discoverability.

The implementation is driven by the requirements defined in `ralph/specs/button-icon-tests.md` and verified by `test/functional/test_button_icons.py`.

## Keywords
button icons, UX, visual feedback, assets, drawing, state machine

## Resources & Assets
A set of new PNG assets must be generated. To facilitate immediate development and consistent style, a Python script will be used to generate these assets programmatically (e.g., simple white text on transparent background).

### Icon Dimensions
- **Standard Action:** 25x25 pixels
- **Small/Long Press:** 15x15 pixels (or smaller if 25x25 fits, but spec suggests 15x15 for some existing ones like pause).
    - *Note based on `button-icon-tests.md`:* Long press regions are "inset". We will use 15x15 for long-press indicators to distinguish them visually, or reuse 25x25 if space permits but position them inner. The `test_button_icons.py` uses specific crop regions.
    - Let's standardize: Standard = 25x25, Small/Secondary = 15x15.

### Required Assets Table

| Resource ID | Filename (suggested) | Text/Symbol | Usage (State -> Button) |
|---|---|---|---|
| `IMAGE_ICON_PLUS_1HR` | `icon_plus_1hr.png` | `+1h` | New -> Back |
| `IMAGE_ICON_PLUS_20MIN` | `icon_plus_20min.png` | `+20` | New -> Up |
| `IMAGE_ICON_PLUS_5MIN` | `icon_plus_5min.png` | `+5m` | New -> Select |
| `IMAGE_ICON_PLUS_1MIN` | `icon_plus_1min.png` | `+1m` | New -> Down |
| `IMAGE_ICON_PLUS_30SEC` | `icon_plus_30sec.png` | `+30` | EditSec -> Back |
| `IMAGE_ICON_PLUS_20SEC` | `icon_plus_20sec.png` | `+20` | EditSec -> Up |
| `IMAGE_ICON_PLUS_5SEC` | `icon_plus_5sec.png` | `+5` | EditSec -> Select |
| `IMAGE_ICON_PLUS_1SEC` | `icon_plus_1sec.png` | `+1` | EditSec -> Down |
| `IMAGE_ICON_RESET` | `icon_reset.png` | `Rst` | Long Select (Various) |
| `IMAGE_ICON_QUIT` | `icon_quit.png` | `X` | Long Down (Various) |
| `IMAGE_ICON_EDIT` | `icon_edit.png` | `Edt` | Counting -> Up |
| `IMAGE_ICON_TO_BG` | `icon_bg.png` | `BG` | Counting -> Back |
| `IMAGE_ICON_DETAILS` | `icon_details.png` | `...` | Counting -> Down |
| `IMAGE_ICON_REPEAT_ENABLE` | `icon_rep_en.png` | `Rep` | Counting -> Long Up |
| `IMAGE_ICON_PLUS_20_REP` | `icon_plus_20_rep.png` | `+20` | EditRepeat -> Up |
| `IMAGE_ICON_PLUS_5_REP` | `icon_plus_5_rep.png` | `+5` | EditRepeat -> Select |
| `IMAGE_ICON_PLUS_1_REP` | `icon_plus_1_rep.png` | `+1` | EditRepeat -> Down |
| `IMAGE_ICON_RESET_COUNT` | `icon_rst_cnt.png` | `0` | EditRepeat -> Back |
| `IMAGE_ICON_DIRECTION` | `icon_direction.png` | `<>` | New/EditSec -> Long Up |

*Note: Existing icons `IMAGE_PLAY_ICON`, `IMAGE_PAUSE_ICON`, `IMAGE_SILENCE_ICON`, `IMAGE_SNOOZE_ICON`, `IMAGE_REPEAT_ICON` will be reused.*

## Architectural Changes

### 1. `drawing.c` / `drawing.h`
- **Asset Loading:** The current `drawing_initialize` loads specific bitmaps. This needs to be scalable.
    - *Decision:* Due to memory constraints on Pebble (especially Aplite), we should only load the icons required for the current state, or use a lazy-loading helper. However, for "QuickTimer" on Basalt+, we likely have enough heap for 20 small bitmaps. If memory becomes an issue, we will refactor to load/unload on mode change. For now, **load all on init** for simplicity, or add a helper `get_icon_for_id(uint32_t id)` that caches.
- **Drawing Logic:**
    - Create a helper function: `void prv_draw_action_icons(GContext *ctx, GRect bounds)` inside `drawing.c`.
    - This function will switch on `main_get_control_mode()` and `timer_state` to decide which icons to draw at which positions.
    - Positions should be defined as constants relative to the screen bounds (likely matching `button-icon-tests.md` regions).

### 2. `appinfo.json`
- Must be updated to include all new resources.

## Implementation Plan

### Phase 1: Assets & Configuration
- [ ] **Create Asset Generator Script**: Create `tools/generate_placeholder_icons.py`.
    - Uses `PIL` (Pillow).
    - Generates 25x25 and 15x15 PNGs.
    - Draws simple text or shapes (white on transparent).
- [ ] **Generate Icons**: Run the script to populate `resources/images/`.
- [ ] **Update appinfo.json**: Add all new files to the resources list.

### Phase 2: Drawing Infrastructure
- [ ] **Update `drawing.c` structs**: Add fields to `drawing_data` for the new bitmaps (or an array/hashmap if cleaner, but explicit pointers are fine for C).
- [ ] **Load/Unload Resources**: Update `drawing_initialize` and `drawing_terminate` to handle the new assets.
- [ ] **Create Drawing Helper**: Implement `prv_draw_action_icons` skeleton in `drawing.c` and call it from `drawing_render`.

### Phase 3: Implementation by State (Iterative)
*Implement the logic for each state and verify with tests.*

- [ ] **ControlModeNew**: Implement Back, Up, Select, Down, Long Up, Long Select, Long Down.
    - Verify: `pytest test/functional/test_button_icons.py -k "test_new_"`
- [ ] **ControlModeEditSec**: Implement Back, Up, Select, Down.
    - Verify: `pytest test/functional/test_button_icons.py -k "test_editsec_"`
- [ ] **ControlModeCounting (Running)**: Implement Back, Up, Down, Long Up, Long Select, Long Down.
    - Verify: `pytest test/functional/test_button_icons.py -k "test_counting_"`
- [ ] **ControlModeCounting (Paused)**: Implement Select (Play).
    - Verify: `pytest test/functional/test_button_icons.py -k "test_paused_"`
- [ ] **Chrono Mode**: Implement Select (Pause/Play), Long Select (Reset).
    - Verify: `pytest test/functional/test_button_icons.py -k "test_chrono_"`
- [ ] **EditRepeat**: Implement Back, Up, Select, Down.
    - Verify: `pytest test/functional/test_button_icons.py -k "test_editrepeat_"`

## Verification
- **Test Command**: `python -m pytest test/functional/test_button_icons.py`
- **Success Criteria**: All tests pass (no `xfail` remaining).

## Dependencies
- `ralph/specs/button-icon-tests.md`
- `test/functional/test_button_icons.py`
