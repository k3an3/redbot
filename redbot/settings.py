DEBUG = False
SECRET_KEY = 'changeme'

try:
    from redbot.settings_local import *
except ImportError:
    pass
