var config = {};

Pebble.addEventListener('ready', function() {
  var stored = localStorage.getItem('config');
  if (stored) {
    try { config = JSON.parse(stored); } catch (e) {}
  }
});

Pebble.addEventListener('appmessage', function(e) {
  var p = e.payload;
  if (p.hasOwnProperty('0'))  { config.show_increment_icons    = p['0']  === 1; }
  if (p.hasOwnProperty('1'))  { config.show_direction_icon     = p['1']  === 1; }
  if (p.hasOwnProperty('2'))  { config.show_quit_icon          = p['2']  === 1; }
  if (p.hasOwnProperty('3'))  { config.show_to_bg_icon         = p['3']  === 1; }
  if (p.hasOwnProperty('4'))  { config.show_edit_icon          = p['4']  === 1; }
  if (p.hasOwnProperty('5'))  { config.show_play_pause_icon    = p['5']  === 1; }
  if (p.hasOwnProperty('6'))  { config.show_details_icon       = p['6']  === 1; }
  if (p.hasOwnProperty('7'))  { config.show_repeat_enable_icon = p['7']  === 1; }
  if (p.hasOwnProperty('8'))  { config.show_alarm_reset_icon   = p['8']  === 1; }
  if (p.hasOwnProperty('9'))  { config.show_silence_icon       = p['9']  === 1; }
  if (p.hasOwnProperty('10')) { config.show_snooze_icon        = p['10'] === 1; }
  localStorage.setItem('config', JSON.stringify(config));
});

function getOr(key, def) {
  return config.hasOwnProperty(key) ? config[key] : def;
}

Pebble.addEventListener('showConfiguration', function() {
  function toggle(id, checked) {
    return '<label class="toggle"><input type="checkbox" id="' + id + '"' +
      (checked ? ' checked' : '') + '><span class="slider"></span></label>';
  }
  function row(label, id, checked) {
    return '<div class="row"><span>' + label + '</span>' + toggle(id, checked) + '</div>';
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

    section('Edit Mode', [
      row('Increment Icons (+1, +5, +20…)', 'show_increment_icons', getOr('show_increment_icons', true)),
      row('Direction Toggle Icon',          'show_direction_icon',  getOr('show_direction_icon',  true)),
    ].join('')),

    section('Timer', [
      row('Edit Icon',          'show_edit_icon',          getOr('show_edit_icon',          true)),
      row('Play / Pause Icon',  'show_play_pause_icon',    getOr('show_play_pause_icon',    true)),
      row('Exit to Background', 'show_to_bg_icon',         getOr('show_to_bg_icon',         true)),
      row('Details Icon',       'show_details_icon',       getOr('show_details_icon',       true)),
      row('Repeat Toggle Icon', 'show_repeat_enable_icon', getOr('show_repeat_enable_icon', true)),
      row('Quit Icon',          'show_quit_icon',          getOr('show_quit_icon',          true)),
    ].join('')),

    section('Alarm', [
      row('Silence Icon',     'show_silence_icon',      getOr('show_silence_icon',      true)),
      row('Snooze Icon',      'show_snooze_icon',        getOr('show_snooze_icon',        true)),
      row('Alarm Reset Icon', 'show_alarm_reset_icon',   getOr('show_alarm_reset_icon',   true)),
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
    '    show_snooze_icon:       val("show_snooze_icon")',
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
    var result = JSON.parse(decodeURIComponent(e.response));
    config = result;
    localStorage.setItem('config', JSON.stringify(config));
    Pebble.sendAppMessage({
      '0':  result.show_increment_icons    ? 1 : 0,
      '1':  result.show_direction_icon     ? 1 : 0,
      '2':  result.show_quit_icon          ? 1 : 0,
      '3':  result.show_to_bg_icon         ? 1 : 0,
      '4':  result.show_edit_icon          ? 1 : 0,
      '5':  result.show_play_pause_icon    ? 1 : 0,
      '6':  result.show_details_icon       ? 1 : 0,
      '7':  result.show_repeat_enable_icon ? 1 : 0,
      '8':  result.show_alarm_reset_icon   ? 1 : 0,
      '9':  result.show_silence_icon       ? 1 : 0,
      '10': result.show_snooze_icon        ? 1 : 0
    },
    function() { console.log('QuickTimer: settings sent'); },
    function(err) { console.log('QuickTimer: send error ' + JSON.stringify(err)); });
  } catch (err) {
    console.log('QuickTimer: error parsing config ' + err);
  }
});
