"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
import redis
from celery import Celery
from rejson import Client

from redbot.configparser import get_modules
from redbot.models import modules

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')


@celery.task
def run_jobs():
    pass


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(10.0, run_jobs.s(), name='Launch job scheduler')


# IPC
storage = redis.StrictRedis(host='localhost', port=6379, db=1)
