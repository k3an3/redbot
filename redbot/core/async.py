"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
import importlib
import random

import redis
from celery import Celery

from redbot.core.configparser import get_modules
from redbot.core.models import modules

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')


@celery.task
def run_jobs():
    while True:
        try:
            attack = importlib.import_module(random.choice(modules)).cls
        except (ImportError, AttributeError):
            pass
        else:
            if not attack.exempt:
                break
    print(attack)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(10, run_jobs.s(), name='Launch job scheduler')
    from redbot.modules.nmap import NmapScan
    sender.add_periodic_task(10, NmapScan.run_scans, name='Launch nmap scan')


# IPC
storage = redis.StrictRedis(host='localhost', port=6379, db=1)