var sidebar = $('.sidebar .nav-item a');

sidebar.click(function() {
    sidebar.removeClass('active');
    $(this).addClass('active');
});

$('input').on('blur', function() {
    var m = $(this).attr('id').split('-');
    ws.emit('settings', {
        module: m[0],
        key: m[1],
        value: $(this).val(),
    });
});

