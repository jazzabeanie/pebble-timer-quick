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
//! TEST_LOGS:
//! The log output costs about 1.4KB of aplite's 24KB app region, which the
//! alarm-delivery code needs. So the aplite release build has no test logs
//! (TEST_LOGS is 0). A test build (`QT_TEST_BUILD=1 pebble build`, which
//! defines TEST_BUILD) has them on every platform. Every other platform keeps
//! them in the release build too. The app's behavior is the same with and
//! without them.
//!
#if defined(PBL_PLATFORM_APLITE) && !defined(TEST_BUILD)
  #define TEST_LOGS 0
#else
  #define TEST_LOGS 1
#endif

#if TEST_LOGS
#define TEST_LOG(level, fmt, ...) APP_LOG(level, fmt, ##__VA_ARGS__)

// Log current app state for functional test assertions
void test_log_state(const char *event);
#else
// The compiler still checks the format and counts the arguments as used, but
// the call is never run, so the call and its strings are not in the binary
#define TEST_LOG(level, fmt, ...) \
  do { if (0) { APP_LOG(level, fmt, ##__VA_ARGS__); } } while (0)

#define test_log_state(event) ((void)0)
#endif
