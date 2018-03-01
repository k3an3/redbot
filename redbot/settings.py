DEBUG = False
SECRET_KEY = 'changeme'
TEAM_DOMAIN_SUFFIX = 'isucdc.com'
REDIS_HOST = 'localhost'

try:
    from redbot.settings_local import *
except ImportError:
    pass
