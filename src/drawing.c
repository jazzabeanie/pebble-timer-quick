// @file drawing.h
// @brief Main drawing code
//
// Contains all the drawing code for this app.
//
// @author Eric D. Phillips
// @date August 29, 2015
// @bugs No known bugs

#include <pebble.h>
#include "animation.h"
#include "main.h"
#include "text_render.h"
#include "timer.h"
#include "utility.h"

// Drawing constants
// Progress ring
#define CIRCLE_RADIUS 63
#define ANGLE_CHANGE_ANI_THRESHOLD 348
#define PROGRESS_ANI_DURATION 250
#define MAIN_TEXT_CIRCLE_RADIUS (CIRCLE_RADIUS - 7)
#define MAIN_TEXT_BOUNDS GRect(-MAIN_TEXT_CIRCLE_RADIUS, -MAIN_TEXT_CIRCLE_RADIUS / 2,\
 MAIN_TEXT_CIRCLE_RADIUS * 2, MAIN_TEXT_CIRCLE_RADIUS)
#define MAIN_TEXT_CIRCLE_RADIUS_EDIT (CIRCLE_RADIUS - 17)
#define MAIN_TEXT_BOUNDS_EDIT GRect(-MAIN_TEXT_CIRCLE_RADIUS_EDIT, \
 -MAIN_TEXT_CIRCLE_RADIUS_EDIT / 2, MAIN_TEXT_CIRCLE_RADIUS_EDIT * 2, MAIN_TEXT_CIRCLE_RADIUS_EDIT)
// Main Text
#define TEXT_FIELD_COUNT 6
#define TEXT_FIELD_EDIT_SPACING 7
#define TEXT_FIELD_ANI_DURATION 140
// Focus Layer
#define FOCUS_FIELD_BORDER 5
#define FOCUS_FIELD_SHRINK_INSET 3
#define FOCUS_FIELD_SHRINK_DURATION 80
#define FOCUS_FIELD_ANI_DURATION 150
#define FOCUS_BOUNCE_ANI_HEIGHT 8
#define FOCUS_BOUNCE_ANI_DURATION 70
#define FOCUS_BOUNCE_ANI_SETTLE_DURATION 140
// Header Text
#define HEADER_Y_OFFSET 5
#define FOOTER_Y_OFFSET -39

// Main drawing state description, used to determine changes in state
typedef struct {
  ControlMode   control_mode;   //< The timer control mode at that state
  uint8_t       hr_digits;      //< The number of digits used by the hours
  uint8_t       min_digits;     //< The number of digits used by the minutes
} DrawState;

// Main data
static struct {
  Layer       *layer;             //< The main layer being drawn on, used to force a refresh
  int32_t     progress_angle;     //< The current angle of the progress ring
  DrawState   draw_state;         //< An arbitrary description of the main drawing state
  GRect       text_fields[TEXT_FIELD_COUNT];      //< The number of text fields (hr : min : sec)
  GRect       focus_field;        //< The selection field layer
  GColor      fore_color;         //< Color of text
  GColor      mid_color;          //< Color of center
  GColor      ring_color;         //< Color of ring
  GColor      back_color;         //< Color behind ring
  GBitmap     *reset_icon;        //< The reset icon to show when the timer is vibrating
  GBitmap     *pause_icon;        //< The pause icon to show when the timer is vibrating
  GBitmap     *silence_icon;      //< The silence icon to show when the timer is vibrating
  GBitmap     *snooze_icon;       //< The snooze icon to show when the timer is vibrating
  // Button action icons
  GBitmap     *icon_plus_1hr;
  GBitmap     *icon_plus_20min;
  GBitmap     *icon_plus_5min;
  GBitmap     *icon_plus_1min;
  GBitmap     *icon_plus_30sec;
  GBitmap     *icon_plus_20sec;
  GBitmap     *icon_plus_5sec;
  GBitmap     *icon_plus_1sec;
  GBitmap     *icon_reset;
  GBitmap     *icon_quit;
  GBitmap     *icon_edit;
  GBitmap     *icon_to_bg;
  GBitmap     *icon_details;
  GBitmap     *icon_repeat_enable;
  GBitmap     *icon_plus_20_rep;
  GBitmap     *icon_plus_5_rep;
  GBitmap     *icon_plus_1_rep;
  GBitmap     *icon_reset_count;
  GBitmap     *icon_direction;
  GBitmap     *play_icon;
} drawing_data;


