var config = {};

Pebble.addEventListener('ready', function() {
  var stored = localStorage.getItem('config');
  if (stored) {
    try { config = JSON.parse(stored); } catch (e) {}
  }
});

Pebble.addEventListener('appmessage', function(e) {
  if (e.payload.hasOwnProperty('0')) {
    config.show_increment_icons = e.payload['0'] === 1;
    localStorage.setItem('config', JSON.stringify(config));
  }
});

Pebble.addEventListener('showConfiguration', function() {
  var showIcons = config.show_increment_icons !== false;

  var html = [
    '<!DOCTYPE html><html>',
    '<head>',
    '<meta name="viewport" content="width=device-width,initial-scale=1">',
    '<title>QuickTimer Settings</title>',
    '<style>',
    'body{font-family:sans-serif;margin:0;background:#f5f5f5;}',
    'h1{background:#00b0cc;color:#fff;margin:0;padding:16px;font-size:20px;}',
    '.row{background:#fff;display:flex;justify-content:space-between;align-items:center;',
    '  padding:16px;margin:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);}',
    '.row span{font-size:16px;}',
    '.toggle{position:relative;display:inline-block;width:50px;height:28px;}',
    '.toggle input{opacity:0;width:0;height:0;}',
    '.slider{position:absolute;cursor:pointer;inset:0;background:#ccc;',
    '  border-radius:28px;transition:.3s;}',
    '.slider:before{content:"";position:absolute;width:22px;height:22px;left:3px;bottom:3px;',
    '  background:#fff;border-radius:50%;transition:.3s;}',
    'input:checked+.slider{background:#00b0cc;}',
    'input:checked+.slider:before{transform:translateX(22px);}',
    'button{display:block;width:calc(100% - 32px);margin:16px auto;padding:14px;',
    '  background:#00b0cc;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;}',
    '</style></head>',
    '<body>',
    '<h1>QuickTimer Settings</h1>',
    '<div class="row">',
    '  <span>Increment Icons</span>',
    '  <label class="toggle">',
    '    <input type="checkbox" id="icons"' + (showIcons ? ' checked' : '') + '>',
    '    <span class="slider"></span>',
    '  </label>',
    '</div>',
    '<button onclick="save()">Save</button>',
    '<script>',
    'function save(){',
    '  var r={show_increment_icons:document.getElementById("icons").checked};',
    '  location.href="pebblejs://close#"+encodeURIComponent(JSON.stringify(r));',
    '}',
    '</script>',
    '</body></html>'
  ].join('');

  Pebble.openURL('data:text/html,' + encodeURIComponent(html));
});

Pebble.addEventListener('webviewclosed', function(e) {
  if (!e.response || e.response === 'CANCELLED') { return; }
  try {
    var result = JSON.parse(decodeURIComponent(e.response));
    config = result;
    localStorage.setItem('config', JSON.stringify(config));
    Pebble.sendAppMessage(
      { '0': result.show_increment_icons ? 1 : 0 },
      function() { console.log('QuickTimer: settings sent'); },
      function(err) { console.log('QuickTimer: send error ' + JSON.stringify(err)); }
    );
  } catch (err) {
    console.log('QuickTimer: error parsing config ' + err);
  }
});
