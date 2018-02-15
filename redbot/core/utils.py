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
    from redbot.modules.discovery import targets
    if req_port:
        # targets = [h for h in get_hosts() if
        pass
    return random.sample(targets, random.randint(1, len(targets)))


def get_class(cname: str) -> Any:
    return importlib.import_module(cname).cls


def set_up_default_settings() -> Dict:
    settings = {
        'iscore_url': {
            'name': 'IScorE URL',
            'default': '',
            'description': 'URL to the IScorE system to be used for API queries'
        },
        'discovery_type': {
            'name': 'Host Discovery Method',
            'default': 'nmap',
            'description': 'Method for discovering targets. Can be "nmap", "iscore", or "both". IScorE requires a '
                           'valid URL. '
        }
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
    return settings.get(key)['value'] if key in settings else setting


def set_core_settings(data: Dict) -> None:
    storage.set('settings-redbot.core', json.dumps(data))


def set_core_setting(key: str, value: Any = None):
    s = get_core_settings()
    s[key]['value'] = value
    set_core_settings(s)


def restart_redbot() -> None:
    subprocess.run(['sudo', 'systemctl', 'restart', 'redbot'])
