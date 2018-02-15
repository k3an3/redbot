DEBUG = False
SECRET_KEY = 'changeme'
ISCORE_URL = ''

try:
    from redbot.settings_local import *
except ImportError:
    pass
