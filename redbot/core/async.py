"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""

from celery import Celery

from redbot.core.models import modules
from redbot.core.utils import get_core_setting, get_random_attack, safe_load_config
from redbot.settings import REDIS_HOST

if not modules:
    safe_load_config()
celery = Celery(include=modules, backend='redis://' + REDIS_HOST, broker='redis://' + REDIS_HOST)
celery.conf.update(
    CELERY_TASK_SOFT_TIME_LIMIT=600,
)


@celery.task
def run_jobs() -> None:
    attack = get_random_attack()
    if get_core_setting('attacks_enabled'):
        attack.run_attack()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    if not modules:
        safe_load_config()
    sender.add_periodic_task(10, run_jobs.s(), name='Launch attacks')
    from redbot.modules.discovery import do_discovery
    sender.add_periodic_task(10, do_discovery.s(), queue='discovery', name='Launch discovery')
