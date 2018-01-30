#!/bin/sh
celery -A redbot.core.async.celery worker --loglevel=info
