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
    } else if (data.status == 'RESULTS') {
        data.result.hosts.forEach(function(a) {
            cy.add({
                group: "nodes",
                data: {
                    id: a[0],
                    parent: data.result.target,
                },
                style: {
                    'background-color': 'blue',
                    'label': a[0],
                }
            });
            a[1].forEach(function(b) {
                cy.add({
                    group: "nodes",
                    data: {
                        id: a[0] + b,
                        parent: a[0]
                    },
                    style: {
                        'width': 20,
                        'height': 20,
                        'background-color': 'white',
                        'color': 'white',
                        'label': b[0],
                    }
                });
            });
            cy.add({
                    group: "edges",
                    data: {
                        source: "redbot",
                        target: a[0],
                    }
                }
            );

            cy.layout(options).run();
            cy.fit();
        });
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
    cy.destroy();
    cy = cytoscape({
        container: $('#cy'),
    });
    cy.add({
        group: "nodes",
        position: {
            x: 0,
            y: 0,
        },
        data: {
            id: "redbot",
        },
        style: {
            'background-color': 'red',
            'shape': 'vee',
            'label': 'redbot',
        }
    });
});

ws.on('disconnect', function(data) {
    display_message({class: 'danger',
        content: 'WebSocket disconnected.'});
});

ws.on('connect', function(data) {
    display_message({class: 'success',
        content: 'WebSocket connected.'});
});
