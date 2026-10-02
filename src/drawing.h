//! @file drawing.h
//! @brief Main drawing code
//!
//! Contains all the drawing code for this app.
//!
//! @author Eric D. Phillips
//! @date August 29, 2015
//! @bugs No known bugs

#pragma once
#include <pebble.h>

// The button hint icons (the small icons at the screen edges that show what
// each button does, and the icons shown during an alarm). Aplite has about
// 2KB of heap: its PNG decoder cannot load most of the icons, and the icon
// code takes about 2KB of the 24KB app region that the alarm-delivery code
// needs. So aplite has no button hint icons. The alarm icon of the Timer List
// is not part of this feature and stays on aplite.
#ifndef PBL_PLATFORM_APLITE
  #define BUTTON_ICONS_FEATURE 1
#else
  #define BUTTON_ICONS_FEATURE 0
#endif

//! Create bounce animation for focus layer
//! @param upward Animate the bounce upward or downward
void drawing_start_bounce_animation(bool upward);

//! Create reset animation for focus layer
void drawing_start_reset_animation(void);

//! Override which timer slot the render path reads (used by the lap flash).
//! While set (>= 0) the render path draws that slot instead of the active
//! slot; button handlers and all non-drawing code keep using the active slot.
//! @param slot The slot index to render, or -1 to clear the override
void drawing_set_slot_override(int8_t slot);

//! Get the current render slot override
//! @return The overridden slot index, or -1 when no override is set
int8_t drawing_get_slot_override(void);

//! Freeze the display of the running active timer at a given time (used from
//! Select press-down on a running lap stopwatch until the press resolves).
//! While set, the render path draws the timer as it was at that time, with
//! the millisecond field. The timer itself is not changed. A lap flash frame
//! (slot override) and a paused timer are drawn as usual.
//! @param at_ms The epoch time (ms) to show the timer at
void drawing_set_freeze_ms(int64_t at_ms);

//! End the display freeze
void drawing_clear_freeze(void);

//! Render everything to the screen
//! @param layer The layer being rendered onto
//! @param ctx The layer's drawing context
void drawing_render(Layer *layer, GContext *ctx);

//! Update the drawing states and recalculate everythings positions
void drawing_update(void);

//! Initialize the singleton drawing data
//! @param layer The layer which the drawing code can force to refresh, for animations
void drawing_initialize(Layer *layer);

//! Destroy the singleton drawing data
void drawing_terminate(void);
