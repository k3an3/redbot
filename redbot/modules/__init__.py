import importlib
import json
import logging
from typing import Dict, Any, List

from redbot.core.async import storage
from redbot.core.models import modules

logger = logging.getLogger('redbot.modules')


def get_all_ports() -> List[int]:
    ports = []
    for module in modules:
        try:
            cls = importlib.import_module(module).cls
        except (ImportError, AttributeError):
            pass
        else:
            if cls:
                p = cls.get_setting('ports')
                if p:
                    ports += p


class Attack:
    name = None
    ports = None
    credentials = None
    settings = None
    exempt = False

    @classmethod
    def get_storage_key(cls):
        return 'settings-' + cls.name

    @classmethod
    def run_attack(cls):
        raise NotImplemented

    @classmethod
    def push_update(cls):
        raise NotImplemented

    @classmethod
    def log(cls, text: str, style: str = "info") -> None:
        from redbot.core.utils import log
        log(text, cls.name, style)

    @classmethod
    def get_setting(cls, key) -> Any:
        settings = cls.get_settings()
        return settings.get(key)['value'] if key in settings else cls.settings[key]['default']

    @classmethod
    def get_settings(cls) -> Dict:
        return json.loads(storage.get(cls.get_storage_key()) or "{}")

    @classmethod
    def set_setting(cls, key: str, value: Any = None):
        s = cls.get_settings()
        s[key] = value
        cls.set_settings(s)

    @classmethod
    def set_settings(cls, data: Dict) -> None:
        storage.set(cls.get_storage_key(), json.dumps(data))

    @classmethod
    def merge_settings(cls) -> Dict:
        s = cls.get_settings()
        for setting in cls.settings:
            try:
                cls.settings[setting].update({'value': s.get(setting)})
            except (TypeError, ValueError):
                pass
        return cls.settings