////////////////////////////////////////////////////////////////////////////////////////////////////
// Sub Texts
//

// Draw header text
static void prv_render_header_text(GContext *ctx, GRect bounds) {
  // calculate bounds
  bounds.origin = grect_center_point(&bounds);
  bounds.origin.x -= CIRCLE_RADIUS;
  bounds.origin.y -= (CIRCLE_RADIUS - HEADER_Y_OFFSET);
  bounds.size.w = CIRCLE_RADIUS * 2;
  bounds.size.h = CIRCLE_RADIUS / 2;
  // draw text
  static char s_time_buffer[16]; // Buffer for formatted time
  char *buff;
  if (main_get_control_mode() == ControlModeNew || main_get_control_mode() == ControlModeEditSec) {
    if (main_is_editing_existing_timer()) {
      buff = "Edit";
    } else {
      buff = "New";
    }
  } else if (timer_is_chrono()) {
    // Calculate and format the total timer length
    int64_t total_ms = timer_get_length_ms();
    int64_t total_seconds = total_ms / 1000;
    int hours = total_seconds / 3600;
    int minutes = (total_seconds % 3600) / 60;
    int seconds = total_seconds % 60;

    if (hours > 0) {
        snprintf(s_time_buffer, sizeof(s_time_buffer), "%02d:%02d:%02d-->", hours, minutes, seconds);
    } else {
        snprintf(s_time_buffer, sizeof(s_time_buffer), "%02d:%02d-->", minutes, seconds);
    }
    buff = s_time_buffer;
  } else {
    // Calculate and format the total timer length
    int64_t total_ms = timer_get_length_ms();
    int64_t total_seconds = total_ms / 1000;
    int hours = total_seconds / 3600;
    int minutes = (total_seconds % 3600) / 60;
    int seconds = total_seconds % 60;

    if (hours > 0) {
        snprintf(s_time_buffer, sizeof(s_time_buffer), "%02d:%02d:%02d", hours, minutes, seconds);
    } else {
        snprintf(s_time_buffer, sizeof(s_time_buffer), "%02d:%02d", minutes, seconds);
    }
    buff = s_time_buffer;
  }
  graphics_draw_text(ctx, buff, fonts_get_system_font(FONT_KEY_GOTHIC_24_BOLD), bounds,
    GTextOverflowModeFill, GTextAlignmentCenter, NULL);
}

