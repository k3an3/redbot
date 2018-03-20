from flask_socketio import emit

from redbot.core.configparser import parse
from redbot.core.models import modules, storage
from redbot.core.utils import get_class, log, restart_redbot, set_core_setting, get_random_attack, NoTargetsError
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
            send_msg("There was an error updating settings.", "danger")
            log(str(e), style="danger")
        else:
            send_msg("Settings updated.", "success")
    elif data['module'] == 'redbot.core':
        try:
            set_core_setting(data['key'], data['value'])
        except Exception as e:
            raise e
            send_msg("There was an error updating settings.", "danger")
            log(str(e), style="danger")
        else:
            send_msg("Settings updated.", "success")
    else:
        send_msg("Selected module does not exist.", "warning")


@socketio.on('admin')
def admin_ws(data):
    command = data['command']
    if command == 'restart':
        restart_redbot()
    elif command == 'clear':
        from redbot.modules.discovery import clear_targets
        clear_targets()
        send_msg("Targets cleared.", "warning")
        log("Targets cleared.", style="warning")
    elif command == 'clearlogs':
        storage.delete('log')
        send_msg("Logs cleared.", "warning")
    elif command == 'testattack':
        if data.get('attack'):
            r = get_class(data['attack'])
        else:
            r = get_random_attack()
        try:
            result, targets = r.run_attack()
        except NoTargetsError:
            send_msg("There are no hosts to target! Ensure that discovery is properly configured and has been run "
                     "first.", "danger")
            log("Test attack {} failed with no hosts to target.".format(r.name), style="danger")
        except Exception as e:
            send_msg("Failed running attack module '{}': {}".format(r.name, e), "danger")
            log("Test attack {} failed with {}".format(r.name, e), style="danger")
        else:
            send_msg("Running attack module '{}' against {} targets.".format(r.name, len(targets)), "success")
    elif command == 'reload':
        parse('config.yml')


@socketio.on('run nmap')
def nmap():
    from redbot.modules.discovery import do_discovery
    log("Discovery scan invoked from web.", "web")
    send_msg("Running scan.")
    do_discovery(force=True)


@socketio.on('get hosts')
def get_hosts_ws(data):
    from redbot.modules.discovery import get_last_scan, get_last_update, get_hosts
    last_scan = max(get_last_scan(), get_last_update())
    if data['scantime'] < last_scan:
        emit('hosts', {'data': get_hosts(), 'scantime': last_scan})
    else:
        emit('hosts', {'data': None, 'scantime': last_scan})
