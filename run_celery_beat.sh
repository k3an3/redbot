#!/bin/sh
celery -A redbot.core.async.celery beat
