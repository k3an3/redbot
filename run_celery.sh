#!/bin/sh
celery -A redbot.async.celery worker --loglevel=info
