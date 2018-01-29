#!/bin/sh
celery -A redbot.async.celery beat
