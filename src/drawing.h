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
