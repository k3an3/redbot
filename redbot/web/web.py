import importlib

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

from redbot import settings
from redbot.core.models import modules
from redbot.core.utils import get_log, log, get_class

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/settings')
def settings():
    module_settings = []
    for module in modules:
        try:
            cls = get_class(module)
            s = cls.get_settings()
            for setting in cls.settings:
                try:
                    cls.settings[setting].update({'value': s.get(setting)})
                except (TypeError, ValueError):
                    pass
            print(cls.settings)
            module_settings.append((module, cls.settings))
        except (AttributeError, ImportError) as e:
            raise e
    return render_template('settings.html', modules=module_settings)


@app.route('/logs')
def logs():
    count = request.args.get('count', 20)
    return render_template('logs.html', logs=get_log(count))


@socketio.on('settings')
def settings_ws(data):
    if data['module'] in modules:
        print(data)
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


def send_msg(message: str, alert: str = 'info') -> None:
    socketio.emit('message', {'class': alert, 'content': message}, broadcast=True)


@app.route('/message')
def msg():
    send_msg(request.args['m'])
    return '', 204


if __name__ == '__main__':
    app.run(debug=True)
