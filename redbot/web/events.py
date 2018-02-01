from flask_socketio import emit

from redbot.core.models import modules
from redbot.core.utils import get_class, log, restart_redbot
from redbot.web.web import socketio, send_msg


@socketio.on('settings')
def settings_ws(data):
    if data['module'] in modules:
        try:
            cls = get_class(data['module'])
        except (AttributeError, ImportError):
            send_msg("Settings for that module cannot be modified.", "warning")
            return
        try:
            cls.set_setting(data['key'], data['value'])
        except Exception as e:
            raise e
            send_msg("There was an error updating settings.", "danger")
            log(str(e), style="danger")
        else:
            send_msg("Settings updated.", "success")


@socketio.on('admin')
def admin_ws(data):
    if data['command'] == 'restart':
        restart_redbot()


@socketio.on('run nmap')
def nmap():
    from redbot.modules.nmap import NmapScan
    log("Nmap scan invoked from web.", "web")
    send_msg("Running scan.")
    NmapScan.run_scans()


@socketio.on('get hosts')
def get_hosts_ws(data):
    from redbot.modules.nmap import get_last_scan, get_targets
    last_scan = get_last_scan()
    if data['scantime'] < last_scan:
        emit('hosts', {'data': get_targets(), 'scantime': last_scan})
    else:
        emit('hosts', {'data': None, 'scantime': last_scan})