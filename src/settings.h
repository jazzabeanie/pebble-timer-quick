#pragma once
#include <pebble.h>

typedef void (*SettingsChangeCallback)(void);

void settings_init(SettingsChangeCallback on_change);
void settings_save(void);
bool settings_get_show_increment_icons(void);
