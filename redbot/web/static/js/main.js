var ws = io.connect('//' + document.domain + ':' + location.port);
var messages = $('#messages');
var loading = $('#loading');
var loadingbar = $('#loadingbar');

messages.hide();
loading.hide();

function display_message(data) {
    messages.attr('class', 'alert alert-' + data.class);
    messages.html(data.content);
    messages.fadeIn();
    setTimeout(function () {
        messages.fadeOut();
    }, 5000);
}

ws.on('message', display_message);

ws.on('nmap progress', function(data) {
    if (data.status == 'PROGRESS') {
        loading.show();
        loadingbar.attr('style', 'width: ' + data.result.progress + '%');
        $('#target').html("Scanning \"" + data.result.target + "\"");
    } else if (data.status == 'SUCCESS') {
        loading.hide();
        $('#target').html('');
        $('#forcescan').fadeIn();
    }
});

$('#forcescan').click(function() {
    $(this).fadeOut();
    ws.emit('run nmap');
    loading.show();
});

ws.on('disconnect', function(data) {
    display_message({class: 'danger',
                     content: 'WebSocket disconnected.'});
});

ws.on('connect', function(data) {
    display_message({class: 'success',
        content: 'WebSocket connected.'});
});
