#pragma once
#include <pebble.h>

// Settings sync with the phone (the AppMessage inbox). It cannot work on
// aplite: the inbox needs about 8KB of heap and aplite has about 2KB, so
// app_message_open() fails there. The code is left out on aplite, which runs
// with the default settings (or with saved settings, if any exist).
#ifndef PBL_PLATFORM_APLITE
  #define SETTINGS_SYNC_FEATURE 1
#else
  #define SETTINGS_SYNC_FEATURE 0
#endif

typedef void (*SettingsChangeCallback)(void);

void settings_init(SettingsChangeCallback on_change);
void settings_save(void);

bool settings_get_show_increment_icons(void);
bool settings_get_show_direction_icon(void);
bool settings_get_show_quit_icon(void);
bool settings_get_show_to_bg_icon(void);
bool settings_get_show_edit_icon(void);
bool settings_get_show_play_pause_icon(void);
bool settings_get_show_details_icon(void);
bool settings_get_show_repeat_enable_icon(void);
bool settings_get_show_alarm_reset_icon(void);
bool settings_get_show_silence_icon(void);
bool settings_get_show_snooze_icon(void);
bool settings_get_swap_back_and_select_long(void);
bool settings_get_multiple_timers_enabled(void);
bool settings_get_voice_naming_enabled(void);
bool settings_get_lap_stopwatch_enabled(void);

//! Seconds the display stays in high-refresh (showing live seconds) after any
//! interaction before dropping to a lower refresh rate. Default 10.
uint32_t settings_get_screen_on_seconds(void);
//! Additional seconds the display stays in high-refresh after a Down press in
//! the running-timer view. 0 disables the extension. Default 60.
uint32_t settings_get_down_extra_seconds(void);
