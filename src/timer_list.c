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

// State
static Window   *s_window;
static Layer    *s_layer;
static AppTimer *s_idle_timer;
static AppTimer *s_refresh_timer;

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

// Emit a TEST_STATE log line for timer list events so functional tests can assert them.
static void prv_log_list_state(const char *event) {
  TEST_LOG(APP_LOG_LEVEL_DEBUG,
    "TEST_STATE:%s,m=TimerList,list_count=%d,sel=%d",
    event, (int)s_total_rows, (int)s_selected_row);
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

// Returns the slot index for a given display row
static int8_t prv_slot_for_row(int16_t row) {
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

    char line1[20] = {0};
    char line2[20] = {0};

    int8_t slot = prv_slot_for_row(row);

    if (s_implicit_idx >= 0 && row == 0) {
      // "New Timer" entry
      snprintf(line1, sizeof(line1), "New Timer");
      int64_t elapsed = prv_slot_elapsed((uint8_t)s_implicit_idx);
      prv_format_time(line2, sizeof(line2), elapsed);
    } else {
      // Existing timer
      if (prv_slot_is_chrono((uint8_t)slot)) {
        // Stopwatch: "HH:MM:SS -->" on line 1, elapsed on line 2
        int64_t total_ms = timer_slots[slot].length_ms;
        prv_format_time(line1, sizeof(line1) - 4, total_ms);
        strncat(line1, " -->", sizeof(line1) - strlen(line1) - 1);
        int64_t elapsed = prv_slot_elapsed((uint8_t)slot);
        prv_format_time(line2, sizeof(line2), elapsed);
      } else {
        // Countdown: total on line 1, remaining on line 2
        prv_format_time(line1, sizeof(line1), timer_slots[slot].length_ms);
        int64_t remaining = prv_slot_remaining((uint8_t)slot);
        prv_format_time(line2, sizeof(line2), remaining);
      }
    }

    GRect l1_rect = GRect(4, row_y, w - 8, LINE1_HEIGHT);
    GRect l2_rect = GRect(4, row_y + LINE1_HEIGHT, w - 8, LINE2_HEIGHT);

    GTextAlignment text_align = PBL_IF_ROUND_ELSE(GTextAlignmentCenter, GTextAlignmentLeft);
    graphics_draw_text(ctx, line1, label_font, l1_rect,
                       GTextOverflowModeFill, text_align, NULL);
    graphics_draw_text(ctx, line2, value_font, l2_rect,
                       GTextOverflowModeFill, text_align, NULL);

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
  uint8_t preexisting_count = timer_count - (s_implicit_idx >= 0 ? 1 : 0);
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
    s_total_rows = 1 + s_sorted_count;
  } else {
    timer_get_sorted_slots(s_sorted, &s_sorted_count);
    s_total_rows = s_sorted_count;
    (void)preexisting_count;
  }

  // Clamp selection
  if (s_total_rows == 0) {
    window_stack_pop_all(true);
    return;
  }
  if (s_selected_row >= (int16_t)s_total_rows) {
    s_selected_row = (int16_t)(s_total_rows - 1);
  }

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
  } else {
    s_implicit_idx = -1;
  }

  s_total_rows = s_sorted_count + (s_implicit_idx >= 0 ? 1 : 0);
  s_selected_row = 0;
  s_screen_h = bounds.size.h;
  s_scroll_y = 0;
  prv_update_scroll();

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
