import importlib
import json
import os
import random
import subprocess
from time import time
from typing import List, Any, Dict

from redbot.core.configparser import parse
from redbot.core.models import modules, storage, targets
from redbot.settings import DEBUG

BASE = 'settings-redbot.core'


class NoTargetsError(Exception):
    pass


def log(text: str, tag: str = "General", style: str = "info") -> None:
    """
    Write log data to storage.

    :param text: The log body.
    :param tag: The tag for the log entry; i.e. which module is logging.
    :param style: The Bootstrap CSS class suffix for this entry.
    """
    from redbot.web.web import socketio
    entry = {'tag': tag, 'style': style, 'time': int(time()), 'text': text}
    socketio.emit('logs', {'entries': [entry]})
    storage.lpush('log', json.dumps(entry))


def get_log(end: int = -1) -> List[str]:
    """
    Return log entries for the given length.

    :param end: How many entries to retrieve.
    :return: A list of log entries.
    """
    return [json.loads(_) for _ in storage.lrange('log', 0, end)]


def random_targets(req_port: int = 0, pressure: int = 0):
    """
    Given a port number, find hosts that have this port open and return a random subset of these hosts.

    :param req_port: Port number that selected hosts should have open.
    :param pressure: Not developed yet.
    :return: A random sample of hosts.
    """
    from redbot.modules.discovery import get_hosts
    hosts = get_hosts()
    if not len(hosts):
        raise NoTargetsError()
    if req_port:
        hosts = [(h, req_port) for h in hosts if req_port in hosts[h]['ports']]
    return random.sample(list(hosts), pressure or random.randint(1, len(hosts)))


def get_class(module_name: str) -> Any:
    """
    Given the name of a module, this function will import the module and return the object "cls".

    :param module_name: Module containing the target class.
    :return: The "cls" class from the specified module.
    """
    return importlib.import_module(module_name).cls


def set_up_default_settings() -> None:
    """
    Note that in order to update these settings on an existing instance, the Redis key holding the settings must be
    cleared.
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
        'build_mode': {
            'name': 'Worker Build Mode',
            'default': 'remote',
            'description': 'Valid options are "remote", "local", or "virtualbox". In order to greatly increase '
                           'deployment performance, the Redbot worker container can be '
                           'built locally or within a local Virtualbox machine. The "local" and "virtualbox" settings '
                           'require a locally running Docker daemon or Virtualbox instance, respectively.'
        },
        'worker_scale': {
            'name': 'Worker Scale',
            'default': 1,
            'description': 'Define the number of attack workers for each target. Will cause the workers to scale '
                           'appropriately. '
        },
    }
    set_core_settings(settings)


def set_settings(key_prefix: str, data: Dict[str, Any]) -> None:
    for key, value in data.items():
        storage.hmset(key_prefix + ':' + key, value)
        storage.sadd(key_prefix, key)


def set_setting(key_prefix: str, key: str, value: Any = None) -> None:
    storage.hmset(key_prefix + ':' + key, {'value': value})
    storage.sadd(key_prefix, key)


def get_settings(key_prefix: str) -> Dict[str, Any]:
    settings = {}
    for s in storage.smembers(key_prefix):
        settings[s] = storage.hgetall(key_prefix + ':' + s)
    return settings


def get_setting(key_prefix: str, key: str) -> Any:
    stored = storage.hgetall(key_prefix + key)
    return stored.get('value', stored.get('default'))


def get_core_settings() -> Dict:
    settings = get_settings(BASE)
    if not settings:
        settings = set_up_default_settings()
    return settings


def get_core_setting(key) -> Any:
    return get_setting(BASE, key)


def set_core_settings(data: Dict) -> None:
    set_settings(BASE, data)


def set_core_setting(key: str, value: Any = None) -> None:
    set_setting(BASE, key, value)


def restart_redbot() -> None:
    from redbot.web import send_msg
    if os.getppid() == 1:
        send_msg('Restarted service.')
        subprocess.run(['sudo', 'systemctl', 'restart', 'redbot'])
    elif DEBUG:
        os.system("touch redbot/web/web.py")
        send_msg('Attempting to restart Flask debugger...')


def get_random_attack() -> Any:
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
        if not modules or not targets:
            raise Exception("Couldn't load modules and/or targets from Redis.")
