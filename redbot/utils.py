import datetime
import random

from redbot.async import storage
from redbot.models import targets


def log(text: str):
    storage.lpush('log', '[{}] {}'.format(datetime.datetime.now(), text))

def random_targets():
    return random.sample(targets, random.randint(1, len(targets)))
