import importlib
import json
import random
import subprocess
from time import time
from typing import List, Any, Dict

from redbot.core.models import storage


def log(text: str, tag: str = "General", style: str = "info"):
    from redbot.web.web import socketio
    entry = {'tag': tag, 'style': style, 'time': int(time()), 'text': text}
    socketio.emit('logs', {'entries': [entry]})
    storage.lpush('log', json.dumps(entry))


def get_log(end: int = -1) -> List[str]:
    return [json.loads(_) for _ in storage.lrange('log', 0, end)]


def random_targets(req_port: int = 0):
    from redbot.modules.discovery import get_hosts
    targets = get_hosts()
    if req_port:
        targets = [h for h in targets if req_port in h['ports']]
    return random.sample(targets, random.randint(1, len(targets)))


def get_class(cname: str) -> Any:
    return importlib.import_module(cname).cls


def set_up_default_settings() -> Dict:
    settings = {
        'iscore_url': {
            'name': 'IScorE URL',
            'default': '',
            'description': 'URL to the IScorE system to be used for API queries.'
        },
        'update_frequency': {
            'name': 'IScorE Check Frequency',
            'default': 5 * 60,
            'description': 'How often (in seconds) to poll the IScorE servicecheck API.'
        },
        'discovery_type': {
            'name': 'Host Discovery Method',
            'default': 'nmap',
            'description': 'Method for discovering targets. Can be "nmap", "iscore", or "both". IScorE requires a '
                           'valid URL. '
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
    subprocess.run(['sudo', 'systemctl', 'restart', 'redbot'])
