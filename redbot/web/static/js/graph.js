var loading = $('#loading');
var loadingbar = $('#loadingbar');
var scantime = 0;
var scanning = false;
loading.hide();

var cy = cytoscape({
    container: $('#cy'),
});

var options = {
  name: 'circle',

  fit: true, // whether to fit the viewport to the graph
  padding: 30, // the padding on fit
  boundingBox: undefined, // constrain layout bounds; { x1, y1, x2, y2 } or { x1, y1, w, h }
  avoidOverlap: true, // prevents node overlap, may overflow boundingBox and radius if not enough space
  nodeDimensionsIncludeLabels: false, // Excludes the label when calculating node bounding boxes for the layout algorithm
  spacingFactor: undefined, // Applies a multiplicative factor (>0) to expand or compress the overall area that the nodes take up
  radius: undefined, // the radius of the circle
  startAngle: 3 / 2 * Math.PI, // where nodes start in radians
  sweep: undefined, // how many radians should be between the first and last node (defaults to full circle)
  clockwise: true, // whether the layout should go clockwise (true) or counterclockwise/anticlockwise (false)
  sort: undefined, // a sorting function to order the nodes; e.g. function(a, b){ return a.data('weight') - b.data('weight') }
  animate: false, // whether to transition the node positions
  animationDuration: 500, // duration of animation in ms if enabled
  animationEasing: undefined, // easing of animation if enabled
  animateFilter: function ( node, i ){ return true; }, // a function that determines whether the node should be animated.  All nodes animated by default on animate enabled.  Non-animated nodes are positioned immediately when the layout starts
  ready: undefined, // callback on layoutready
  stop: undefined, // callback on layoutstop
  transform: function (node, position ){ return position; } // transform a given node position. Useful for changing flow direction in discrete layouts

};

$('#fit').click(function() {
    cy.layout( options ).run();
    cy.fit();
});

ws.on('hosts', function(data) {
    update_scantime(data.scantime);
    if (data.data == null)
        return;
    cy.destroy();
    init_graph();
    var table = $('#hosts tbody');
    table.empty();
    $.each(data.data, function(host, data) {
        graph_host([host, data.ports], data.target);
        table.append('<tr><td>' + data.target + '</td><td>' + host + '</td><td>' + parse_ports(data.ports) + '</td><td></td></tr>');
    });
});

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
                'label': b,
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

$('#forcescan').click(function() {
    scanning = true;
    $(this).fadeOut();
    ws.emit('run nmap');
    loading.show();
    cy.destroy();
    init_graph();
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

var targets = {};

ws.on('nmap progress', function(data) {
    if (data.status == 'PROGRESS') {
        targets[data.result.target] = parseInt(data.result.progress);
        scanning = true;
        loading.show();
        var total = Object.keys(targets).length * 100;
        var progress = 0;
        $.each(targets, function(a) {
            progress += parseInt(targets[a]);
        });
        loadingbar.attr('style', 'width: ' + 100 * progress / total + '%');
        $('#target').html("Scanning \"" + data.result.target + "\", " + (100 * progress / total).toFixed(2) + "% total");
    } else if (data.status == 'RESULTS') {
        data.result.hosts.forEach(graph_host, data.result.target);
        targets[data.result.target] = 100;
    } else if (data.status == 'SUCCESS') {
    }
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
        result += port;
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

ws.on('scan finished', function(a) {
    loading.hide();
    $('#target').html('');
    $('#forcescan').fadeIn();
    scanning = false;
});


get_hosts();
setInterval(get_hosts, 5000);
