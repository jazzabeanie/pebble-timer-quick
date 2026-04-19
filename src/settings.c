#include <pebble.h>
#include "settings.h"

#define PERSIST_SETTINGS_VERSION 1
#define PERSIST_SETTINGS_VERSION_KEY 4342897
#define PERSIST_SETTINGS_KEY 58737

#define APPMSG_KEY_SHOW_INCREMENT_ICONS 0

typedef struct {
  bool show_increment_icons;
} AppSettings;

static AppSettings s_settings;
static SettingsChangeCallback s_change_callback;

static void prv_send_to_phone(void) {
  DictionaryIterator *iter;
  if (app_message_outbox_begin(&iter) != APP_MSG_OK) { return; }
  dict_write_int8(iter, APPMSG_KEY_SHOW_INCREMENT_ICONS,
                  s_settings.show_increment_icons ? 1 : 0);
  app_message_outbox_send();
}

static void prv_inbox_received(DictionaryIterator *iterator, void *context) {
  Tuple *t = dict_find(iterator, APPMSG_KEY_SHOW_INCREMENT_ICONS);
  if (t) {
    s_settings.show_increment_icons = (bool)t->value->int32;
    settings_save();
    if (s_change_callback) {
      s_change_callback();
    }
  }
}

bool settings_get_show_increment_icons(void) {
  return s_settings.show_increment_icons;
}

void settings_save(void) {
  persist_write_int(PERSIST_SETTINGS_VERSION_KEY, PERSIST_SETTINGS_VERSION);
  persist_write_data(PERSIST_SETTINGS_KEY, &s_settings, sizeof(s_settings));
}

void settings_init(SettingsChangeCallback on_change) {
  s_change_callback = on_change;
  s_settings.show_increment_icons = true;
  if (persist_read_int(PERSIST_SETTINGS_VERSION_KEY) == PERSIST_SETTINGS_VERSION &&
      persist_exists(PERSIST_SETTINGS_KEY)) {
    persist_read_data(PERSIST_SETTINGS_KEY, &s_settings, sizeof(s_settings));
  }
  app_message_register_inbox_received(prv_inbox_received);
  app_message_open(64, 32);
  prv_send_to_phone();
}
