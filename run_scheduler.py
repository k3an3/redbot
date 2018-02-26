#!/usr/bin/env python3
from redbot.core.async import set_up_periodic_tasks, scheduler
from redbot.core.configparser import parse

parse('config.yml')

set_up_periodic_tasks()
scheduler.start()
