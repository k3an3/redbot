function update_setting(obj, val) {
    var m = obj.attr('id').split('-');
    ws.emit('settings', {
        module: m[0],
        key: m[1],
        value: val,
    });
}

$('.form-control').on('blur', function() {
    update_setting($(this), $(this).val());
});

$('.form-check-input').change(function() {
    update_setting($(this), this.checked);
});

$('.testattack').click(function() {
    ws.emit('admin', {
        command: 'testattack',
        attack: $(this).attr('id').split('-')[1]
    });
});

$('#redbot button').click(function() {
    ws.emit('admin', {
        command: $(this).attr('id')
    });
});
