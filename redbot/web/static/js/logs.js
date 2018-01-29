logcount.hide();
var logs = $('#logs');

ws.on('logs', function(data) {
    if (data.entries != null)
        data.entries.forEach(function(a) {
            logs.prepend('<div class="card"><div class="card-header">' + new Date(a.time * 1000) + '</div><div class="card-body text-' + a.style + '"><h5 class="card-title">' + a.tag + '</h5>' + a.text + '</div></div>').fadeIn();
        });
});

$('.unftime').each(function() {
    $(this).html(new Date(1000 * parseInt($(this).html())));
})