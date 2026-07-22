// @file timer_list.c
// @brief Timer List window for multi-timer support

#include <pebble.h>
#include "timer_list.h"
#include "timer.h"
#include "utility.h"
#include "main.h"

#define IDLE_TIMEOUT_MS   30000
#define LINE1_HEIGHT      26
#define LINE2_HEIGHT      20
#define ROW_HEIGHT        (LINE1_HEIGHT + LINE2_HEIGHT)
#define REFRESH_MS        500
// Duration of the "hold Down to clear all timers" hint overlay
#define HINT_FEEDBACK_MS  3000

// Sentinel returned by prv_slot_for_row for the pinned "Delete all" row
#define SLOT_DELETE_ALL   (-2)

// State
static Window   *s_window;
static Layer    *s_layer;
static AppTimer *s_idle_timer;
static AppTimer *s_refresh_timer;
#if LAP_FEATURE
// "Hold Down to clear all timers" hint (shown by Select on the Delete all row)
static AppTimer *s_hint_timer;
static bool      s_show_hint;
#endif

// Index of the implicit new stopwatch slot (-1 if at capacity)
static int8_t  s_implicit_idx;
// Sorted pre-existing slot indices (populated before implicit slot is created)
static uint8_t s_sorted[MAX_TIMERS];
static uint8_t s_sorted_count;
// Currently highlighted row (0 = New Timer / first item)
static int16_t s_selected_row;
// Total displayable rows
static uint8_t s_total_rows;
// Scroll offset in pixels and screen height for scroll calculations
static int16_t s_scroll_y;
static int16_t s_screen_h;

// Repeat indicator: the same glyph the Counting-mode "enable repeat" button
// shows. The list draws it on rows whose background flips between light
// (unselected) and black (selected), so it is pre-tinted to both the black and
// white text colors and the matching copy is drawn per row.
#define REPEAT_ICON_SIZE 15
static GBitmap *s_repeat_icon_dark;   //< black glyph for light (unselected) rows
static GBitmap *s_repeat_icon_light;  //< white glyph for the black selected row

// Load the repeat glyph and recolor its opaque pixels to `color`, leaving
// transparent pixels untouched so GCompOpSet still composites cleanly. Handles
// the 8-bit (color) and palettized (b&w) formats the resource loads as.
static GBitmap *prv_create_tinted_repeat_icon(GColor color) {
  GBitmap *bmp = gbitmap_create_with_resource(RESOURCE_ID_IMAGE_ICON_REPEAT_ENABLE);
  if (!bmp) {
    return NULL;
  }
  GBitmapFormat fmt = gbitmap_get_format(bmp);
  if (fmt == GBitmapFormat8Bit) {
    GRect b = gbitmap_get_bounds(bmp);
    uint8_t *data = gbitmap_get_data(bmp);
    uint16_t stride = gbitmap_get_bytes_per_row(bmp);
    for (int y = 0; y < b.size.h; y++) {
      uint8_t *row = data + y * stride;
      for (int x = 0; x < b.size.w; x++) {
        uint8_t alpha = row[x] & 0xC0;  // preserve the 2-bit alpha (edge softness)
        if (alpha) {
          row[x] = alpha | (color.argb & 0x3F);  // replace RGB, keep alpha
        }
      }
    }
  } else {
    // Palettized (1/2/4-bit with a transparent entry): recolor opaque entries
    GColor *palette = gbitmap_get_palette(bmp);
    if (palette) {
      int count = (fmt == GBitmapFormat1BitPalette) ? 2
                : (fmt == GBitmapFormat2BitPalette) ? 4
                : (fmt == GBitmapFormat4BitPalette) ? 16 : 0;
      for (int i = 0; i < count; i++) {
        if (palette[i].a != 0) {
          palette[i].r = color.r;
          palette[i].g = color.g;
          palette[i].b = color.b;
        }
      }
    }
  }
  return bmp;
}

