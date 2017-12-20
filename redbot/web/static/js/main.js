var ws = io.connect('//' + document.domain + ':' + location.port);
var messages = $('#messages');
var loading = $('#loading');
var loadingbar = $('#loadingbar');

messages.hide();
loading.hide();

ws.on('message', function(data) {
    console.log(data);
    messages.addClass(data.class);
    messages.html(data.content);
    messages.fadeIn();
    setTimeout(function () {
        messages.fadeOut();
    }, 5000);
});

ws.on('nmap progress', function(data) {
    console.log(data);
    if (data.status == 'PROGRESS') {
        loading.show();
        loadingbar.attr('style', 'width: ' + data.result + '%');
    } else if (data.status == 'SUCCESS') {
        loading.hide();
    }
});
