$('#logcount').hide();
var logs = $('#logs');
ws.on('logs', function(data) {
    if (data.entries != null)
        data.entries.forEach(function(a) {
            console.log(a);
        });
});