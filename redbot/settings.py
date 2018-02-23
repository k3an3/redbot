DEBUG = False
SECRET_KEY = 'changeme'
TEAM_DOMAIN_SUFFIX = 'isucdc.com'

try:
    from redbot.settings_local import *
except ImportError:
    pass