// Draw footer text
static void prv_render_footer_text(GContext *ctx, GRect bounds) {
  // calculate bounds
  bounds.origin = grect_center_point(&bounds);
  bounds.origin.x -= CIRCLE_RADIUS;
  bounds.origin.y += CIRCLE_RADIUS + FOOTER_Y_OFFSET;
  bounds.size.w = CIRCLE_RADIUS * 2;
  bounds.size.h = CIRCLE_RADIUS / 2;
  // calculate text
  char buff[10];
  // in timer mode, get time
  time_t end_time = epoch() / MSEC_IN_SEC;
  if (main_get_control_mode() != ControlModeCounting && !timer_is_chrono()) {
    end_time += timer_get_value_ms() / MSEC_IN_SEC;
  }
  // format to readable time
  struct tm end_tm = *localtime(&end_time);
  strftime(buff, sizeof(buff), clock_is_24h_style() ? "%k:%M" : "%l:%M", &end_tm);
  // draw text
  graphics_draw_text(ctx, buff, fonts_get_system_font(FONT_KEY_GOTHIC_28_BOLD), bounds,
    GTextOverflowModeFill, GTextAlignmentCenter, NULL);
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Main Text
//

// Update main text drawing state
static void prv_main_text_update_state(Layer *layer) {
  // get properties
  GRect bounds = layer_get_bounds(layer);
  // calculate time parts
  uint16_t hr, min, sec;
  timer_get_time_parts(&hr, &min, &sec);
  // convert to strings
  char buff[TEXT_FIELD_COUNT][4] = {{'\0'}};
  if (main_get_control_mode() == ControlModeNew || main_get_control_mode() == ControlModeEditSec) {
    snprintf(buff[0], sizeof(buff[0]), "-");
  }
  if (hr) {
    snprintf(buff[1], sizeof(buff[1]), "%d", hr);
  }
  snprintf(buff[2], sizeof(buff[2]), "%s", hr ? ":" : "\0");
  snprintf(buff[3], sizeof(buff[3]), hr ? "%02d" : "%d", min);
  snprintf(buff[4], sizeof(buff[4]), ":");

#if REDUCE_SCREEN_UPDATES
  int64_t val = timer_get_value_ms();
  if (main_is_interaction_active() || main_is_last_interaction_down()) {
     snprintf(buff[5], sizeof(buff[5]), "%02d", sec);
  } else if (val > 5 * MSEC_IN_MIN) {
     snprintf(buff[5], sizeof(buff[5]), "__");
  } else if (val >= 30 * MSEC_IN_SEC) {
     snprintf(buff[5], sizeof(buff[5]), "%d_", sec / 10);
  } else {
     snprintf(buff[5], sizeof(buff[5]), "%02d", sec);
  }
#else
  snprintf(buff[5], sizeof(buff[5]), "%02d", sec);
#endif

  // APP_LOG(APP_LOG_LEVEL_DEBUG, "Render Mode: %d | Buffers: [%s][%s][%s][%s][%s][%s] (prv_main_text_update_state)",
  //         main_get_control_mode(),
  //         buff[0], buff[1], buff[2], buff[3], buff[4], buff[5]);

  // calculate new sizes for all text elements
  char tot_buff[12];
  snprintf(tot_buff, sizeof(tot_buff), "%s%s%s%s%s%s", buff[0], buff[1], buff[2], buff[3], buff[4], buff[5]);
  
  // APP_LOG(APP_LOG_LEVEL_DEBUG, "tot_buff: %s (prv_main_text_update_state)", tot_buff);

  uint16_t font_size = text_render_get_max_font_size(tot_buff, MAIN_TEXT_BOUNDS);
  // APP_LOG(APP_LOG_LEVEL_DEBUG, "font_size: %u (prv_main_text_update_state)", font_size);

  // calculate new size for each text element
  GRect total_bounds = GRectZero;
  GRect field_bounds[TEXT_FIELD_COUNT];
  for (uint8_t ii = 0; ii < TEXT_FIELD_COUNT; ii++) {
    field_bounds[ii] = text_render_get_content_bounds(buff[ii], font_size);
    total_bounds.size.w += field_bounds[ii].size.w;
  }
  total_bounds.size.h = field_bounds[TEXT_FIELD_COUNT - 1].size.h;
  total_bounds.origin.x = (bounds.size.w - total_bounds.size.w) / 2;
  total_bounds.origin.y = (bounds.size.h - total_bounds.size.h) / 2;
  // calculate positions for all text elements
  field_bounds[0].origin = total_bounds.origin;
  for (uint8_t ii = 0; ii < TEXT_FIELD_COUNT - 1; ii++) {
    field_bounds[ii + 1].origin.x = field_bounds[ii].origin.x + field_bounds[ii].size.w;
    field_bounds[ii + 1].origin.y = total_bounds.origin.y;
  }
  // animate to new positions
  for (uint8_t ii = 0; ii < TEXT_FIELD_COUNT; ii++) {
    animation_grect_start(&drawing_data.text_fields[ii], field_bounds[ii],
      TEXT_FIELD_ANI_DURATION, 0, CurveSinEaseOut);
  }

}

// Draw main text onto drawing context
static void prv_render_main_text(GContext *ctx, GRect bounds) {
  // get time parts
  uint16_t hr, min, sec;
  timer_get_time_parts(&hr, &min, &sec);
  // convert to strings
  char buff[TEXT_FIELD_COUNT][4] = {{'\0'}};
  if ((main_get_control_mode() == ControlModeNew || main_get_control_mode() == ControlModeEditSec) && timer_data.length_ms == 0) {
    snprintf(buff[0], sizeof(buff[0]), "-");
  }
  if (hr) {
    snprintf(buff[1], sizeof(buff[1]), "%d", hr);
  }
  snprintf(buff[2], sizeof(buff[2]), "%s", hr ? ":" : "\0");
  snprintf(buff[3], sizeof(buff[3]), hr ? "%02d" : "%d", min);
  snprintf(buff[4], sizeof(buff[4]), ":");

#if REDUCE_SCREEN_UPDATES
  int64_t val = timer_get_value_ms();
  if (main_is_interaction_active() || main_is_last_interaction_down()) {
     snprintf(buff[5], sizeof(buff[5]), "%02d", sec);
  } else if (val > 5 * MSEC_IN_MIN) {
     snprintf(buff[5], sizeof(buff[5]), "__");
  } else if (val >= 30 * MSEC_IN_SEC) {
     snprintf(buff[5], sizeof(buff[5]), "%d_", sec / 10);
  } else {
     snprintf(buff[5], sizeof(buff[5]), "%02d", sec);
  }
#else
  snprintf(buff[5], sizeof(buff[5]), "%02d", sec);
#endif

  // APP_LOG(APP_LOG_LEVEL_DEBUG, "Render Mode: %d | Buffers: [%s][%s][%s][%s][%s][%s]",
  //         main_get_control_mode(),
  //         buff[0], buff[1], buff[2], buff[3], buff[4], buff[5]);

  // draw the main text elements in their respective bounds
  for (uint8_t ii = 0; ii < TEXT_FIELD_COUNT; ii++) {
    text_render_draw_scalable_text(ctx, buff[ii], drawing_data.text_fields[ii]);
  }
}

// Animation update callback
static void prv_animation_update_callback(void) {
  // refresh
  layer_mark_dirty(drawing_data.layer);
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Progress Ring
//

// Draw progress ring
static void prv_render_progress_ring(GContext *ctx, GRect bounds) {
  // calculate ring bounds size
  int32_t gr_angle = atan2_lookup(bounds.size.h, bounds.size.w);
  int32_t radius = (bounds.size.h / 2) * TRIG_MAX_RATIO / sin_lookup(gr_angle);
  bounds.origin.x += bounds.size.w / 2 - radius;
  bounds.origin.y += bounds.size.h / 2 - radius;
  bounds.size.w = bounds.size.h = radius * 2;
  // draw ring on context
  int32_t angle_1 = drawing_data.progress_angle;
  int32_t angle_2 = TRIG_MAX_ANGLE;
  graphics_context_set_fill_color(ctx, drawing_data.back_color);
  graphics_fill_radial(ctx, bounds, GOvalScaleModeFillCircle, radius, angle_1, angle_2);
}

// Update the progress ring position based on the current and total values
static void prv_progress_ring_update(void) {
  // calculate new angle
  int32_t new_angle = TRIG_MAX_ANGLE * timer_get_value_ms() / timer_get_length_ms();
  if (timer_is_chrono()) {
    new_angle = TRIG_MAX_ANGLE * (timer_get_value_ms() % MSEC_IN_MIN) / MSEC_IN_MIN;
  }
  // check if large angle and animate
  animation_stop(&drawing_data.progress_angle);
#if REDUCE_SCREEN_UPDATES
  bool should_animate = false;
  // Only animate if we are updating frequently (less than 30 seconds remaining)
  if (timer_get_value_ms() < 30 * MSEC_IN_SEC || main_is_interaction_active() || main_is_last_interaction_down()) {
    should_animate = true;
  }
#else
  bool should_animate = true;
#endif

  if (timer_is_paused()) {
    should_animate = false;
  }

  if (should_animate && abs(new_angle - drawing_data.progress_angle) >= ANGLE_CHANGE_ANI_THRESHOLD) {
    animation_int32_start(&drawing_data.progress_angle, new_angle, PROGRESS_ANI_DURATION, 0,
      CurveSinEaseOut);
  } else {
    drawing_data.progress_angle = new_angle;
  }
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Drawing State Changes
//

// Compare two different TextStates, return true if conditions are met for a refresh
static bool prv_text_state_compare(DrawState text_state_1, DrawState text_state_2) {
  return text_state_1.control_mode == text_state_2.control_mode && // if control modes are different
          (text_state_1.control_mode == ControlModeCounting &&     // if in counting mode
           text_state_1.hr_digits == text_state_2.hr_digits &&
           text_state_1.min_digits == text_state_2.min_digits) &&
          text_state_2.hr_digits < 3; // on first start hr is set to 99 to force refresh
}

// Create a state description
static DrawState prv_draw_state_create(void) {
  // get states
  uint16_t hr, min, sec;
  timer_get_time_parts(&hr, &min, &sec);
  return (DrawState) {
    .control_mode = main_get_control_mode(),
    .hr_digits = (uint8_t)(hr > 0) + (uint8_t)(hr > 9) + (uint8_t)(hr > 99),
    .min_digits = (uint8_t)(min > 0) + (uint8_t)(min > 9),
  };
}

// Check for draw state changes and update drawing accordingly
static void prv_update_draw_state(Layer *layer) {
  // check for changes in the states of things
  DrawState cur_draw_state = prv_draw_state_create();
  if (!prv_text_state_compare(cur_draw_state, drawing_data.draw_state)) {
    drawing_data.draw_state = cur_draw_state;
    // update text state
    prv_main_text_update_state(layer);
  }
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Button Action Icons
//

// Icon position constants (basalt 144x168)
#define ICON_BACK_X 5
#define ICON_BACK_Y 10
#define ICON_UP_X 114
#define ICON_UP_Y 10
#define ICON_SELECT_X 127
#define ICON_SELECT_Y 76
#define ICON_DOWN_X 114
#define ICON_DOWN_Y 133
#define ICON_STANDARD_SIZE 25
#define ICON_SMALL_SIZE 15
// Long press sub-icon positions (top and bottom of screen)
#define LONG_UP_X 97
#define LONG_UP_Y 10
#define LONG_SELECT_X 110
#define LONG_SELECT_Y 76
#define LONG_DOWN_X 97
#define LONG_DOWN_Y 145

// Draw a bitmap icon at a given position
static void prv_draw_icon(GContext *ctx, GBitmap *icon, int16_t x, int16_t y, int16_t w, int16_t h) {
  if (icon) {
    graphics_draw_bitmap_in_rect(ctx, icon, GRect(x, y, w, h));
  }
}

// Draw action icons based on the current app state
static void prv_draw_action_icons(GContext *ctx, GRect bounds) {
  graphics_context_set_compositing_mode(ctx, GCompOpSet);

  ControlMode mode = main_get_control_mode();
  bool is_paused = timer_is_paused();
  bool is_chrono = timer_is_chrono();
  bool is_vibrating = timer_is_vibrating();

  if (is_vibrating) {
    // Alarm state icons are handled separately in drawing_render
    return;
  }

  if (mode == ControlModeNew || mode == ControlModeEditSec) {
    // New/EditSec mode: show increment icons
    if (mode == ControlModeNew) {
      prv_draw_icon(ctx, drawing_data.icon_plus_1hr, ICON_BACK_X, ICON_BACK_Y,
                    ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
      prv_draw_icon(ctx, drawing_data.icon_plus_20min, ICON_UP_X, ICON_UP_Y,
                    ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
      prv_draw_icon(ctx, drawing_data.icon_plus_5min, ICON_SELECT_X, ICON_SELECT_Y,
                    ICON_SMALL_SIZE, ICON_SMALL_SIZE);
      prv_draw_icon(ctx, drawing_data.icon_plus_1min, ICON_DOWN_X, ICON_DOWN_Y,
                    ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    } else {
      // EditSec
      prv_draw_icon(ctx, drawing_data.icon_plus_30sec, ICON_BACK_X, ICON_BACK_Y,
                    ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
      prv_draw_icon(ctx, drawing_data.icon_plus_20sec, ICON_UP_X, ICON_UP_Y,
                    ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
      prv_draw_icon(ctx, drawing_data.icon_plus_5sec, ICON_SELECT_X, ICON_SELECT_Y,
                    ICON_SMALL_SIZE, ICON_SMALL_SIZE);
      prv_draw_icon(ctx, drawing_data.icon_plus_1sec, ICON_DOWN_X, ICON_DOWN_Y,
                    ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    }
    // Long press icons for New/EditSec
    prv_draw_icon(ctx, drawing_data.icon_direction, LONG_UP_X, LONG_UP_Y,
                  ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    // TODO: overlaps the display and a new solution is needed
    // prv_draw_icon(ctx, drawing_data.icon_reset, LONG_SELECT_X, LONG_SELECT_Y,
    //               ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    prv_draw_icon(ctx, drawing_data.icon_quit, LONG_DOWN_X, LONG_DOWN_Y,
                  ICON_SMALL_SIZE, ICON_SMALL_SIZE);
  } else if (mode == ControlModeCounting) {
    // Counting mode icons
    prv_draw_icon(ctx, drawing_data.icon_to_bg, ICON_BACK_X, ICON_BACK_Y,
                  ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    prv_draw_icon(ctx, drawing_data.icon_edit, ICON_UP_X, ICON_UP_Y,
                  ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    if (is_paused) {
      prv_draw_icon(ctx, drawing_data.play_icon, ICON_SELECT_X, ICON_SELECT_Y,
                    ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    } else {
      prv_draw_icon(ctx, drawing_data.pause_icon, ICON_SELECT_X, ICON_SELECT_Y,
                    ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    }
    prv_draw_icon(ctx, drawing_data.icon_details, ICON_DOWN_X, ICON_DOWN_Y,
                  ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    // Long press icons
    if (!is_chrono) {
      prv_draw_icon(ctx, drawing_data.icon_repeat_enable, LONG_UP_X, LONG_UP_Y,
                    ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    }
    // TODO: overlaps the display and a new solution is needed
    // prv_draw_icon(ctx, drawing_data.icon_reset, LONG_SELECT_X, LONG_SELECT_Y,
    //               ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    prv_draw_icon(ctx, drawing_data.icon_quit, LONG_DOWN_X, LONG_DOWN_Y,
                  ICON_SMALL_SIZE, ICON_SMALL_SIZE);
  } else if (mode == ControlModeEditRepeat) {
    // EditRepeat mode icons
    prv_draw_icon(ctx, drawing_data.icon_reset_count, ICON_BACK_X, ICON_BACK_Y,
                  ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    prv_draw_icon(ctx, drawing_data.icon_plus_20_rep, ICON_UP_X, ICON_UP_Y,
                  ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
    prv_draw_icon(ctx, drawing_data.icon_plus_5_rep, ICON_SELECT_X, ICON_SELECT_Y,
                  ICON_SMALL_SIZE, ICON_SMALL_SIZE);
    prv_draw_icon(ctx, drawing_data.icon_plus_1_rep, ICON_DOWN_X, ICON_DOWN_Y,
                  ICON_STANDARD_SIZE, ICON_STANDARD_SIZE);
  }
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// API Implementation
//

// Create reset animation for focus layer
void drawing_start_reset_animation(void) {
  // create shrunken focus bounds and animate to new bounds
  GRect focus_to_bounds;
  focus_to_bounds = grect_inset(drawing_data.focus_field,
    GEdgeInsets1(FOCUS_FIELD_SHRINK_INSET));
  // shrinking animation
  animation_grect_start(&drawing_data.focus_field, focus_to_bounds,
    FOCUS_FIELD_SHRINK_DURATION, 0, CurveLinear);
  // return animation back to original size
  animation_grect_start(&drawing_data.focus_field, drawing_data.focus_field,
    FOCUS_FIELD_SHRINK_DURATION, BUTTON_HOLD_RESET_MS, CurveLinear);
}

// Render everything to the screen
void drawing_render(Layer *layer, GContext *ctx) {
  // get properties
  GRect bounds = layer_get_bounds(layer);
  // draw background
  // this is actually the ring, which is then covered up with the background
  graphics_context_set_fill_color(ctx, drawing_data.ring_color);
#ifdef PBL_BW
  graphics_fill_rect_grey(ctx, bounds);
#else
  graphics_fill_rect(ctx, bounds, 0, GCornerNone);
#endif
  prv_render_progress_ring(ctx, bounds);
  // draw main circle
  graphics_context_set_fill_color(ctx, drawing_data.mid_color);
  graphics_fill_circle(ctx, grect_center_point(&bounds), CIRCLE_RADIUS);
  // draw main text (drawn as filled and stroked path)
  graphics_context_set_stroke_color(ctx, drawing_data.fore_color);
  graphics_context_set_fill_color(ctx, drawing_data.fore_color);
  prv_render_main_text(ctx, bounds);
  // draw header and footer text
  graphics_context_set_text_color(ctx, drawing_data.fore_color);
  prv_render_header_text(ctx, bounds);
  prv_render_footer_text(ctx, bounds);

  // Draw button action icons
  prv_draw_action_icons(ctx, bounds);

  // Draw repeat counter
  if (timer_data.is_repeating) {
    bool show = false;
    if (main_get_control_mode() == ControlModeEditRepeat) {
      show = true;
      // flash the indicator
      uint64_t delta = epoch() - main_get_last_interaction_time();
      if ((delta % 1000) >= 500) {
        show = false;
      }
    } else if (timer_data.repeat_count > 1) {
      show = true;
    }

    if (show) {
      char s_repeat_buffer[8];
      if (timer_data.repeat_count == 0) {
        snprintf(s_repeat_buffer, sizeof(s_repeat_buffer), "_x");
      } else {
        snprintf(s_repeat_buffer, sizeof(s_repeat_buffer), "%dx", timer_data.repeat_count);
      }
      GRect repeat_bounds = GRect(bounds.size.w - 50, 0, 50, 30);
      graphics_context_set_text_color(ctx, GColorWhite);
      graphics_draw_text(ctx, s_repeat_buffer, fonts_get_system_font(FONT_KEY_GOTHIC_24_BOLD),
        repeat_bounds, GTextOverflowModeFill, GTextAlignmentRight, NULL);
      graphics_context_set_text_color(ctx, drawing_data.fore_color);
    }
  }

  if (timer_is_vibrating()) {
    // GCompOpSet respects the PNG's alpha (transparency) channel.
    // This assumes your icon resource is a PNG with a transparent background.
    graphics_context_set_compositing_mode(ctx, GCompOpSet);

    // Calculate platform-agnostic icon positions
    const GSize icon_size = GSize(25, 25);
    const int16_t icon_padding_right = 5;
    const int16_t icon_padding_top = 10;
    const int16_t icon_x_right = bounds.size.w - icon_size.w - icon_padding_right;
    const GSize middle_icon_size = GSize(15, 15);
    const int16_t middle_icon_padding_right = 2;
    const int16_t middle_icon_x_right = bounds.size.w - middle_icon_size.w - middle_icon_padding_right;

    // Draw the reset icon (top right, Up button standard press)
    GRect reset_rect = GRect(icon_x_right, icon_padding_top, icon_size.w, icon_size.h);
    graphics_draw_bitmap_in_rect(ctx, drawing_data.reset_icon, reset_rect);
    // Draw the hold icon beside the reset icon (toward screen center)
    prv_draw_icon(ctx, drawing_data.icon_reset, LONG_UP_X, LONG_UP_Y,
                  ICON_SMALL_SIZE, ICON_SMALL_SIZE);

    // Draw the pause icon (middle right)
    // This calculates the Y coordinate to be perfectly centered vertically
    const int16_t pause_icon_y = (bounds.size.h - middle_icon_size.h) / 2;
    GRect pause_rect = GRect(middle_icon_x_right, pause_icon_y, middle_icon_size.w, middle_icon_size.h);
    graphics_draw_bitmap_in_rect(ctx, drawing_data.pause_icon, pause_rect);

    // Draw the silence icon (top left)
    GRect silence_rect = GRect(icon_padding_right, icon_padding_top, icon_size.w, icon_size.h);
    graphics_draw_bitmap_in_rect(ctx, drawing_data.silence_icon, silence_rect);

    // Draw the snooze icon (bottom right)
    const int16_t icon_padding_bottom = 10;
    const int16_t snooze_icon_y = bounds.size.h - icon_size.h - icon_padding_bottom;
    GRect snooze_rect = GRect(icon_x_right, snooze_icon_y, icon_size.w, icon_size.h);
    graphics_draw_bitmap_in_rect(ctx, drawing_data.snooze_icon, snooze_rect);

    // Set the mode back to default (Set) so it doesn't
    // affect other drawing operations.
    graphics_context_set_compositing_mode(ctx, GCompOpSet);
  }
}

// Update the drawing states and recalculate everythings positions
void drawing_update(void) {
  // update drawing state
  prv_update_draw_state(drawing_data.layer);
  // update progress ring angle
  prv_progress_ring_update();
}

// Initialize the singleton drawing data
void drawing_initialize(Layer *layer) {
  // get properties
  GRect bounds = layer_get_bounds(layer);
  // set the layer
  drawing_data.layer = layer;
  // set visual states
  drawing_data.progress_angle = 0;
  for (uint8_t ii = 0; ii < TEXT_FIELD_COUNT; ii++) {
    drawing_data.text_fields[ii].origin = grect_center_point(&bounds);
    drawing_data.text_fields[ii].size = GSizeZero;
  }
  drawing_data.focus_field.origin = grect_center_point(&bounds);
  if (main_get_control_mode() == ControlModeCounting) {
    drawing_data.focus_field.origin.x = bounds.size.w;
  }
  drawing_data.focus_field.size = GSizeZero;
  // set initial draw state to something which guaranties a refresh
  drawing_data.draw_state = (DrawState) {
    .hr_digits = 99,
  };
  // set the colors
  drawing_data.fore_color = GColorBlack;
  drawing_data.mid_color = PBL_IF_COLOR_ELSE(GColorMintGreen, GColorWhite);
  drawing_data.ring_color = PBL_IF_COLOR_ELSE(GColorGreen, GColorWhite);
  drawing_data.back_color = PBL_IF_COLOR_ELSE(GColorDarkGray, GColorBlack);
  // load alarm icons
  drawing_data.reset_icon = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_REPEAT_ICON);
  drawing_data.pause_icon = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_PAUSE_ICON);
  drawing_data.silence_icon = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_SILENCE_ICON);
  drawing_data.snooze_icon = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_SNOOZE_ICON);
  // load button action icons
  drawing_data.icon_plus_1hr = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_1HR);
  drawing_data.icon_plus_20min = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_20MIN);
  drawing_data.icon_plus_5min = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_5MIN);
  drawing_data.icon_plus_1min = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_1MIN);
  drawing_data.icon_plus_30sec = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_30SEC);
  drawing_data.icon_plus_20sec = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_20SEC);
  drawing_data.icon_plus_5sec = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_5SEC);
  drawing_data.icon_plus_1sec = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_1SEC);
  drawing_data.icon_reset = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_RESET);
  drawing_data.icon_quit = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_QUIT);
  drawing_data.icon_edit = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_EDIT);
  drawing_data.icon_to_bg = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_TO_BG);
  drawing_data.icon_details = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_DETAILS);
  drawing_data.icon_repeat_enable = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_REPEAT_ENABLE);
  drawing_data.icon_plus_20_rep = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_20_REP);
  drawing_data.icon_plus_5_rep = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_5_REP);
  drawing_data.icon_plus_1_rep = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_PLUS_1_REP);
  drawing_data.icon_reset_count = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_RESET_COUNT);
  drawing_data.icon_direction = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_DIRECTION);
  drawing_data.play_icon = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_PLAY_ICON);
  // set animation update callback
  animation_register_update_callback(&prv_animation_update_callback);
}

