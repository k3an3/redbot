from typing import Dict

from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, login_required, logout_user
from flask_socketio import SocketIO
from peewee import DoesNotExist

from redbot import settings
from redbot.core.models import modules, User
from redbot.core.utils import get_log, get_class, get_core_settings
from redbot.settings import LDAP_HOST

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins=[])
login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/settings')
def settings():
    module_settings = [('redbot.core', get_core_settings(), None, False)]
    for module in modules:
        try:
            cls = get_class(module)
            module_settings.append((module, cls.merge_settings(), cls.notes, cls.test))
        except (AttributeError, ImportError) as e:
            raise e
    return render_template('settings.html', modules=module_settings)


@app.route('/logs')
def logs():
    count = request.args.get('count', 20)
    return render_template('logs.html', logs=get_log(count))


def send_msg(message: str, alert: str = 'info') -> None:
    socketio.emit('message', {'class': alert, 'content': message}, broadcast=True)


@app.route('/message')
def msg():
    send_msg(request.args['m'])
    return '', 204


@app.template_filter('format_setting')
def format_setting(module: str, name: str, setting: Dict):
    desc = ''
    if type(setting.get('default')) == bool or type(setting.get('default')) == str and \
            setting['default'].lower() in ['true', 'false']:
        if 'description' in setting:
            desc = '<small class="form-text text-muted">{}</small>'.format(setting['description'])
        return """<div class="form-check">
        <input class="form-check-input" type="checkbox" id="{module}-{setting}" {checked}>
        <label for="{module}-{setting}">{name}</label>{desc}</div>""".format(
            module=module, setting=name,
            name=setting.get('name', name),
            checked='checked' if setting.get('value', setting['default']) not in [False, 'False'] else '',
            desc=desc)
    else:
        if 'description' in setting:
            desc = '<small class="form-text text-muted">{}</small>'.format(setting['description'])
        return """<div class="form-group"> <label for="{module}-{setting}">{name}</label> <input class="form-control" 
        type="{type}" id="{module}-{setting}" placeholder="{default}" value="{value}">{desc}</div>""".format(
            module=module,
            setting=name,
            name=setting.get(
                'name',
                name),
            default=setting[
                'default'],
            value='****************' if 'password' in name.lower() else setting.get(
                'value') or '',
            desc=desc,
            type='password' if 'password' in name.lower() else 'text'
        )


@login_manager.user_loader
def load_user(user_id):
    return User.get(id=user_id)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    created = False
    try:
        user = User.get(username=username)
    except DoesNotExist:
        if LDAP_HOST:
            user = ldap_auth(username, password)
            created = True
    if user:
        if created or user.check_password(password):
            login_user(user)
            flash('Logged in successfully.')
    if not user:
        flash('Invalid credentials.')
    return redirect('/')