// Emit a TEST_STATE log line for timer list events so functional tests can assert them.
static void prv_log_list_state(const char *event) {
  // Include the name of the first existing slot (if any) so tests can verify name display.
  const char *name0 = "";
  if (s_sorted_count > 0) {
    name0 = timer_slots[s_sorted[0]].name;
  }
  TEST_LOG(APP_LOG_LEVEL_DEBUG,
    "TEST_STATE:%s,m=TimerList,list_count=%d,sel=%d,name0=%s",
    event, (int)s_total_rows, (int)s_selected_row, name0);
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Helpers
//

static void prv_format_time(char *buf, size_t len, int64_t ms) {
  if (ms < 0) ms = 0;
  uint32_t total_sec = (uint32_t)(ms / 1000);
  uint32_t hr  = total_sec / 3600;
  uint32_t min = (total_sec % 3600) / 60;
  uint32_t sec = total_sec % 60;
  if (hr > 0) {
    snprintf(buf, len, "%02lu:%02lu:%02lu", (unsigned long)hr, (unsigned long)min, (unsigned long)sec);
  } else {
    snprintf(buf, len, "%02lu:%02lu", (unsigned long)min, (unsigned long)sec);
  }
}

// Returns elapsed_ms for a slot (handles running vs. paused)
static int64_t prv_slot_elapsed(uint8_t idx) {
  Timer *t = &timer_slots[idx];
  if (t->is_paused) return t->start_ms;
  return (int64_t)epoch() - t->start_ms;
}

// Returns true if slot is a stopwatch (chrono)
static bool prv_slot_is_chrono(uint8_t idx) {
  Timer *t = &timer_slots[idx];
  return t->length_ms - prv_slot_elapsed(idx) <= 0;
}

// Returns remaining ms for a countdown slot (positive = time left)
static int64_t prv_slot_remaining(uint8_t idx) {
  Timer *t = &timer_slots[idx];
  return t->length_ms - prv_slot_elapsed(idx);
}

// Returns the slot index for a given display row, or SLOT_DELETE_ALL for the
// pinned bottom "Delete all" row (compiled out on aplite with the lap feature)
static int8_t prv_slot_for_row(int16_t row) {
#if LAP_FEATURE
  if (row == (int16_t)(s_total_rows - 1)) return SLOT_DELETE_ALL;
#endif
  if (s_implicit_idx >= 0) {
    if (row == 0) return s_implicit_idx;
    return (int8_t)s_sorted[row - 1];
  }
  return (int8_t)s_sorted[row];
}

static void prv_restart_idle_timer(void);

static void prv_update_scroll(void) {
#if defined(PBL_ROUND)
  // On round displays: keep the selected row vertically centred
  s_scroll_y = s_selected_row * ROW_HEIGHT + ROW_HEIGHT / 2 - s_screen_h / 2;
#else
  // On rectangular displays: scroll just enough to keep the row in view
  int16_t sel_top = s_selected_row * ROW_HEIGHT;
  int16_t sel_bot = sel_top + ROW_HEIGHT;
  if (sel_top < s_scroll_y) {
    s_scroll_y = sel_top;
  } else if (sel_bot > s_scroll_y + s_screen_h) {
    s_scroll_y = sel_bot - s_screen_h;
  }
#endif
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Drawing
//

static void prv_layer_update_proc(Layer *layer, GContext *ctx) {
  GRect bounds = layer_get_bounds(layer);
  const int16_t w = bounds.size.w;

  // Background
  graphics_context_set_fill_color(ctx, PBL_IF_COLOR_ELSE(GColorMintGreen, GColorWhite));
  graphics_fill_rect(ctx, bounds, 0, GCornerNone);

  graphics_context_set_text_color(ctx, GColorBlack);

  // Transient overlays: the Delete all hint, or the slot-limit warning fired
  // by creating the implicit timer while this window is on top
#if LAP_FEATURE
  const char *overlay = s_show_hint ? "Hold Down to clear all timers"
                                    : main_get_warning_message();
  if (overlay) {
    GRect text_bounds = GRect(bounds.origin.x + 10, bounds.origin.y + bounds.size.h / 2 - 34,
                              bounds.size.w - 20, 68);
    graphics_draw_text(ctx, overlay, fonts_get_system_font(FONT_KEY_GOTHIC_28_BOLD),
      text_bounds, GTextOverflowModeWordWrap, GTextAlignmentCenter, NULL);
    return;
  }
#endif

  for (int16_t row = 0; row < s_total_rows; row++) {
    int16_t row_y = row * ROW_HEIGHT - s_scroll_y;
    if (row_y + ROW_HEIGHT <= 0 || row_y >= bounds.size.h) continue;

    GRect row_rect = GRect(0, row_y, w, ROW_HEIGHT);
    bool is_selected = (row == s_selected_row);

    // Highlight selected row
    if (is_selected) {
      graphics_context_set_fill_color(ctx, GColorBlack);
      graphics_fill_rect(ctx, row_rect, 0, GCornerNone);
      graphics_context_set_text_color(ctx, GColorWhite);
    } else {
      graphics_context_set_text_color(ctx, GColorBlack);
    }

    GFont label_font = fonts_get_system_font(FONT_KEY_GOTHIC_24_BOLD);
    GFont value_font = fonts_get_system_font(FONT_KEY_GOTHIC_18_BOLD);

    // Sized so the enlarged timer names display without clipping
    char line1[44] = {0};
    char line2[24] = {0};

    int8_t slot = prv_slot_for_row(row);

    // Existing repeating timers get a repeat glyph at the right of the name line
    bool show_repeat_icon = (slot >= 0) && timer_slots[slot].is_repeating;

    if (slot == SLOT_DELETE_ALL) {
      // Pinned "Delete all" entry
      snprintf(line1, sizeof(line1), "Delete all");
    } else if (s_implicit_idx >= 0 && row == 0) {
      // "New Timer" entry
      snprintf(line1, sizeof(line1), "New Timer");
      int64_t elapsed = prv_slot_elapsed((uint8_t)s_implicit_idx);
      prv_format_time(line2, sizeof(line2), elapsed);
    } else {
      // Existing timer
      strncpy(line1, timer_slots[slot].name, sizeof(line1) - 1);
      line1[sizeof(line1) - 1] = '\0';
      if (prv_slot_is_chrono((uint8_t)slot)) {
        int64_t elapsed = prv_slot_elapsed((uint8_t)slot);
        prv_format_time(line2, sizeof(line2), elapsed);
      } else {
        int64_t remaining = prv_slot_remaining((uint8_t)slot);
        prv_format_time(line2, sizeof(line2), remaining);
      }
    }

    // Reserve room on the name line for the repeat glyph so long names don't
    // draw underneath it
    int16_t l1_right_pad = show_repeat_icon ? (REPEAT_ICON_SIZE + 6) : 0;
    GRect l1_rect = GRect(4, row_y, w - 8 - l1_right_pad, LINE1_HEIGHT);
    GRect l2_rect = GRect(4, row_y + LINE1_HEIGHT, w - 8, LINE2_HEIGHT);

    GTextAlignment text_align = PBL_IF_ROUND_ELSE(GTextAlignmentCenter, GTextAlignmentLeft);
    graphics_draw_text(ctx, line1, label_font, l1_rect,
                       GTextOverflowModeFill, text_align, NULL);
    graphics_draw_text(ctx, line2, value_font, l2_rect,
                       GTextOverflowModeFill, text_align, NULL);

    if (show_repeat_icon) {
      GBitmap *icon = is_selected ? s_repeat_icon_light : s_repeat_icon_dark;
      if (icon) {
        int16_t ix = w - REPEAT_ICON_SIZE - 4;
        int16_t iy = row_y + (LINE1_HEIGHT - REPEAT_ICON_SIZE) / 2;
        graphics_context_set_compositing_mode(ctx, GCompOpSet);
        graphics_draw_bitmap_in_rect(ctx, icon,
            GRect(ix, iy, REPEAT_ICON_SIZE, REPEAT_ICON_SIZE));
      }
    }

    // Separator line (between rows, only when not selected)
    if (!is_selected && row < s_total_rows - 1) {
      graphics_context_set_stroke_color(ctx, GColorLightGray);
      int16_t sep_y = row_y + ROW_HEIGHT - 1;
      graphics_draw_line(ctx, GPoint(0, sep_y), GPoint(w, sep_y));
    }

    // Reset text color for next row
    graphics_context_set_text_color(ctx, GColorBlack);
  }
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Idle / Refresh Timers
//

static void prv_idle_callback(void *data) {
  s_idle_timer = NULL;
  prv_log_list_state("timer_list_idle_background");
  // Implicit slot stays in array → will be persisted on terminate
  window_stack_pop_all(true);
}

static void prv_restart_idle_timer(void) {
  if (s_idle_timer) app_timer_cancel(s_idle_timer);
  s_idle_timer = app_timer_register(IDLE_TIMEOUT_MS, prv_idle_callback, NULL);
}

static void prv_refresh_callback(void *data) {
  s_refresh_timer = NULL;
  if (s_layer) layer_mark_dirty(s_layer);
  s_refresh_timer = app_timer_register(REFRESH_MS, prv_refresh_callback, NULL);
}

#if LAP_FEATURE
// Hide the "hold Down to clear all timers" hint
static void prv_hint_hide_callback(void *data) {
  s_hint_timer = NULL;
  s_show_hint = false;
  if (s_layer) layer_mark_dirty(s_layer);
}

// Show the hint overlay for HINT_FEEDBACK_MS
static void prv_show_hint(void) {
  s_show_hint = true;
  if (s_hint_timer) app_timer_cancel(s_hint_timer);
  s_hint_timer = app_timer_register(HINT_FEEDBACK_MS, prv_hint_hide_callback, NULL);
  if (s_layer) layer_mark_dirty(s_layer);
}
#endif  // LAP_FEATURE


////////////////////////////////////////////////////////////////////////////////////////////////////
// Button Handlers
//

static void prv_up_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_restart_idle_timer();
  if (s_selected_row > 0) {
    s_selected_row--;
    prv_update_scroll();
    layer_mark_dirty(s_layer);
  }
}

static void prv_down_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_restart_idle_timer();
  if (s_selected_row < (int16_t)(s_total_rows - 1)) {
    s_selected_row++;
    prv_update_scroll();
    layer_mark_dirty(s_layer);
  }
}

static void prv_select_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_restart_idle_timer();

#if LAP_FEATURE
  if (prv_slot_for_row(s_selected_row) == SLOT_DELETE_ALL) {
    // Select on "Delete all" only shows the instruction hint; deletes nothing
    prv_show_hint();
    prv_log_list_state("timer_list_delete_all_hint");
    return;
  }
#endif

  if (s_implicit_idx >= 0 && s_selected_row == 0) {
    // "New Timer" selected: keep implicit slot, set active, reveal main window in New mode
    timer_set_active_slot((uint8_t)s_implicit_idx);
    main_set_control_mode(ControlModeNew);
    main_reset_new_expire_timer();
    prv_log_list_state("timer_list_select_new");
  } else {
    // Existing timer selected
    int8_t selected_slot = prv_slot_for_row(s_selected_row);
    // Discard implicit slot
    if (s_implicit_idx >= 0) {
      timer_slot_delete((uint8_t)s_implicit_idx);
      // After deletion, if selected_slot > s_implicit_idx it shifted down
      if (selected_slot > s_implicit_idx) selected_slot--;
    }
    timer_set_active_slot((uint8_t)selected_slot);
    main_set_control_mode(ControlModeCounting);
    prv_log_list_state("timer_list_select_existing");
  }

  main_force_redraw();
  window_stack_pop(true);
}

