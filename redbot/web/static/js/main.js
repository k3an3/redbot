var ws = io.connect('//' + document.domain + ':' + location.port);
var messages = $('#messages');
var logcount = $('#logcount');
var lastwsstate = true;

messages.hide();

function display_message(data) {
    messages.attr('class', 'alert alert-' + data.class);
    messages.html(data.content);
    messages.fadeIn();
    setTimeout(function () {
        messages.fadeOut();
    }, 5000);
}

ws.on('message', display_message);

ws.on('disconnect', function(data) {
    lastwsstate = false;
    display_message({class: 'danger',
        content: 'WebSocket disconnected.'});
});

ws.on('connect', function(data) {
    if (!lastwsstate)
        display_message({class: 'success',
            content: 'WebSocket reconnected.'});
    lastwsstate = true;
});

ws.on('logs', function() {
    logcount.html(parseInt(logcount.html()) + 1);
});