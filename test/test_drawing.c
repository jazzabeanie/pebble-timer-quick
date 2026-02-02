#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h> // For abs

// Include test/pebble.h
#include "pebble.h"

// Define macros expected by drawing.c
#define GRect(x, y, w, h) ((GRect){{(x), (y)}, {(w), (h)}})
#define GSize(w, h) ((GSize){(w), (h)})
#define GPoint(x, y) ((GPoint){(x), (y)})

// Define missing types/enums that are used in drawing.c
typedef enum {
  GColorBlack,
  GColorWhite,
  GColorMintGreen,
  GColorGreen,
  GColorDarkGray,
} GColor;

#define PBL_IF_COLOR_ELSE(if_true, if_false) (if_true)

typedef enum {
  GCornerNone,
} GCornerMask;

typedef enum {
  GCompOpSet,
} GCompOp;

typedef enum {
  GOvalScaleModeFillCircle,
} GOvalScaleMode;

typedef struct GBitmap GBitmap; // Opaque

// FONT keys as strings
#define FONT_KEY_GOTHIC_24_BOLD "FONT_KEY_GOTHIC_24_BOLD"
#define FONT_KEY_GOTHIC_28_BOLD "FONT_KEY_GOTHIC_28_BOLD"

typedef enum {
    GTextOverflowModeFill,
} GTextOverflowMode;

typedef enum {
    GTextAlignmentCenter,
    GTextAlignmentRight,
} GTextAlignment;

typedef struct GFont GFont; // Opaque

typedef struct GEdgeInsets {
    int16_t top;
    int16_t right;
    int16_t bottom;
    int16_t left;
} GEdgeInsets;

#define GEdgeInsets1(i) ((GEdgeInsets){.top = i, .right = i, .bottom = i, .left = i})

typedef int32_t int32_t;
#define TRIG_MAX_RATIO 0xffff
#define TRIG_MAX_ANGLE 0x10000

// Defines from main.h/drawing.c that might be needed if not present
#define MSEC_IN_SEC 1000
#define MSEC_IN_MIN (60 * MSEC_IN_SEC)

// Resource IDs (dummy)
#define RESOURCE_ID_IMAGE_REPEAT_ICON 1
#define RESOURCE_ID_IMAGE_PAUSE_ICON 2
#define RESOURCE_ID_IMAGE_SILENCE_ICON 3
#define RESOURCE_ID_IMAGE_SNOOZE_ICON 4
#define RESOURCE_ID_IMAGE_ICON_PLUS_1HR 5
#define RESOURCE_ID_IMAGE_ICON_PLUS_20MIN 6
#define RESOURCE_ID_IMAGE_ICON_PLUS_5MIN 7
#define RESOURCE_ID_IMAGE_ICON_PLUS_1MIN 8
#define RESOURCE_ID_IMAGE_ICON_PLUS_30SEC 9
#define RESOURCE_ID_IMAGE_ICON_PLUS_20SEC 10
#define RESOURCE_ID_IMAGE_ICON_PLUS_5SEC 11
#define RESOURCE_ID_IMAGE_ICON_PLUS_1SEC 12
#define RESOURCE_ID_IMAGE_ICON_RESET 13
#define RESOURCE_ID_IMAGE_ICON_QUIT 14
#define RESOURCE_ID_IMAGE_ICON_EDIT 15
#define RESOURCE_ID_IMAGE_ICON_TO_BG 16
#define RESOURCE_ID_IMAGE_ICON_DETAILS 17
#define RESOURCE_ID_IMAGE_ICON_REPEAT_ENABLE 18
#define RESOURCE_ID_IMAGE_ICON_PLUS_20_REP 19
#define RESOURCE_ID_IMAGE_ICON_PLUS_5_REP 20
#define RESOURCE_ID_IMAGE_ICON_PLUS_1_REP 21
#define RESOURCE_ID_IMAGE_ICON_RESET_COUNT 22
#define RESOURCE_ID_IMAGE_ICON_DIRECTION 23
#define RESOURCE_ID_IMAGE_PLAY_ICON 24
#define RESOURCE_ID_IMAGE_ICON_MINUS_1HR 25
#define RESOURCE_ID_IMAGE_ICON_MINUS_20MIN 26
#define RESOURCE_ID_IMAGE_ICON_MINUS_5MIN 27
#define RESOURCE_ID_IMAGE_ICON_MINUS_1MIN 28
#define RESOURCE_ID_IMAGE_ICON_PLUS_60SEC 29
#define RESOURCE_ID_IMAGE_ICON_MINUS_60SEC 30
#define RESOURCE_ID_IMAGE_ICON_MINUS_20SEC 31
#define RESOURCE_ID_IMAGE_ICON_MINUS_5SEC 32
#define RESOURCE_ID_IMAGE_ICON_MINUS_1SEC 33

// Globals
GSize GSizeZero = {0,0};
GRect GRectZero = {{0,0},{0,0}};

// External variables
#include "../src/main.h" // For ControlMode
#include "../src/timer.h" // For Timer struct and extern
// Note: drawing.c includes main.h and timer.h too.
// We include them here so we can define mocks that use types from them.

// Definition of timer_data
Timer timer_data;

// Include animation headers for InterpolationCurve
#include "../src/interpolation.h"
#include "../src/animation.h"

// Mocks for main.c
ControlMode mock_control_mode = ControlModeNew;
bool mock_editing_existing = false;
bool mock_interaction_active = false;
bool mock_last_interaction_down = false;
uint64_t mock_last_interaction_time = 0;
bool mock_reverse_direction = false;

