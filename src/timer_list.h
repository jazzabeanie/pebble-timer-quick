#pragma once
#include <pebble.h>

//! Push the Timer List window onto the window stack
void timer_list_window_push(void);

//! Get whether the Timer List is the top window. While it is, the list holds
//! every alarm, and the main window does not check or start one.
//! @return True from the push until the list starts to close
bool timer_list_is_on_top(void);
