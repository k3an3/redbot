from typing import List

import os
import yaml

from redbot.models import targets, modules


def parse(filename: str) -> None:
    with open(filename) as f:
        y = yaml.load(f)
    for target in y['targets']:
        targets.append(target)
    for module in y['modules']:
        modules.append('redbot.modules.' + module)
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
