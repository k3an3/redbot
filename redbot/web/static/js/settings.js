var sidebar = $('.sidebar .nav-item a');

sidebar.click(function() {
    sidebar.removeClass('active');
    $(this).addClass('active');
});

function update_setting(obj, val) {
    var m = obj.attr('id').split('-');
    ws.emit('settings', {
        module: m[0],
        key: m[1],
        value: val,
    });
}

$('input').on('blur', function() {
    update_setting($(this), $(this).val());
});

$('checkbox').change(function() {
    update_setting($(this), this.checked);
});

$('#restart').click(function() {
    ws.emit('admin', {
        command: 'restart',
    })
})

ws.on('logs', function() {
    logcount.html(parseInt(logcount.html()) + 1);
});
