#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

// Types
typedef int32_t status_t;

// Logging
#define APP_LOG_LEVEL_ERROR 1
#define APP_LOG_LEVEL_WARNING 50
#define APP_LOG_LEVEL_INFO 100
#define APP_LOG_LEVEL_DEBUG 200
#define APP_LOG_LEVEL_VERBOSE 255

#define APP_LOG(level, fmt, args...) printf(fmt "\n", ## args)

// Persistence
status_t persist_write_int(const uint32_t key, const int32_t value);
int persist_write_data(const uint32_t key, const void *data, const size_t size);
bool persist_exists(const uint32_t key);
status_t persist_delete(const uint32_t key);
int persist_read_data(const uint32_t key, void *buffer, const size_t buffer_size);

// Vibration
typedef struct {
  const uint32_t *durations;
  int num_segments;
} VibePattern;

void vibes_long_pulse(void);
void vibes_enqueue_custom_pattern(VibePattern pattern);
void vibes_cancel(void);
void vibes_short_pulse(void);

// Time
time_t time(time_t *tloc);
uint16_t time_ms(time_t *tloc, uint16_t *out_ms);

// Utils
#define ARRAY_LENGTH(array) (sizeof((array)) / sizeof((array)[0]))

// --- UI Mocks ---
typedef struct Window Window;
typedef struct Layer Layer;
typedef struct AppTimer AppTimer;
typedef void* ClickRecognizerRef;
typedef struct GContext GContext;
typedef struct GRect {
  int16_t x; int16_t y; int16_t w; int16_t h;
} GRect;

typedef enum {
  BUTTON_ID_BACK,
  BUTTON_ID_UP,
  BUTTON_ID_SELECT,
  BUTTON_ID_DOWN,
} ButtonId;

typedef void (*ClickHandler)(ClickRecognizerRef recognizer, void *context);
typedef void (*ClickConfigProvider)(void *context);
typedef void (*AppTimerCallback)(void *data);

typedef struct tm tm;
typedef int TimeUnits;
#define MINUTE_UNIT 0

// Function stubs needed
Window* window_create(void);
void window_destroy(Window* window);
void window_set_click_config_provider(Window *window, ClickConfigProvider click_config_provider);
Layer* window_get_root_layer(Window *window);
GRect layer_get_bounds(Layer *layer);
void window_stack_push(Window *window, bool animated);
void window_stack_pop(bool animated);
Layer* layer_create(GRect frame);
void layer_destroy(Layer* layer);
void layer_set_update_proc(Layer *layer, void* proc);
void layer_add_child(Layer *parent, Layer *child);
void layer_mark_dirty(Layer *layer);
void window_single_click_subscribe(ButtonId button_id, ClickHandler handler);
void window_raw_click_subscribe(ButtonId button_id, void* down_handler, void* up_handler, void* context);
void window_long_click_subscribe(ButtonId button_id, uint16_t delay_ms, ClickHandler handler, void* context);
AppTimer* app_timer_register(uint32_t timeout_ms, AppTimerCallback callback, void* callback_data);
void app_timer_cancel(AppTimer* timer);
void app_timer_reschedule(AppTimer* timer, uint32_t new_timeout_ms);
void tick_timer_service_subscribe(TimeUnits tick_units, void* handler);
void tick_timer_service_unsubscribe(void);
void wakeup_cancel_all(void);
void wakeup_schedule(time_t timestamp, uint32_t cookie, bool notify_if_missed);
