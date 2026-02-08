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
After implementing, remove `@pytest.mark.xfail` markers from spec #21 tests (Tests 3–6 in `test/functional/test_edit_timer_direction.py`). All tests should pass.

## Dependencies
- **edit-timer-direction-tests.md** (spec #21): Tests must be implemented first (TDD approach)
- **stopwatch-subtraction.md** (spec #11): Zero-crossing timer math must work correctly
- **directional-icons.md** (spec #10): Direction toggle and icon display system

## Progress

### 2026-02-09: Implementation Complete
1. Added `prv_check_zero_crossing_direction_flip(bool was_chrono)` helper to `src/main.c`
2. Added `was_chrono`/`prv_check_zero_crossing_direction_flip()` calls to all 8 edit-mode button handlers (4 in ControlModeNew, 4 in ControlModeEditSec)
3. **Additional change: `prv_update_timer` routing** — Removed `control_mode != ControlModeEditSec` exclusion from the chrono increment routing. After a zero-crossing, the timer type changes, so `prv_update_timer` must correctly route through `timer_increment_chrono()` for chronos in EditSec too. The routing condition is now: `is_editing_existing_timer && base_length_ms == 0` → `timer_increment_chrono()`, else → `timer_increment()`
4. **Additional change: Zero-crossing routing state update** — `prv_check_zero_crossing_direction_flip` also updates `base_length_ms` and `is_editing_existing_timer` after a crossing so that `prv_update_timer` routes through the correct increment function on subsequent presses:
   - Crossing to chrono: `base_length_ms = 0`, `is_editing_existing_timer = true`
   - Crossing to countdown: `base_length_ms = timer_get_value_ms()`
5. Removed `@pytest.mark.xfail` markers from tests 3–6 in `test/functional/test_edit_timer_direction.py`
6. All 6 direction tests pass on basalt (2 type conversion + 4 auto-flip)
7. All 26 unit tests pass

## Status
**Completed**

## Tests
**Passing** (6 tests on basalt: 2 type conversion + 4 auto-flip)
