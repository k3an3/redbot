"""
async.py
~~~~~~~~

Manages the setup for task handling.
"""
from celery import Celery

tasks = Celery('redbot')
