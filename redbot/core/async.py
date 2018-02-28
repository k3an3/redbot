"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
import importlib
import random

from celery import Celery

from redbot.core.configparser import get_modules, parse
from redbot.core.models import modules
from redbot.core.utils import get_core_setting

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')
celery.conf.update(
    CELERY_TASK_SOFT_TIME_LIMIT=600,
)


@celery.task
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


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    parse('config.yml')
#    sender.add_periodic_task(10, run_jobs.s(), name='Launch attacks')
    from redbot.modules.discovery import do_discovery
    sender.add_periodic_task(10, do_discovery.s(), name='Launch discovery')
