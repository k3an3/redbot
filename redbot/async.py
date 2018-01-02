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

# IPC
json_storage = Client(host='localhost', port=6379, db=1)
storage = redis.StrictRedis(host='localhost', port=6379, db=1)
