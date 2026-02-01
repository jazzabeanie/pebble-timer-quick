# Specification: Directional Button Icons

## Overview
This specification defines the requirements for updating the application's button icons to reflect the "reverse direction" state. Currently, the application allows users to toggle between adding and subtracting time (via a long press of the Up button), but the icons always display "+" (increment) indicators. This feature ensures the UI accurately reflects the active direction by displaying "-" (decrement) icons when reverse mode is active.

Additionally, this spec addresses a discrepancy in the "Edit Seconds" mode where the Back button adds 60 seconds (1 minute), but the icon displays "+30".

## Keywords
button icons, reverse direction, minus icons, UI feedback, state machine, drawing

## Goals
1.  **Visual Consistency**: Display "-" icons (e.g., `-20`, `-5`) when the user has toggled the timer into reverse/decrement mode.
2.  **Accuracy Fix**: Replace the incorrect `+30` icon for the Back button in Edit Seconds mode with a `+60` icon to match the actual logic (which adds 60 seconds).
3.  **Scope**: Apply these changes to both `ControlModeNew` (Hours/Minutes editing) and `ControlModeEditSec` (Seconds editing).

## Resources & Assets
New PNG assets must be generated. The naming convention should follow the existing pattern, adding `_minus` for decrement icons.

### Icon Dimensions
*   **Standard Action**: 25x25 pixels
*   **Small/Secondary**: 15x15 pixels

### Required Assets Table

| Resource ID | Filename (suggested) | Text/Symbol | Usage (Mode -> Button -> Direction) |
|---|---|---|---|
| `IMAGE_ICON_MINUS_1HR` | `icon_minus_1hr.png` | `-1h` | New -> Back -> Reverse |
| `IMAGE_ICON_MINUS_20MIN` | `icon_minus_20min.png` | `-20` | New -> Up -> Reverse |
| `IMAGE_ICON_MINUS_5MIN` | `icon_minus_5min.png` | `-5m` | New -> Select -> Reverse |
| `IMAGE_ICON_MINUS_1MIN` | `icon_minus_1min.png` | `-1m` | New -> Down -> Reverse |
| `IMAGE_ICON_PLUS_60SEC` | `icon_plus_60sec.png` | `+60` | EditSec -> Back -> Forward (Replaces `+30`) |
| `IMAGE_ICON_MINUS_60SEC` | `icon_minus_60sec.png` | `-60` | EditSec -> Back -> Reverse |
| `IMAGE_ICON_MINUS_20SEC` | `icon_minus_20sec.png` | `-20` | EditSec -> Up -> Reverse |
| `IMAGE_ICON_MINUS_5SEC` | `icon_minus_5sec.png` | `-5` | EditSec -> Select -> Reverse |
| `IMAGE_ICON_MINUS_1SEC` | `icon_minus_1sec.png` | `-1` | EditSec -> Down -> Reverse |

**Note**: The existing `IMAGE_ICON_DIRECTION` (`<>`) icon will remain unchanged and used for the Long-Press Up indicator to signify the *ability* to toggle direction.

## Architectural Changes

### 1. `src/main.c` / `src/main.h`
*   **Expose State**: The `is_reverse_direction` state is currently static/private in `main.c`. It must be exposed via a new public function in `main.h`:
    ```c
    bool main_is_reverse_direction(void);
    ```

### 2. `src/drawing.c`
*   **Asset Loading**: Update `drawing_initialize` to load the 9 new bitmaps.
*   **Drawing Logic**: Update `prv_draw_action_icons` to check `main_is_reverse_direction()`:
    *   If `false` (Forward): Draw existing `PLUS` icons (updating Back button in EditSec to use `PLUS_60SEC`).
    *   If `true` (Reverse): Draw the new `MINUS` icons.

## Implementation Steps
1.  **Generate Assets**: Create the 9 new PNG files in `resources/images/`.
2.  **Update Manifest**: Add the new resources to `appinfo.json`.
3.  **Expose State**: Implement `main_is_reverse_direction` in `src/main.c` and header.
4.  **Update Drawing**: Modify `src/drawing.c` to load new resources and implement the conditional drawing logic.
5.  **Clean Up**: Remove the unused `IMAGE_ICON_PLUS_30SEC` resource and variable if no longer needed.

## Verification & Testing
*   **Functional Tests**: Update or create new functional tests (e.g., `test/functional/test_directional_icons.py`) that:
    1.  Enter `ControlModeNew`.
    2.  Verify `+` icons are present.
    3.  Long-press Up to toggle direction.
    4.  Verify `-` icons are present via screenshot/pixel comparison.
    5.  Repeat for `ControlModeEditSec`.
    6.  Verify the Back button in `ControlModeEditSec` shows `+60` (Forward) and `-60` (Reverse).
*   **Reference Images**: Generate new reference masks for the minus icon states.

## Dependencies
*   `ralph/specs/button-icons.md` (Basis for current icon system)

## Progress

### 2026-02-01: Implementation Completed
All requirements have been implemented and verified:

1.  **Assets Created**: Generated 9 new PNG icon files:
    - `icon_minus_1hr.png`, `icon_minus_20min.png`, `icon_minus_5min.png`, `icon_minus_1min.png`
    - `icon_plus_60sec.png` (replaces +30), `icon_minus_60sec.png`
    - `icon_minus_20sec.png`, `icon_minus_5sec.png`, `icon_minus_1sec.png`

2.  **Manifest Updated**: Added all 9 new resources to `appinfo.json`.

3.  **State Exposed**: Implemented `main_is_reverse_direction()` in `src/main.c` and `src/main.h`.

4.  **Drawing Logic Updated**: Modified `src/drawing.c`:
    - Added 9 new `GBitmap` pointers to `drawing_data` struct
    - Updated `drawing_initialize()` to load new bitmaps
    - Updated `drawing_terminate()` to free new bitmaps
    - Refactored `prv_draw_action_icons()` to conditionally draw +/- icons based on `main_is_reverse_direction()`
    - Fixed EditSec Back button to use `+60` icon instead of `+30`

5.  **Functional Tests Created**: Added `test/functional/test_directional_icons.py` with 11 tests:
    - `TestNewModeForwardIcons`: Verifies icons exist in forward direction
    - `TestNewModeReverseIcons`: Verifies -1h, -20, -5m, -1m icons appear after toggle
    - `TestEditSecModeForwardIcons`: Verifies +60 fix and other icons
    - `TestEditSecModeReverseIcons`: Verifies -60, -20, -5, -1 icons appear after toggle

6.  **Tests Passing**: All 11 directional icon tests pass on basalt. All 23 unit tests pass. Existing button icon tests (17 tested) pass.

**Note**: The `IMAGE_ICON_PLUS_30SEC` resource was NOT removed as it may still be in use or needed for backward compatibility. This cleanup can be done in a future iteration if confirmed safe.
