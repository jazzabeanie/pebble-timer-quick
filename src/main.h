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
  ControlModeCounting
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