// Destroy the singleton drawing data
void drawing_terminate(void) {
  gbitmap_destroy(drawing_data.reset_icon);
  gbitmap_destroy(drawing_data.pause_icon);
  gbitmap_destroy(drawing_data.silence_icon);
  gbitmap_destroy(drawing_data.snooze_icon);
  gbitmap_destroy(drawing_data.icon_plus_1hr);
  gbitmap_destroy(drawing_data.icon_plus_20min);
  gbitmap_destroy(drawing_data.icon_plus_5min);
  gbitmap_destroy(drawing_data.icon_plus_1min);
  gbitmap_destroy(drawing_data.icon_plus_30sec);
  gbitmap_destroy(drawing_data.icon_plus_20sec);
  gbitmap_destroy(drawing_data.icon_plus_5sec);
  gbitmap_destroy(drawing_data.icon_plus_1sec);
  gbitmap_destroy(drawing_data.icon_reset);
  gbitmap_destroy(drawing_data.icon_quit);
  gbitmap_destroy(drawing_data.icon_edit);
  gbitmap_destroy(drawing_data.icon_to_bg);
  gbitmap_destroy(drawing_data.icon_details);
  gbitmap_destroy(drawing_data.icon_repeat_enable);
  gbitmap_destroy(drawing_data.icon_plus_20_rep);
  gbitmap_destroy(drawing_data.icon_plus_5_rep);
  gbitmap_destroy(drawing_data.icon_plus_1_rep);
  gbitmap_destroy(drawing_data.icon_reset_count);
  gbitmap_destroy(drawing_data.icon_direction);
  gbitmap_destroy(drawing_data.play_icon);
  animation_stop_all();
}
