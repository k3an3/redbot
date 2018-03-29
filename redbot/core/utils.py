"""
General-purpose utilities useful across the application.
"""
import importlib
import json
import os
import random
import subprocess
from time import time
from typing import List, Any, Dict

from ldap3 import Server, Connection, ALL_ATTRIBUTES

from redbot.core.configparser import parse
from redbot.core.models import modules, storage, targets, User
from redbot.settings import DEBUG, LDAP_SSL, LDAP_PORT, LDAP_HOST, LDAP_DN_FORMAT, LDAP_BASE_DN, LDAP_FILTER

BASE = 'settings-redbot.core'


class NoTargetsError(Exception):
    """
    Exception thrown when an attack is run but no targets have been discovered yet.
    """
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


def host_has_port(host, port) -> bool:
    return str(port) in host['ports']


def random_targets(req_port: int = 0):
    """
    Given a port number, find hosts that have this port open and return a random subset of these hosts.

    :param req_port: Port number that selected hosts should have open.
    :return: A random sample of hosts.
    """
    from redbot.modules.discovery import get_hosts
    hosts = get_hosts()
    if not len(hosts):
        raise NoTargetsError()
    if req_port:
        hosts = [h for h in hosts if host_has_port(hosts[h], req_port)]
    return [(h, req_port) for h in random.sample(list(hosts), random.randint(1, len(hosts)))]


def get_class(module_name: str) -> Any:
    """
    Given the name of a module, this function will import the module and return the object "cls".

    :param module_name: Module containing the target class.
    :return: The "cls" class from the specified module.
    """
    return importlib.import_module(module_name).cls


def set_up_default_settings() -> Dict[str, Dict]:
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
            'name': 'Deploy Host',
            'default': '',
            'description': 'Host to deploy to. Not needed if a pool within a cluster is selected.'
        },
        'vcenter_folder': {
            'name': 'Deploy Folder',
            'default': 'ISEAGE/Keane/Redbot',
            'description': 'The name of the folder to deploy Redbot workers to. The user must have permission '
                           'to create VMs in this folder. '
        },
        'vcenter_pool': {
            'name': 'Deploy Pool',
            'default': '/*/host/*/Resources/ISEAGE/Keane/Redbot',
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
        'vcenter_datastore': {
            'name': 'Deploy Datastore',
            'default': '',
            'description': 'The names of one or more datastores to deploy to. A random datastore will be selected.'
        },
        'task_timeout': {
            'name': 'Task Timeout',
            'default': 60,
            'description': 'How long attacks should be allowed to run before they are killed.'
        }
    }
    set_core_settings(settings)
    return settings


def set_settings(key_prefix: str, data: Dict[str, Any]) -> None:
    """
    Low-level handler to write settings to Redis.
    :param key_prefix: The string key for this module's settings.
    :param data: A dictionary of settings to write.
    """
    for key, value in data.items():
        storage.hmset(key_prefix + ':' + key, value)
        storage.sadd(key_prefix, key)


def set_setting(key_prefix: str, key: str, value: Any = None) -> None:
    """
    Low-level handler to write a setting to Redis.
    :param key_prefix: The string key for this module's settings.
    :param key: The key where the data should be stored.
    :param value: The value of the data to be stored.
    """
    storage.hmset(key_prefix + ':' + key, {'value': value})
    storage.sadd(key_prefix, key)


def get_settings(key_prefix: str) -> Dict[str, Any]:
    """
    Low-level handler to read all settings.
    :param key_prefix: Which key(s) to retrieve.
    :return: A dictionary of all settings.
    """
    settings = {}
    for s in storage.smembers(key_prefix):
        settings[s] = storage.hgetall(key_prefix + ':' + s)
    return settings


def get_setting(key_prefix: str, key: str) -> Any:
    """
    Low-level handler to read a setting.
    :param key_prefix: Which key prefix to prepend to the key.
    :param key: Which key inside the prefix to retrieve.
    :return: The setting's value.
    """
    stored = storage.hgetall(key_prefix + ":" + key)
    val = stored.get('value', stored.get('default'))
    return False if val == 'False' else True if val == 'True' else val


def get_core_settings() -> Dict:
    settings = get_settings(BASE)
    if not settings:
        settings = set_up_default_settings()
    return settings


def get_core_setting(key) -> Any:
    ""
    return get_setting(BASE, key)


def set_core_settings(data: Dict) -> None:
    set_settings(BASE, data)


def set_core_setting(key: str, value: Any = None) -> None:
    set_setting(BASE, key, value)


def restart_redbot() -> None:
    """
    Attempt to restart the Redbot service. Will attempt to restart via Systemd, and will fallback to abuse Flask's
    autoreload if it is in use.
    """
    from redbot.web import send_msg
    if os.getppid() == 1:
        send_msg('Restarted service.')
        subprocess.run(['sudo', 'systemctl', 'restart', 'redbot'])
    elif DEBUG:
        os.system("touch redbot/web/web.py")
        send_msg('Attempting to restart Flask debugger...')


def get_random_attack() -> Any:
    """
    Cycle through all installed modules and return the Attack class from one of them.
    :return: An Attack class.
    """
    from redbot.core.async import modules
    while True:
        try:
            attack = get_class(random.choice(modules))
        except (ImportError, AttributeError):
            pass
        else:
            if not attack.exempt:
                return attack


def get_file(filename: str) -> str:
    """
    Return path to a file located in the 'files' subdirectory.
    :param filename:
    :return: Relateive path to the file.
    """
    return os.path.join('files', filename)


def safe_load_config() -> None:
    """
    Try to parse and load from config.yml; if it does not exist, will attempt to load config from Redis.
    """
    try:
        parse('config.yml')
    except FileNotFoundError:
        modules.extend([module for module in storage.lrange('modules', 0, -1)])
        targets.extend([json.loads(target) for target in storage.lrange('targets', 0, -1)])
        if not modules or not targets:
            raise Exception("Couldn't load modules and/or targets from Redis.")


def is_admin(r: str) -> bool:
    """
    LDAP helper function to determine whether a user is a member of the Domain Admins group.
    :param r: LDAP attributes
    :return: True if the user is a Domain Admin, False otherwise.
    """
    for g in [g.decode() for g in r['memberOf']]:
        if 'CN=Domain Admins,' in g:
            return True
    return False


def ldap_auth(username: str, password: str) -> User:
    """
    Function to bind with an LDAP server given credentials, and fetch information about that user suitable for
    authenticating and assigning roles to them. :param username: :param password: :return:
    :param username: Username to bind with and to retrieve attributes for.
    :param password: The user's password to bind with.
    :return: A User object of an authenticated user. Returns None if the user could not be authenticated.
    """
    s = Server(host=LDAP_HOST, port=LDAP_PORT, use_ssl=LDAP_SSL)
    with Connection(s, user=(LDAP_DN_FORMAT.format(username)), password=password) as c:
        u = None
        if c.bind():
            print("Successful bind for user " + username)
            c.search(search_base=LDAP_BASE_DN,
                     search_filter='({})'.format(LDAP_FILTER.format(username)),
                     attributes=ALL_ATTRIBUTES)
            r = c.response[0]['raw_attributes']
            u, created = User.get_or_create(username=username,
                                            defaults={'ldap': True,
                                                      'password': '',
                                                      'admin': is_admin(r)
                                                      })
            if created:
                print("Created new user from LDAP: " + username)
            else:
                u.admin = is_admin(r)
                u.save()
        else:
            print("Failed to bind with user " + LDAP_FILTER.format(username) + LDAP_BASE_DN)
        return u
