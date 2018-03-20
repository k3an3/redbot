import importlib
import json
import logging
import random
from abc import ABC
from typing import Dict, Any, List, Set, Callable, Iterable, Tuple

from celery import group
from celery.result import GroupResult

from redbot.core.models import modules, storage
from redbot.core.utils import set_settings, set_setting, get_settings, get_setting

logger = logging.getLogger('redbot.modules')


def get_all_ports() -> Set[int]:
    """
    Create a set of all ports used by all installed modules.

    :return: Unique set of all ports.
    """
    ports = set()
    for module in modules:
        try:
            cls = importlib.import_module(module).cls
        except (ImportError, AttributeError):
            pass
        else:
            if cls:
                p = cls.get_setting('ports')
                for port in p.replace(' ', '').split(','):
                    ports.add(int(port))


class Attack(ABC):
    """
    The abstract base class for all attack modules. Any attack modules to be used by Redbot must be a subclass of
    this class, and they must implement at least the run_attack method; others may be overridden optionally.
    """
    name = None
    credentials = None
    settings = None
    exempt = False
    notes = ""
    test = True

    @classmethod
    def get_storage_key(cls) -> str:
        """
        Obtain the Redis key for this class's settings based on its name.

        :return: The Redis key for this class's settings.
        """
        return 'settings-' + cls.name

    @classmethod
    def run_attack(cls) -> Tuple[GroupResult, List]:
        """
        This method is called by Redbot's job scheduler, and executes the class's main functionality. Code to run the
        attack (selecting targets, running Celery tasks) should be invoked from here.

        For convenience, once target selection has completed, the attacks, targets, and any options can be passed to
        attack_all.

        :return: A tuple containing the GroupResult object, and a list of the targets that are being attacked.
        """
        raise NotImplemented

    @classmethod
    def attack_all(cls, attacks: Iterable[Callable], targets: Iterable[Tuple], *args, **kwargs) -> GroupResult:
        """
        A convenience method to execute all supplied attacks against supplied targets in parallel.

        :param attacks: An iterable of attack callables that should be randomly selected from for each target.
        :param targets: An iterable of target (host, port) pairs to be attacked.
        :param args: Optional positional arguments that will be passed to the attack callables.
        :param kwargs: Optional keyword arguments that will be passed to the attack callables.
        :return: A Celery GroupResult object containing results of all tasks started here.
        """
        return group(random.choice(attacks).s(*target, *args, **kwargs) for target in targets)()

    @classmethod
    def push_update(cls, data: Dict[str, str]) -> None:
        """
        An optional method to receive updates from a Celery task-in-progress. This can be used to update progress
        information in real time on the front end. The limitation with this is that the task in question must be
        called from the context of the web application, so it is not useful for scheduled jobs.

        A working implementation can be found in the redbot.modules.discovery module.

        :param data: Dictionary of status and results provided by Celery.
        """
        raise NotImplemented

    @classmethod
    def log(cls, text: str, style: str = "info") -> None:
        """
        Wrapper for the log utility function, simply adds module name to log call.

        :param text: The body of the log message.
        :param style: The CSS class suffix for Bootstrap theming, e.g. info, warning, danger, success, etc.
        """
        from redbot.core.utils import log
        log(text, cls.name, style)

    @classmethod
    def get_setting(cls, key) -> Any:
        """
        Wrapper for utils get_setting.

        :param key: Setting key to retrieve.
        :return: Fetched setting value.
        """
        setting = get_setting(cls.get_storage_key(), key)
        return setting or cls.settings[key]['default']

    @classmethod
    def get_settings(cls) -> Dict:
        """
        Wrapper for utils get_settings.

        :return: Dictionary of all settings for this class.
        """
        return get_settings(cls.get_storage_key())

    @classmethod
    def set_setting(cls, key: str, value: Any = None) -> None:
        """
        Wrapper for utils get_settings.

        :param key: Setting key to write.
        :param value:  Setting value to write.
        """
        set_setting(cls.get_storage_key(), key, value)

    @classmethod
    def set_settings(cls, data: Dict) -> None:
        """
        Wrapper for utils get_settings.

        :param data: Dictionary data to update this class's settings with.
        """
        set_settings(cls.get_storage_key(), data)

    @classmethod
    def merge_settings(cls) -> Dict:
        """
        Merge settings from Redis and those stored in the class.

        :return: A dictionary of the merged settings.
        """
        s = cls.get_settings()
        for setting in cls.settings:
            try:
                cls.settings[setting].update({'value': s[setting]['value']})
            except (TypeError, ValueError, KeyError):
                pass
        return cls.settings

    @classmethod
    def get_random_targets(cls) -> List[Tuple[str, int]]:
        """
        Convenience method that will create a list of targets based on the specified ports supported or configured
        for this class.

        :return: A list of target tuples matching the allowed ports.
        """
        from redbot.core.utils import random_targets
        targets = []
        [targets.extend(random_targets(int(port))) for port in cls.get_setting('ports').replace(' ', '').split(',')]
        return targets
