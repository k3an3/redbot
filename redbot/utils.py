import datetime
import random
from typing import List

from redbot.async import storage
from redbot.models import targets


def log(text: str):
    storage.lpush('log', '[{}] {}'.format(datetime.datetime.now(), text))


def get_log(filter: str = "") -> List[str]:
    return storage.lget('log')


def random_targets():
    return random.sample(targets, random.randint(1, len(targets)))