ControlMode main_get_control_mode(void) { return mock_control_mode; }
bool main_is_editing_existing_timer(void) { return mock_editing_existing; }
bool main_is_interaction_active(void) { return mock_interaction_active; }
bool main_is_last_interaction_down(void) { return mock_last_interaction_down; }
uint64_t main_get_last_interaction_time(void) { return mock_last_interaction_time; }
bool main_is_reverse_direction(void) { return mock_reverse_direction; }

// Mocks for timer.c
void timer_get_time_parts(uint16_t *hr, uint16_t *min, uint16_t *sec) { *hr=0; *min=0; *sec=0; }
int64_t timer_get_value_ms(void) { return 0; }
int64_t timer_get_length_ms(void) { return 0; }
bool timer_is_vibrating(void) { return false; }
bool timer_is_chrono(void) { return false; }
bool timer_is_paused(void) { return true; }

// Mocks for text_render.h
// Note: drawing.c includes text_render.h, so we must match types.
// We can define stubs.
#include "../src/text_render.h"
uint16_t text_render_get_max_font_size(char *text, GRect bounds) { return 10; }
GRect text_render_get_content_bounds(char *text, uint16_t font_size) { return (GRect){{0,0},{10,10}}; }
void text_render_draw_scalable_text(GContext *ctx, char *text, GRect bounds) {}

// Mocks for animation.h
// We must match signatures in animation.h
void animation_grect_start(GRect *ptr, GRect to, uint32_t duration, uint32_t delay, InterpolationCurve interpolation) {}
void animation_stop(void *ptr) {}
void animation_int32_start(int32_t *ptr, int32_t to, uint32_t duration, uint32_t delay, InterpolationCurve interpolation) {}
void animation_register_update_callback(void *callback) {}
void animation_stop_all(void) {}

// Mocks for Pebble Graphics
void graphics_draw_text(GContext *ctx, const char *text, GFont const *font, GRect box, GTextOverflowMode overflow_mode, GTextAlignment alignment, void *layout) {}
GFont *fonts_get_system_font(const char *font_key) { return NULL; }
void graphics_context_set_fill_color(GContext *ctx, GColor color) {}
void graphics_fill_radial(GContext *ctx, GRect rect, GOvalScaleMode mode, uint16_t inset_thickness, int32_t angle_start, int32_t angle_end) {}
void graphics_fill_rect(GContext *ctx, GRect rect, uint16_t corner_radius, GCornerMask corner_mask) {}
void graphics_fill_rect_grey(GContext *ctx, GRect rect) {}
void graphics_fill_circle(GContext *ctx, GPoint p, uint16_t radius) {}
void graphics_context_set_stroke_color(GContext *ctx, GColor color) {}
void graphics_context_set_text_color(GContext *ctx, GColor color) {}
void graphics_context_set_compositing_mode(GContext *ctx, GCompOp mode) {}
GRect layer_get_bounds(Layer *layer) { return (GRect){{0,0},{144,168}}; }
void layer_mark_dirty(Layer *layer) {}

// We need to track bitmap draws
#define MAX_DRAWS 20
typedef struct {
    GBitmap *bitmap;
    GRect rect;
} DrawCall;
DrawCall draw_calls[MAX_DRAWS];
int draw_call_count = 0;

void graphics_draw_bitmap_in_rect(GContext *ctx, const GBitmap *bitmap, GRect rect) {
    if (draw_call_count < MAX_DRAWS) {
        draw_calls[draw_call_count].bitmap = (GBitmap*)bitmap;
        draw_calls[draw_call_count].rect = rect;
        draw_call_count++;
    }
}

bool was_bitmap_drawn(uint32_t resource_id) {
    for (int i=0; i<draw_call_count; i++) {
        if ((uintptr_t)draw_calls[i].bitmap == resource_id) {
            return true;
        }
    }
    return false;
}

GBitmap* gbitmap_create_with_resource(uint32_t resource_id) {
    return (GBitmap*)(uintptr_t)resource_id; // Return resource ID as pointer for easy check
}
void gbitmap_destroy(GBitmap *bitmap) {}

// Math
int32_t sin_lookup(int32_t angle) { return TRIG_MAX_RATIO; }
int32_t atan2_lookup(int16_t y, int16_t x) { return 0; }
uint64_t epoch(void) { return 0; }

GPoint grect_center_point(const GRect *rect) { return (GPoint){0,0}; }
GRect grect_inset(GRect rect, GEdgeInsets insets) { return rect; }
bool clock_is_24h_style(void) { return true; }

// Include source file
#include "../src/drawing.c"

// Tests
static void test_icon_overlap(void **state) {
    // Setup
    mock_control_mode = ControlModeNew;
    timer_data.is_repeating = true;
    timer_data.repeat_count = 2; // > 1 implies showing counter

    // Initialize drawing (loads icons)
    drawing_initialize((Layer*)1);

    // Reset call count
    draw_call_count = 0;

    // Render
    drawing_render((Layer*)1, (GContext*)1);

    // Check if 20min icon was drawn (Resource ID 6)
    // We expect it NOT to be drawn after the fix
    assert_false(was_bitmap_drawn(RESOURCE_ID_IMAGE_ICON_PLUS_20MIN));

    // Cleanup
    drawing_terminate();
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_icon_overlap),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
