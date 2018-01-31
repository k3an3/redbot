try:
    import eventlet

    eventlet.monkey_patch()
    print('Using eventlet')
    create_thread_func = lambda f: f
    start_thread_func = lambda f: eventlet.spawn(f)
except ImportError:
    try:
        import gevent
        import gevent.monkey

        gevent.monkey.patch_all()
        print('Using gevent')
        create_thread_func = lambda f: gevent.Greenlet(f)
        start_thread_func = lambda t: t.start()
    except ImportError:
        import threading

        print('Using threading')
        create_thread_func = lambda f: threading.Thread(target=f)
        start_thread_func = lambda t: t.start()

import os
from logging.handlers import RotatingFileHandler

import sys
import logging

from redbot import settings
from redbot.core.configparser import parse
from redbot.web.web import app, socketio

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

try:
    parse('config.yml')
except FileNotFoundError:
    print("Error: Create `config.yml` before starting! Start with `example-config.yml`.")
    raise SystemExit
handler = RotatingFileHandler('redbot.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
socketio.run(app, debug=settings.DEBUG)
