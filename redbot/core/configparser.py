import json
from typing import List

import yaml

from redbot.core.models import targets, modules, storage


def parse(filename: str) -> None:
    targets.clear()
    modules.clear()
    storage.delete('targets')
    storage.delete('modules')
    with open(filename) as f:
        y = yaml.load(f)
    for target in y['targets']:
        targets.append(target)
        storage.lpush('targets', json.dumps(target))
    for module in y['modules']:
        modules.append('redbot.modules.' + module)
        storage.lpush('modules', json.dumps(target))
    print("Loaded targets")
    print(targets)
    print("Loaded modules")
    print(modules)


def get_modules(filename: str) -> List[str]:
    m = []
    with open(filename) as f:
        y = yaml.load(f)
    for module in y['modules']:
        m.append('redbot.modules.' + module)
    return m
