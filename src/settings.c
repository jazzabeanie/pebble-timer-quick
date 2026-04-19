#include <pebble.h>
#include "settings.h"

#define PERSIST_SETTINGS_VERSION 2
#define PERSIST_SETTINGS_VERSION_KEY 4342897
#define PERSIST_SETTINGS_KEY 58737

#define APPMSG_KEY_SHOW_INCREMENT_ICONS    0
#define APPMSG_KEY_SHOW_DIRECTION_ICON     1
#define APPMSG_KEY_SHOW_QUIT_ICON          2
#define APPMSG_KEY_SHOW_TO_BG_ICON         3
#define APPMSG_KEY_SHOW_EDIT_ICON          4
#define APPMSG_KEY_SHOW_PLAY_PAUSE_ICON    5
#define APPMSG_KEY_SHOW_DETAILS_ICON       6
#define APPMSG_KEY_SHOW_REPEAT_ENABLE_ICON 7
#define APPMSG_KEY_SHOW_ALARM_RESET_ICON   8
#define APPMSG_KEY_SHOW_SILENCE_ICON       9
#define APPMSG_KEY_SHOW_SNOOZE_ICON        10

typedef struct {
  bool show_increment_icons;
  bool show_direction_icon;
  bool show_quit_icon;
  bool show_to_bg_icon;
  bool show_edit_icon;
  bool show_play_pause_icon;
  bool show_details_icon;
  bool show_repeat_enable_icon;
  bool show_alarm_reset_icon;
  bool show_silence_icon;
  bool show_snooze_icon;
} AppSettings;

static AppSettings s_settings;
static SettingsChangeCallback s_change_callback;

static void prv_send_to_phone(void) {
  DictionaryIterator *iter;
  if (app_message_outbox_begin(&iter) != APP_MSG_OK) { return; }
  dict_write_int8(iter, APPMSG_KEY_SHOW_INCREMENT_ICONS,    s_settings.show_increment_icons    ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_DIRECTION_ICON,     s_settings.show_direction_icon     ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_QUIT_ICON,          s_settings.show_quit_icon          ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_TO_BG_ICON,         s_settings.show_to_bg_icon         ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_EDIT_ICON,          s_settings.show_edit_icon          ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_PLAY_PAUSE_ICON,    s_settings.show_play_pause_icon    ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_DETAILS_ICON,       s_settings.show_details_icon       ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_REPEAT_ENABLE_ICON, s_settings.show_repeat_enable_icon ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_ALARM_RESET_ICON,   s_settings.show_alarm_reset_icon   ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_SILENCE_ICON,       s_settings.show_silence_icon       ? 1 : 0);
  dict_write_int8(iter, APPMSG_KEY_SHOW_SNOOZE_ICON,        s_settings.show_snooze_icon        ? 1 : 0);
  app_message_outbox_send();
}

static void prv_inbox_received(DictionaryIterator *iterator, void *context) {
  bool changed = false;
  Tuple *t;

  #define HANDLE(key, field) \
    t = dict_find(iterator, key); \
    if (t) { s_settings.field = (bool)t->value->int32; changed = true; }

  HANDLE(APPMSG_KEY_SHOW_INCREMENT_ICONS,    show_increment_icons)
  HANDLE(APPMSG_KEY_SHOW_DIRECTION_ICON,     show_direction_icon)
  HANDLE(APPMSG_KEY_SHOW_QUIT_ICON,          show_quit_icon)
  HANDLE(APPMSG_KEY_SHOW_TO_BG_ICON,         show_to_bg_icon)
  HANDLE(APPMSG_KEY_SHOW_EDIT_ICON,          show_edit_icon)
  HANDLE(APPMSG_KEY_SHOW_PLAY_PAUSE_ICON,    show_play_pause_icon)
  HANDLE(APPMSG_KEY_SHOW_DETAILS_ICON,       show_details_icon)
  HANDLE(APPMSG_KEY_SHOW_REPEAT_ENABLE_ICON, show_repeat_enable_icon)
  HANDLE(APPMSG_KEY_SHOW_ALARM_RESET_ICON,   show_alarm_reset_icon)
  HANDLE(APPMSG_KEY_SHOW_SILENCE_ICON,       show_silence_icon)
  HANDLE(APPMSG_KEY_SHOW_SNOOZE_ICON,        show_snooze_icon)

  #undef HANDLE

  if (changed) {
    settings_save();
    if (s_change_callback) { s_change_callback(); }
  }
}

bool settings_get_show_increment_icons(void)    { return s_settings.show_increment_icons; }
bool settings_get_show_direction_icon(void)     { return s_settings.show_direction_icon; }
bool settings_get_show_quit_icon(void)          { return s_settings.show_quit_icon; }
bool settings_get_show_to_bg_icon(void)         { return s_settings.show_to_bg_icon; }
bool settings_get_show_edit_icon(void)          { return s_settings.show_edit_icon; }
bool settings_get_show_play_pause_icon(void)    { return s_settings.show_play_pause_icon; }
bool settings_get_show_details_icon(void)       { return s_settings.show_details_icon; }
bool settings_get_show_repeat_enable_icon(void) { return s_settings.show_repeat_enable_icon; }
bool settings_get_show_alarm_reset_icon(void)   { return s_settings.show_alarm_reset_icon; }
bool settings_get_show_silence_icon(void)       { return s_settings.show_silence_icon; }
bool settings_get_show_snooze_icon(void)        { return s_settings.show_snooze_icon; }

void settings_save(void) {
  persist_write_int(PERSIST_SETTINGS_VERSION_KEY, PERSIST_SETTINGS_VERSION);
  persist_write_data(PERSIST_SETTINGS_KEY, &s_settings, sizeof(s_settings));
}

void settings_init(SettingsChangeCallback on_change) {
  s_change_callback = on_change;
  s_settings = (AppSettings){
    .show_increment_icons    = true,
    .show_direction_icon     = true,
    .show_quit_icon          = true,
    .show_to_bg_icon         = true,
    .show_edit_icon          = true,
    .show_play_pause_icon    = true,
    .show_details_icon       = true,
    .show_repeat_enable_icon = true,
    .show_alarm_reset_icon   = true,
    .show_silence_icon       = true,
    .show_snooze_icon        = true,
  };
  if (persist_read_int(PERSIST_SETTINGS_VERSION_KEY) == PERSIST_SETTINGS_VERSION &&
      persist_exists(PERSIST_SETTINGS_KEY)) {
    persist_read_data(PERSIST_SETTINGS_KEY, &s_settings, sizeof(s_settings));
  }
  app_message_register_inbox_received(prv_inbox_received);
  app_message_open(128, 128);
  prv_send_to_phone();
}
