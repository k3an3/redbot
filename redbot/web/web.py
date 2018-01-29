from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

from redbot import settings
from redbot.models import modules
from redbot.utils import get_log, log

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/settings')
def settings():
    return render_template('settings.html', modules=modules)


@app.route('/logs')
def logs():
    return render_template('logs.html', logs=get_log(20))


@socketio.on('run nmap')
def nmap():
    log("Nmap scan invoked from web.", "web")
    from redbot.modules.nmap import run_scans
    send_msg("Running scan.")
    run_scans()


@socketio.on('get hosts')
def get_hosts_ws(data):
    from redbot.modules.nmap import get_last_scan, get_hosts
    last_scan = get_last_scan()
    if data['scantime'] < last_scan:
        emit('hosts', {'data': get_hosts(), 'scantime': last_scan})
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
