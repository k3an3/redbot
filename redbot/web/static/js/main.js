var ws = io.connect('//' + document.domain + ':' + location.port);
var messages = $('#messages');

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
    display_message({class: 'danger',
        content: 'WebSocket disconnected.'});
});

ws.on('connect', function(data) {
    display_message({class: 'success',
        content: 'WebSocket connected.'});
});

