# Specification: Auto Direction Flip on Zero-Crossing

## Overview
When editing a timer (in `ControlModeNew` or `ControlModeEditSec`), if a button press causes the timer to cross zero — converting between chrono and countdown modes — the direction should automatically flip to forward. This ensures the button icons immediately show positive values, reflecting that the user is now adding time in the default direction for the new timer type.

### Motivation
Currently, when a user subtracts time past zero (e.g., from a 30-second chrono, subtracting 1 minute to get a 30-second countdown), the direction remains in reverse mode, showing negative icons. This is confusing because the user is now effectively in a new timer type where the "default" action is to add time, but the UI still shows minus signs.

The negative symbol should mean "the increment is not the default for this timer type." When the timer type changes, the default changes with it, so the direction must auto-reset to forward to stay consistent.

### Example Workflow
1. Timer is counting up (chrono) showing 0:30
2. User enters edit mode (Up button → ControlModeNew)
3. User toggles to reverse direction (long press Up) — icons show negative values
4. User presses Down (subtract 1 minute) — timer crosses zero
5. Timer converts to countdown showing 0:30 — **icons auto-flip to positive values**
6. User presses Down (add 1 minute) — countdown shows 1:30
7. The entire flow feels natural: subtract past zero, then continue adding in the new mode

## Keywords
auto-flip, direction flip, zero-crossing, reverse direction, is_reverse_direction, chrono to countdown, countdown to chrono, edit mode, ControlModeNew, ControlModeEditSec

## Requirements

### 1. Auto-flip on zero-crossing
When any button press in an edit mode causes the timer to change type (chrono ↔ countdown as determined by `timer_is_chrono()`), `is_reverse_direction` must be reset to `false` (forward).

### 2. Applies to all edit-mode buttons
The auto-flip must apply to every button that modifies the timer value in both edit modes:

**ControlModeNew (minutes editing):**
| Button | Forward | Reverse |
|--------|---------|---------|
| Up | +20 min | -20 min |
| Select | +5 min | -5 min |
| Down | +1 min | -1 min |
| Back | +60 min | -60 min |

**ControlModeEditSec (seconds editing):**
| Button | Forward | Reverse |
|--------|---------|---------|
| Up | +20 sec | -20 sec |
| Select | +5 sec | -5 sec |
| Down | +1 sec | -1 sec |
| Back | +60 sec | -60 sec |

### 3. Direction always resets to forward
The auto-flip always sets direction to forward (positive icons). It does NOT toggle — it always goes to forward regardless of which direction the zero was crossed from. This is because "forward" means "the default direction for the current timer type," and after a type change, the user is always starting fresh in the new type.

### 4. Immediate icon update
After the auto-flip, the button icons must reflect positive values on the same redraw as the button press that caused the zero-crossing. The user should see positive icons as soon as the display updates.

### 5. No effect when not crossing zero
If a button press in reverse mode subtracts time but does NOT cross zero (timer type remains the same), the direction remains in reverse. The auto-flip only triggers when `timer_is_chrono()` returns a different value before vs. after the button press.

## Implementation Notes

### Detection Approach
Check `timer_is_chrono()` before and after each timer modification in edit-mode button handlers. If the return value changed, a zero-crossing occurred:

```c
static void prv_check_zero_crossing_direction_flip(bool was_chrono) {
    if (was_chrono != timer_is_chrono()) {
        main_data.is_reverse_direction = false;
    }
}
```

### Button Handlers to Modify
Each of the following handlers needs the zero-crossing check. The pattern is the same for all — capture `timer_is_chrono()` before the modification, then call the helper after:

**In ControlModeNew:**
- `prv_up_single_click_handler` (when `control_mode == ControlModeNew`)
- `prv_down_single_click_handler` (when `control_mode == ControlModeNew`)
- `prv_select_single_click_handler` (when `control_mode == ControlModeNew`)
- `prv_back_single_click_handler` (when `control_mode == ControlModeNew`)

**In ControlModeEditSec:**
- `prv_up_single_click_handler` (when `control_mode == ControlModeEditSec`)
- `prv_down_single_click_handler` (when `control_mode == ControlModeEditSec`)
- `prv_select_single_click_handler` (when `control_mode == ControlModeEditSec`)
- `prv_back_single_click_handler` (when `control_mode == ControlModeEditSec`)

### Pattern for Each Handler
```c
// In each edit-mode button handler:

// Before the timer modification:
bool was_chrono = timer_is_chrono();

// ... existing timer modification code (timer_increment, timer_increment_chrono, etc.) ...

// After the modification:
prv_check_zero_crossing_direction_flip(was_chrono);
```

### Verification
After implementing, remove `@pytest.mark.xfail` markers from spec #21 tests (Tests 3–7 in `test/functional/test_edit_timer_direction.py`). All tests should pass.

## Dependencies
- **edit-timer-direction-tests.md** (spec #21): Tests must be implemented first (TDD approach)
- **stopwatch-subtraction.md** (spec #11): Zero-crossing timer math must work correctly
- **directional-icons.md** (spec #10): Direction toggle and icon display system

## Status
**Not Started**

## Tests
**NA** (Tests defined in spec #21)
