import json
from typing import List

import yaml

from redbot.core.models import targets, modules, storage


def parse(filename: str) -> None:
    with open(filename) as f:
        y = yaml.load(f)
    targets.clear()
    modules.clear()
    storage.delete('targets')
    storage.delete('modules')
    for target in y['targets']:
        targets.append(target)
        storage.lpush('targets', json.dumps(target))
    modules.append('redbot.modules.discovery')
    for module in y['modules']:
        module_name = 'redbot.modules.' + module
        modules.append(module_name)
        storage.lpush('modules', module_name)
    print("Loaded targets")
    print(targets)
    print("Loaded modules")
    print(modules)


def get_modules(filename: str) -> List[str]:
    m = ['redbot.modules.discovery']
    with open(filename) as f:
        y = yaml.load(f)
    for module in y['modules']:
        m.append('redbot.modules.' + module)
    return m