static void prv_back_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_restart_idle_timer();
  // Implicit slot stays → persisted on terminate; exit the app
  window_stack_pop_all(true);
}

static void prv_down_long_click_handler(ClickRecognizerRef recognizer, void *ctx) {
  prv_restart_idle_timer();

#if LAP_FEATURE
  if (prv_slot_for_row(s_selected_row) == SLOT_DELETE_ALL) {
    // Hold Down on "Delete all": remove every timer and exit to the watchface
    while (timer_count > 0) {
      timer_slot_delete(timer_count - 1);
    }
    s_implicit_idx = -1;
    s_sorted_count = 0;
    s_total_rows = 1;  // only the Delete all row remains
    s_selected_row = 0;
    timer_persist_store();
    prv_log_list_state("timer_list_delete_all");
    window_stack_pop_all(true);
    return;
  }
#endif

  if (s_implicit_idx >= 0 && s_selected_row == 0) {
    // Hold Down on "New Timer": discard implicit slot and quit
    timer_slot_delete((uint8_t)s_implicit_idx);
    s_implicit_idx = -1;
    window_stack_pop_all(true);
    return;
  }

  // Hold Down on existing timer: delete it and refresh list
  int8_t slot_to_delete = prv_slot_for_row(s_selected_row);
  timer_slot_delete((uint8_t)slot_to_delete);

  // Rebuild sorted list (implicit slot may have shifted)
  if (s_implicit_idx >= 0) {
    // implicit slot is now at timer_count - 1
    s_implicit_idx = (int8_t)(timer_count - 1);
    // Sort only the preexisting slots (0..preexisting_count-1)
    uint8_t all_sorted[MAX_TIMERS];
    uint8_t all_count = 0;
    timer_get_sorted_slots(all_sorted, &all_count);
    // Exclude the implicit slot from sorted list
    s_sorted_count = 0;
    for (uint8_t i = 0; i < all_count; i++) {
      if (all_sorted[i] != (uint8_t)s_implicit_idx) {
        s_sorted[s_sorted_count++] = all_sorted[i];
      }
    }
  } else {
    timer_get_sorted_slots(s_sorted, &s_sorted_count);
  }
  // LAP_FEATURE (0/1) accounts for the pinned Delete all row
  s_total_rows = (s_implicit_idx >= 0 ? 1 : 0) + s_sorted_count + LAP_FEATURE;

#if LAP_FEATURE
  // Move the selection to the previous timer entry. Deleting the topmost
  // timer keeps the position (the next timer shifts up); deleting the last
  // timer selects the New Timer row. Never lands on Delete all.
  int16_t first_real = (s_implicit_idx >= 0) ? 1 : 0;
  if (s_sorted_count == 0) {
    if (s_implicit_idx < 0) {
      // No timers left and no New Timer row to select: exit like before
      window_stack_pop_all(true);
      return;
    }
    s_selected_row = 0;  // New Timer row
  } else {
    int16_t sel = s_selected_row - 1;
    int16_t last_real = first_real + (int16_t)s_sorted_count - 1;
    if (sel < first_real) sel = first_real;
    if (sel > last_real) sel = last_real;
    s_selected_row = sel;
  }
#else
  // Clamp selection (previous behavior)
  if (s_total_rows == 0) {
    window_stack_pop_all(true);
    return;
  }
  if (s_selected_row >= (int16_t)s_total_rows) {
    s_selected_row = (int16_t)(s_total_rows - 1);
  }
#endif
  prv_update_scroll();

  // Log after list is rebuilt so list_count reflects the post-deletion state
  prv_log_list_state("timer_list_delete");
  layer_mark_dirty(s_layer);
}

