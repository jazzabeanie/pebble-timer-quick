var config = {};

function getOr(key, def) {
  return config.hasOwnProperty(key) ? config[key] : def;
}

function sendSettingsToWatch(attempt) {
  attempt = attempt || 0;
  Pebble.sendAppMessage(
    {
      '0':  getOr('show_increment_icons',    true) ? 1 : 0,
      '1':  getOr('show_direction_icon',     true) ? 1 : 0,
      '2':  getOr('show_quit_icon',          true) ? 1 : 0,
      '3':  getOr('show_to_bg_icon',         true) ? 1 : 0,
      '4':  getOr('show_edit_icon',          true) ? 1 : 0,
      '5':  getOr('show_play_pause_icon',    true) ? 1 : 0,
      '6':  getOr('show_details_icon',       true) ? 1 : 0,
      '7':  getOr('show_repeat_enable_icon', true) ? 1 : 0,
      '8':  getOr('show_alarm_reset_icon',   true) ? 1 : 0,
      '9':  getOr('show_silence_icon',       true) ? 1 : 0,
      '10': getOr('show_snooze_icon',        true)  ? 1 : 0,
      '12': getOr('swap_back_and_select_long', false) ? 1 : 0,
      '13': getOr('multiple_timers_enabled',   true)  ? 1 : 0
    },
    function() { console.log('QuickTimer: settings sent to watch'); },
    function(err) {
      console.log('QuickTimer: send error ' + JSON.stringify(err));
      if (attempt < 3) {
        setTimeout(function() { sendSettingsToWatch(attempt + 1); }, 1000);
      }
    }
  );
}

function loadConfig() {
  var stored = localStorage.getItem('config');
  if (stored) {
    try { config = JSON.parse(stored); } catch (e) { config = {}; }
  }
}

// On connect: phone is authoritative — push saved settings to watch.
Pebble.addEventListener('ready', function() {
  loadConfig();
  sendSettingsToWatch();
});

// Watch sends key 11 on startup to request settings.
// Respond with current stored settings (defaults if nothing stored yet).
Pebble.addEventListener('appmessage', function(e) {
  if (e.payload.hasOwnProperty('11')) {
    loadConfig();
    sendSettingsToWatch();
  }
});

Pebble.addEventListener('showConfiguration', function() {
  loadConfig();

  function toggle(id, checked) {
    return '<label class="toggle"><input type="checkbox" id="' + id + '"' +
      (checked ? ' checked' : '') + '><span class="slider"></span></label>';
  }
  function row(label, id) {
    return '<div class="row"><span>' + label + '</span>' + toggle(id, getOr(id, true)) + '</div>';
  }
  function rowOff(label, id) {
    return '<div class="row"><span>' + label + '</span>' + toggle(id, getOr(id, false)) + '</div>';
  }
  function section(title, rows) {
    return '<div class="section"><div class="section-title">' + title + '</div>' + rows + '</div>';
  }

  var html = [
    '<!DOCTYPE html><html><head>',
    '<meta name="viewport" content="width=device-width,initial-scale=1">',
    '<title>QuickTimer Settings</title>',
    '<style>',
    'body{font-family:sans-serif;margin:0;background:#f0f0f0;}',
    'h1{background:#00b0cc;color:#fff;margin:0;padding:14px 16px;font-size:20px;}',
    '.section{margin:16px 0;}',
    '.section-title{font-size:12px;font-weight:bold;color:#888;text-transform:uppercase;',
    '  padding:0 16px 6px;}',
    '.row{background:#fff;display:flex;justify-content:space-between;align-items:center;',
    '  padding:14px 16px;border-bottom:1px solid #eee;}',
    '.row:last-child{border-bottom:none;}',
    '.row span{font-size:15px;}',
    '.toggle{position:relative;display:inline-block;width:46px;height:26px;flex-shrink:0;}',
    '.toggle input{opacity:0;width:0;height:0;}',
    '.slider{position:absolute;cursor:pointer;inset:0;background:#ccc;',
    '  border-radius:26px;transition:.25s;}',
    '.slider:before{content:"";position:absolute;width:20px;height:20px;left:3px;bottom:3px;',
    '  background:#fff;border-radius:50%;transition:.25s;}',
    'input:checked+.slider{background:#00b0cc;}',
    'input:checked+.slider:before{transform:translateX(20px);}',
    'button{display:block;width:calc(100% - 32px);margin:8px auto 24px;padding:14px;',
    '  background:#00b0cc;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;}',
    '</style></head><body>',
    '<h1>QuickTimer Settings</h1>',

    section('General', [
      row('Multiple Timers', 'multiple_timers_enabled'),
    ].join('')),

    section('Edit Mode', [
      row('Increment Icons (+1, +5, +20, etc)', 'show_increment_icons'),
      row('Direction Toggle Icon',          'show_direction_icon'),
      rowOff('Swap Back / Select-Hold Buttons', 'swap_back_and_select_long'),
    ].join('')),

    section('Timer', [
      row('Edit Icon',          'show_edit_icon'),
      row('Play / Pause Icon',  'show_play_pause_icon'),
      row('Exit to Background Icon', 'show_to_bg_icon'),
      row('Details Icon',       'show_details_icon'),
      row('Repeat Toggle Icon', 'show_repeat_enable_icon'),
      row('Quit Icon',          'show_quit_icon'),
    ].join('')),

    section('Alarm', [
      row('Silence Icon',     'show_silence_icon'),
      row('Snooze Icon',      'show_snooze_icon'),
      row('Alarm Reset Icon', 'show_alarm_reset_icon'),
    ].join('')),

    '<button onclick="save()">Save</button>',
    '<script>',
    'function val(id){return document.getElementById(id).checked;}',
    'function save(){',
    '  var r={',
    '    show_increment_icons:   val("show_increment_icons"),',
    '    show_direction_icon:    val("show_direction_icon"),',
    '    show_quit_icon:         val("show_quit_icon"),',
    '    show_to_bg_icon:        val("show_to_bg_icon"),',
    '    show_edit_icon:         val("show_edit_icon"),',
    '    show_play_pause_icon:   val("show_play_pause_icon"),',
    '    show_details_icon:      val("show_details_icon"),',
    '    show_repeat_enable_icon:val("show_repeat_enable_icon"),',
    '    show_alarm_reset_icon:  val("show_alarm_reset_icon"),',
    '    show_silence_icon:      val("show_silence_icon"),',
    '    show_snooze_icon:       val("show_snooze_icon"),',
    '    swap_back_and_select_long: val("swap_back_and_select_long"),
    multiple_timers_enabled:   val("multiple_timers_enabled")',
    '  };',
    '  location.href="pebblejs://close#"+encodeURIComponent(JSON.stringify(r));',
    '}',
    '</script></body></html>'
  ].join('');

  Pebble.openURL('data:text/html,' + encodeURIComponent(html));
});

Pebble.addEventListener('webviewclosed', function(e) {
  if (!e.response || e.response === 'CANCELLED') { return; }
  try {
    config = JSON.parse(decodeURIComponent(e.response));
    localStorage.setItem('config', JSON.stringify(config));
    sendSettingsToWatch();
  } catch (err) {
    console.log('QuickTimer: error parsing config ' + err);
  }
});
