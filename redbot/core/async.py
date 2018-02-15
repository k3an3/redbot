"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
import importlib
import random

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
    from redbot.modules.discovery import scheduled_scan
    sender.add_periodic_task(10, scheduled_scan.s(), name='Launch nmap scan')
