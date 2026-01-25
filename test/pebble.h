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

// Time
time_t time(time_t *tloc);
uint16_t time_ms(time_t *tloc, uint16_t *out_ms);

// Utils
#define ARRAY_LENGTH(array) (sizeof((array)) / sizeof((array)[0]))


