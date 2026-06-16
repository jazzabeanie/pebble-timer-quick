#pragma once
#include <pebble.h>

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
