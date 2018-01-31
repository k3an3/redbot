import importlib
import json
import random
from time import time
from typing import List, Any, Dict

from redbot.core.async import storage


def log(text: str, tag: str = "General", style: str = "info"):
    from redbot.web.web import socketio
    entry = {'tag': tag, 'style': style, 'time': int(time()), 'text': text}
    socketio.emit('logs', {'entries': [entry]})
    storage.lpush('log', json.dumps(entry))


def get_log(end: int = -1) -> List[str]:
    return [json.loads(_) for _ in storage.lrange('log', 0, end)]


def random_targets(req_port: int = 0):
    from redbot.modules.nmap import targets
    if req_port:
        # targets = [h for h in get_hosts() if
        pass
    return random.sample(targets, random.randint(1, len(targets)))


def get_class(cname: str) -> Any:
    return importlib.import_module(cname).cls


def get_core_settings() -> Dict:
    return json.loads(storage.get('settings-redbot.core'))
