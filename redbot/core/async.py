"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""

from celery import Celery
from celery.result import allow_join_result

from redbot.core.configparser import get_modules, parse
from redbot.core.models import modules
from redbot.core.utils import get_core_setting, get_random_attack

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')
celery.conf.update(
    CELERY_TASK_SOFT_TIME_LIMIT=600,
)


@celery.task
def run_jobs() -> None:
    attack = get_random_attack()
    if get_core_setting('attacks_enabled'):
        with allow_join_result():
            attack.run_attack()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if not modules:
        parse('config.yml')
    sender.add_periodic_task(10, run_jobs.s(), name='Launch attacks')
    from redbot.modules.discovery import do_discovery
    sender.add_periodic_task(10, do_discovery.s(), queue='discovery', name='Launch discovery')
