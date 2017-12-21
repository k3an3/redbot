from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

from redbot import settings

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template('index.html')


@socketio.on("run nmap")
def nmap():
    from redbot.modules.nmap import run_scans
    emit('message', {'class': 'info', 'content': 'Running scan.'})
    run_scans()


def send_msg(message: str, alert: str = 'info') -> None:
    socketio.emit('message', {'class': alert, 'content': message}, broadcast=True)


@app.route('/message')
def msg():
    send_msg(request.args['m'])
    return '', 204


if __name__ == "__main__":
    app.run(debug=True)
