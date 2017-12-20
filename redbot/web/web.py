from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

from redbot import settings

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template('index.html')


def push_update(body):
    print(body)
    socketio.emit('nmap progress', body, broadcast=True)


@app.route("/nmaptest")
def nmap():
    from redbot.modules.nmap import nmap_scan
    r = nmap_scan.delay('192.168.1.0/24')
    r.get(on_message=push_update, propagate=False)
    return '', 291


@app.route('/message')
def msg():
    socketio.emit('message', {'class': 'alert-info', 'content': request.args['m']}, broadcast=True)
    return '', 204


if __name__ == "__main__":
    app.run(debug=True)
