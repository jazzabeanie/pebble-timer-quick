//! @file main.c
//! @brief Main logic for QuickTimer
//!
//! Contains the higher level logic code
//!
//! @author Eric D. Phillips
//! @date August 27, 2015
//! @bugs No known bugs

#pragma once
#include <pebble.h>

#define BUTTON_HOLD_RESET_MS 750
#define REDUCE_SCREEN_UPDATES 1

// Current control mode
typedef enum {
  ControlModeNew,
  ControlModeEditHr,
  ControlModeEditMin,
  ControlModeEditSec,
  ControlModeCounting,
  ControlModeEditRepeat
} ControlMode;

//! Get the current control mode of the app
//! @return The current ControlMode
ControlMode main_get_control_mode(void);

//! Get whether the app is currently editing an existing timer
//! @return True if editing an existing timer, false otherwise
bool main_is_editing_existing_timer(void);

//! Get whether the user has interacted with the app recently
//! @return True if the interaction timeout has not expired
bool main_is_interaction_active(void);

//! Get the timestamp of the last user interaction
//! @return The timestamp in milliseconds
uint64_t main_get_last_interaction_time(void);

//! Get whether the last interaction was a down button press
//! @return True if the last interaction was a down button press
bool main_is_last_interaction_down(void);

//! Get whether the app is in reverse direction mode
//! @return True if decrementing instead of incrementing
bool main_is_reverse_direction(void);

//! Get whether the backlight is currently on
//! @return True if the backlight is on
bool main_is_backlight_on(void);

//! Set the current control mode (used by Timer List window on timer selection)
void main_set_control_mode(ControlMode mode);

//! Reset the new-expire timer so the user gets a full 3 seconds in edit mode
void main_reset_new_expire_timer(void);

//! Force a redraw of the main window layer
void main_force_redraw(void);

//! Get whether the no-phone-connected feedback icon is currently being shown
//! @return True while the disconnected-rename feedback icon is on screen
bool main_is_showing_no_phone(void);

//! Get the warning message to draw instead of the timer view, if any.
//! Non-NULL while the slot-limit/no-free-slot warning overlay is active, and
//! during the "original" phase of the lap flash when the recorded lap left
//! 3 or fewer slots free.
//! @return The warning text, or NULL when no warning should be drawn
const char *main_get_warning_message(void);

//! Notify that a new timer slot was successfully created (not a lap).
//! Shows the approaching-limit warning (message + three short vibrations)
//! when 3 or fewer slots remain free.
void main_notify_timer_created(void);
