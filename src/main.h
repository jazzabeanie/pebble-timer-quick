//! @file main.c
//! @brief Main logic for Timer++
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
