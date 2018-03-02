import importlib
import json
import os
import random
import subprocess
from time import time
from typing import List, Any, Dict

from redbot.core.configparser import parse
from redbot.core.models import modules, storage, targets
from redbot.modules import Attack
from redbot.settings import DEBUG


class NoTargetsError(Exception):
    pass


def log(text: str, tag: str = "General", style: str = "info"):
    from redbot.web.web import socketio
    entry = {'tag': tag, 'style': style, 'time': int(time()), 'text': text}
    socketio.emit('logs', {'entries': [entry]})
    storage.lpush('log', json.dumps(entry))


def get_log(end: int = -1) -> List[str]:
    return [json.loads(_) for _ in storage.lrange('log', 0, end)]


def random_targets(req_port: int = 0, pressure: int = 0):
    from redbot.modules.discovery import get_hosts
    targets = get_hosts()
    if not len(targets):
        raise NoTargetsError()
    if req_port:
        targets = [(h, req_port) for h in targets if req_port in targets[h]['ports']]
    return random.sample(list(targets), pressure or random.randint(1, len(targets)))


def get_class(cname: str) -> Any:
    return importlib.import_module(cname).cls


def set_up_default_settings() -> Dict:
    """
    Note that in order to update these settings on an existing instance, the Redis key holding the settings must be
    cleared.
    :return:
    """
    print("Applying default settings...")
    settings = {
        'enable_attacks': {
            'name': 'Enable Auto-Attack',
            'default': False,
            'description': 'By enabling this, all specified and/or discovered targets will be attacked!'
        },
        'attack_spacing': {
            'name': 'Attack Interval',
            'default': 10,
            'description': 'The interval (in seconds) at which attacks should be launched. The minimum is 10 seconds.'
        },
        'auto_scale': {
            'name': 'Enable Auto-Scale',
            'default': False,
            'description': 'Automatically deploy VMs to match the scale factor below. Requires vCenter credentials '
                           'and valid permissions.'
        },
        'vcenter_host': {
            'name': 'vCenter Host',
            'default': '',
            'description': 'A valid hostname or IP address for the target vCenter.'
        },
        'vcenter_user': {
            'name': 'vCenter Username',
            'default': '',
            'description': 'Valid username for the target vCenter who has permission to create VMs.'
        },
        'vcenter_password': {
            'name': 'vCenter Password',
            'default': '',
            'description': 'Valid password for the supplied vCenter user.'
        },
        'vcenter_attack_network': {
            'name': 'Attack Network',
            'default': 'RedGreen',
            'description': 'The network within vCenter where Redbot workers may attack from. The network must serve '
                           'DHCP, and the default gateway must have routes to the target ranges. The Redbot user must '
                           'have permission to assign this network. '
        },
        'vcenter_mgmt_network': {
            'name': 'Backplane Network',
            'default': 'Redbot',
            'description': 'The network that Redbot nodes will use to communicate with the Redis instance. The Redbot '
                           'user must have permissions to assign this network. This network must have DHCP. '
        },
        'vcenter_deploy_host': {
            'name': 'Deploy Host(s)',
            'default': 'CDC/*',
            'description': 'The name of the host or cluster (e.g. CDC/*) that Redbot workers should be deployed to. '
                           'The user must have permission to create VMs on the target host or cluster. '
        },
        'vcenter_pool': {
            'name': 'Deploy Pool',
            'default': 'Redbot',
            'description': 'The name of the resource pool to deploy Redbot workers to. The user must have permission '
                           'to create VMs in this pool. '
        },
        'worker_scale': {
            'name': 'Worker Scale',
            'default': 1,
            'description': 'Define the number of attack workers for each target.'
        },
    }
    set_core_settings(settings)


def get_core_settings() -> Dict:
    settings = json.loads(storage.get('settings-redbot.core') or '{}')
    if not settings:
        settings = set_up_default_settings()
    return settings


def get_core_setting(key) -> Any:
    settings = get_core_settings()
    setting = None
    try:
        setting = getattr(importlib.import_module('redbot.settings'), key.upper())
    except (ImportError, AttributeError):
        pass
    return settings[key].get('value', settings[key]['default']) if key in settings else setting


def set_core_settings(data: Dict) -> None:
    storage.set('settings-redbot.core', json.dumps(data))


def set_core_setting(key: str, value: Any = None):
    s = get_core_settings()
    s[key]['value'] = value
    set_core_settings(s)


def restart_redbot() -> None:
    from redbot.web import send_msg
    if os.getppid() == 1:
        send_msg('Restarted service.')
        subprocess.run(['sudo', 'systemctl', 'restart', 'redbot'])
    elif DEBUG:
        os.system("touch redbot/web/web.py")
        send_msg('Attempting to restart Flask debugger...')


def get_random_attack() -> Attack:
    from redbot.core.async import modules
    while True:
        try:
            attack = importlib.import_module(random.choice(modules)).cls
        except (ImportError, AttributeError):
            pass
        else:
            if not attack.exempt:
                return attack


def get_file(filename: str) -> str:
    return os.path.join('files', filename)


def safe_load_config() -> None:
    try:
        parse('config.yml')
    except FileNotFoundError:
        modules.extend([module.decode() for module in storage.lrange('modules', 0, -1)])
        targets.extend([json.loads(target) for target in storage.lrange('targets', 0, -1)])
