var ws = io.connect('//' + document.domain + ':' + location.port);
var messages = $('#messages');
var loading = $('#loading');
var loadingbar = $('#loadingbar');
var scantime = 0;
var scanning = false;

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

function graph_host(host, target) {
    cy.add({
        group: "nodes",
        data: {
            id: host[0],
            parent: target,
        },
        style: {
            'background-color': 'blue',
            'label': host[0],
        }
    });
    host[1].forEach(function(b) {
        cy.add({
            group: "nodes",
            data: {
                id: host[0] + b,
                parent: host[0]
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
                target: host[0],
            }
        }
    );

    cy.layout(options).run();
    cy.fit();
}

ws.on('nmap progress', function(data) {
    if (data.status == 'PROGRESS') {
        scanning = true;
        loading.show();
        loadingbar.attr('style', 'width: ' + data.result.progress + '%');
        $('#target').html("Scanning \"" + data.result.target + "\"");
    } else if (data.status == 'RESULTS') {
        data.result.hosts.forEach(graph_host, data.result.target);
    } else if (data.status == 'SUCCESS') {
        loading.hide();
        $('#target').html('');
        $('#forcescan').fadeIn();
        scanning = false;
    }
});

function init_graph() {
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
}

$('#forcescan').click(function() {
    scanning = true;
    $(this).fadeOut();
    ws.emit('run nmap');
    loading.show();
    cy.destroy();
    init_graph();
});

ws.on('disconnect', function(data) {
    display_message({class: 'danger',
        content: 'WebSocket disconnected.'});
});

ws.on('connect', function(data) {
    display_message({class: 'success',
        content: 'WebSocket connected.'});
});

function get_hosts() {
    if (!scanning)
        ws.emit('get hosts', {scantime: scantime});
}

function parse_ports(ports_list) {
    var result = "";
    ports_list.forEach(function(port) {
        if (result != "")
            result += ", ";
        result += port[0];
    });
    return result;
}

function update_scantime(unixtime) {
    scantime = unixtime;
    if (scantime > 0) {
        var d = new Date(unixtime * 1000);
        $('#lastscan').text(d.toDateString() + " " + d.toTimeString());
    }
}

ws.on('hosts', function(data) {
    console.log(data);
    update_scantime(data.scantime);
    if (data.data == null)
        return;
    cy.destroy();
    init_graph();
    var table = $('#hosts tbody');
    table.empty();
    $.each(data.data, function(target, hosts) {
        hosts.forEach(function(host) {
            graph_host(host, target);
            table.append('<tr><td>' + target + '</td><td>' + host[0] + '</td><td>' + parse_ports(host[1]) + '</td></tr>');
        });
    });
});

get_hosts();
setInterval(get_hosts, 5000);