static void prv_click_config_provider(void *ctx) {
  window_single_click_subscribe(BUTTON_ID_UP,     prv_up_click_handler);
  window_single_click_subscribe(BUTTON_ID_DOWN,   prv_down_click_handler);
  window_single_click_subscribe(BUTTON_ID_SELECT, prv_select_click_handler);
  window_single_click_subscribe(BUTTON_ID_BACK,   prv_back_click_handler);
  window_long_click_subscribe(BUTTON_ID_DOWN, BUTTON_HOLD_RESET_MS,
                              prv_down_long_click_handler, NULL);
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// Window Lifecycle
//

static void prv_window_load(Window *window) {
  Layer *root = window_get_root_layer(window);
  GRect bounds = layer_get_bounds(root);

  // Snapshot pre-existing sorted slots BEFORE creating implicit slot
  uint8_t preexisting_count = timer_count;
  if (preexisting_count > 0) {
    timer_get_sorted_slots(s_sorted, &s_sorted_count);
  } else {
    s_sorted_count = 0;
  }

  // Create implicit new stopwatch (unless at capacity)
  if (preexisting_count < MAX_TIMERS) {
    s_implicit_idx = timer_slot_create();
    if (s_implicit_idx >= 0) {
      // Warn (message + three vibrations) when this creation leaves <= 3 free
      main_notify_timer_created();
    }
  } else {
    s_implicit_idx = -1;
  }

  // LAP_FEATURE (0/1) accounts for the pinned Delete all row
  s_total_rows = s_sorted_count + (s_implicit_idx >= 0 ? 1 : 0) + LAP_FEATURE;
  s_selected_row = 0;
  s_screen_h = bounds.size.h;
  s_scroll_y = 0;
  prv_update_scroll();

  s_repeat_icon_dark = prv_create_tinted_repeat_icon(GColorBlack);
  s_repeat_icon_light = prv_create_tinted_repeat_icon(GColorWhite);

  s_layer = layer_create(bounds);
  layer_set_update_proc(s_layer, prv_layer_update_proc);
  layer_add_child(root, s_layer);

  prv_log_list_state("timer_list_show");
  prv_restart_idle_timer();
  s_refresh_timer = app_timer_register(REFRESH_MS, prv_refresh_callback, NULL);
}

static void prv_window_unload(Window *window) {
  if (s_idle_timer) {
    app_timer_cancel(s_idle_timer);
    s_idle_timer = NULL;
  }
  if (s_refresh_timer) {
    app_timer_cancel(s_refresh_timer);
    s_refresh_timer = NULL;
  }
#if LAP_FEATURE
  if (s_hint_timer) {
    app_timer_cancel(s_hint_timer);
    s_hint_timer = NULL;
    s_show_hint = false;
  }
#endif
  if (s_repeat_icon_dark) {
    gbitmap_destroy(s_repeat_icon_dark);
    s_repeat_icon_dark = NULL;
  }
  if (s_repeat_icon_light) {
    gbitmap_destroy(s_repeat_icon_light);
    s_repeat_icon_light = NULL;
  }
  layer_destroy(s_layer);
  s_layer = NULL;
  window_destroy(s_window);
  s_window = NULL;
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// API
//

void timer_list_window_push(void) {
  s_window = window_create();
  window_set_click_config_provider(s_window, prv_click_config_provider);
  window_set_window_handlers(s_window, (WindowHandlers){
    .load   = prv_window_load,
    .unload = prv_window_unload,
  });
  window_stack_push(s_window, true);
}
