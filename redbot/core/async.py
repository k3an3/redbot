"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
import importlib
import random

from apscheduler.schedulers.background import BackgroundScheduler
from celery import Celery

from redbot.core.configparser import get_modules
from redbot.core.models import modules

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')

scheduler = BackgroundScheduler()


def run_jobs() -> None:
    while True:
        try:
            attack = importlib.import_module(random.choice(modules)).cls
        except (ImportError, AttributeError):
            pass
        else:
            if not attack.exempt:
                break
    print("Would run attack", attack)


def set_up_periodic_tasks() -> None:
    scheduler.add_periodic_task(10, run_jobs.s(), name='Launch job scheduler')
    from redbot.modules.discovery import scheduled_scan
    scheduler.add_periodic_task(10, scheduled_scan.s(), name='Launch nmap scan')
