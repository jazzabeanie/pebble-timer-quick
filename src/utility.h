//! @file utility.h
//! @brief File containing simple convenience functions.
//!
//! This file contains simple convenience functions that may be used
//! in several different places. An example would be the "assert" function
//! which terminates program execution based on the state of a pointer.
//!
//! @author Eric D. Phillips
//! @date August 29, 2015
//! @bugs No known bugs

#pragma once
#include <pebble.h>

//! Time span conversions
#define MSEC_IN_HR 3600000
#define MSEC_IN_MIN 60000
#define MSEC_IN_SEC 1000
#define SEC_IN_MIN 60
#define MIN_IN_HR 60

//! Compatibility functions for Aplite
#ifdef PBL_SDK_2
#define GEdgeInsets1(value) value
GRect grect_inset(GRect bounds, int16_t inset);
static const uint8_t GOvalScaleModeFillCircle = 0;
void graphics_fill_radial(GContext *ctx, GRect bounds, uint8_t fill_mode, int16_t inset,
                          int32_t angle_start, int32_t angle_end);
#endif

#ifdef PBL_BW
//! Fill GRect with "grey" on Aplite
void graphics_fill_rect_grey(GContext *ctx, GRect rect);
#endif

//! Terminate program if null pointer
//! @param ptr The pointer to check for null
#define ASSERT(ptr) assert(ptr, __FILE__, __LINE__)

//! Malloc with failure check
//! @param size The size of the memory to allocate
#define MALLOC(size) malloc_check(size, __FILE__, __LINE__)

//! Terminate program if null pointer
//! @param ptr The pointer to check for null
//! @param file The name of the file it is called from
//! @param line The line number it is called from
void assert(void *ptr, const char *file, int line);

//! Malloc with failure check
//! @param size The size of the memory to allocate
//! @param file The name of the file it is called from
//! @param line The line number it is called from
void *malloc_check(uint16_t size, const char *file, int line);

//! Get current epoch in milliseconds
//! @return The current epoch time in milliseconds
uint64_t epoch(void);

//! ============================================================================
//! TEST_LOG: Structured logging for functional test assertions
//! ============================================================================
//!
//! PURPOSE:
//! This macro enables functional tests to verify app state by parsing log
//! output instead of using unreliable OCR on screenshots. Tests run
//! `pebble logs` to capture these structured log lines.
//!
//! WHY WRAP APP_LOG?
//! Currently this just calls APP_LOG, but wrapping it allows us to easily
//! disable test logging in production builds later by changing this one macro.
//!
//! TO DISABLE IN PRODUCTION (Option B - zero overhead):
//! Replace the #define below with:
//!   #ifdef TEST_BUILD
//!   #define TEST_LOG(level, fmt, ...) APP_LOG(level, fmt, ##__VA_ARGS__)
//!   #else
//!   #define TEST_LOG(level, fmt, ...) ((void)0)
//!   #endif
//! Then add -DTEST_BUILD to CFLAGS in wscript for emulator/test builds.
//!
#define TEST_LOG(level, fmt, ...) APP_LOG(level, fmt, ##__VA_ARGS__)

// Log current app state for functional test assertions
void test_log_state(const char *event);
