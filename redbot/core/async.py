"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
import importlib
import random

from apscheduler.schedulers.blocking import BlockingScheduler
from celery import Celery

from redbot.core.configparser import get_modules
from redbot.core.models import modules
from redbot.core.utils import get_core_setting

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')
celery.conf.update(
    CELERY_TASK_SOFT_TIME_LIMIT=600,
)


scheduler = BlockingScheduler()


def run_jobs() -> None:
    while True:
        try:
            attack = importlib.import_module(random.choice(modules)).cls
        except (ImportError, AttributeError):
            pass
        else:
            if not attack.exempt:
                break
    if get_core_setting('attacks_enabled'):
        attack.run_attack()


def set_up_periodic_tasks() -> None:
    run_jobs()
    scheduler.add_job(run_jobs, 'interval', seconds=10)
    from redbot.modules.discovery import do_discovery
    do_discovery()
    scheduler.add_job(do_discovery, 'interval', seconds=10)
