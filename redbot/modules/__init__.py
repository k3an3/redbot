import importlib
from typing import Dict, Any, List

from redbot.async import storage
from redbot.models import modules


def get_setting(key: str, settings: Dict[str, Any]) -> Any:
    return storage.get('value') or settings[key].get('default')


def get_all_ports() -> List[int]:
    ports = []
    for module in modules:
        try:
            settings = getattr(importlib.import_module(module), 'settings')
        except (ImportError, AttributeError):
            pass
        else:
            if settings:
                p = get_setting('ports', settings)
                if p:
                    ports += p


class Attack:
    name = None
    ports = None
    credentials = None

    @classmethod
    def run_attack(cls):
        raise NotImplemented
