// Generated by CoffeeScript 1.8.0
(function() {
  var add_info, commands;

  add_info = function(m, cls) {
    var dot;
    $('table.last').parent().find('p.query_info').remove();
    $('table.last').after($('<p>', {
      "class": 'query_info ' + cls
    }).text(m));
    if (cls === 'searching') {
      dot = function() {
        var $s;
        $s = $('p.searching');
        if ($s.size()) {
          $s.text(($s.text() + '.').replace('....', ''));
          return setTimeout(dot, 500);
        }
      };
      return dot();
    }
  };

  commands = {
    INFO: function(m) {
      return console.log(m);
    },
    VISIT: function(m) {
      var $line;
      $line = $(m);
      $line.addClass('recent');
      $('table.last tbody').append($line);
      setTimeout((function() {
        return $line.removeClass('recent');
      }), 500);
      $('header h1 a').addClass('pulse');
      return setTimeout((function() {
        return $('header h1 a').removeClass('pulse');
      }), 75);
    },
    PAUSE: function(m) {
      return add_info(m, 'paused');
    },
    BEGIN: function(m) {
      return add_info(m, 'searching');
    },
    BUSY: function(m) {
      return add_info(m, 'busy');
    },
    END: function(m) {
      if (m.indexOf('Done') === 0) {
        return add_info(m, 'done');
      } else {
        return add_info(m, 'error');
      }
    }
  };

  $(function() {
    var criterion, host, query_ws, value;
    if (!$('.criterion').size() || !_query_criterion || !_query_value) {
      return;
    }
    criterion = _query_criterion;
    value = _query_value;
    host = location.host;
    if (host.indexOf(':')) {
      host = host.split(':')[0];
    }
    window.query_ws = query_ws = new WebSocket("" + (location.protocol === 'https:' ? 'wss' : 'ws') + "://" + host + ":" + window._pystil_port + "/query");
    query_ws.onopen = function() {
      console.log('Websocket opened', arguments);
      return query_ws.send("criterion|" + criterion + "|" + value);
    };
    query_ws.onerror = function() {
      return console.log('Websocket errored', arguments);
    };
    query_ws.onmessage = function(evt) {
      var cmd, data, message, pipe;
      message = evt.data;
      pipe = message.indexOf('|');
      if (pipe > -1) {
        cmd = message.substr(0, pipe);
        data = message.substr(pipe + 1);
        return commands[cmd](data);
      }
    };
    add_info('Initializing', 'init');
    return $(window).scroll(function() {
      if ($(window).scrollTop() + $(window).height() === $(document).height()) {
        if ($('p.paused').size()) {
          add_info('Searching...', 'searching');
          return query_ws.send('more');
        }
      }
    });
  });

}).call(this);
