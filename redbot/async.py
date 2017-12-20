"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
from celery import Celery

from redbot.configparser import get_modules
from redbot.models import modules

if not modules:
    modules = get_modules('config.yml')
celery = Celery(include=modules, backend='redis://', broker='redis://')
