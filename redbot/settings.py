"""
settings.py

Do local configuration in settings_local.py.
"""
from peewee import SqliteDatabase

DEBUG = False
SECRET_KEY = 'changeme'
TEAM_DOMAIN_SUFFIX = 'isucdc.com'

# REDIS_HOST can be overridden by the REDIS_HOST environment variable
REDIS_HOST = 'localhost'

# Address that the Flask-SocketIO server should bind to
BIND_ADDR = '127.0.0.1'

# Configure the database for users using Peewee
DB = SqliteDatabase('redbot.sql')
# DB = MySQLDatabase('redbot', host='localhost', user='redbot', password='cdc')

# LDAP Settings (optional)
LDAP_HOST = ""
LDAP_PORT = 3389
LDAP_SSL = False
LDAP_DN_FORMAT = "{}@iseage.org"
# Or possibly something like
# LDAP_DN_FORMAT = "uid={},ou=Users,dc=example,dc=com"
LDAP_BASE_DN = ""
# The contents of the LDAP filter, which will be placed inside ({}).
# Usually 'sAMAccountName={}' for Windows AD, or 'uid={}' for OpenLDAP.
LDAP_FILTER = "sAMAccountName={}"

# How often to run Celery task handlers. This will be the minimum time
# between scheduled job launches, which is tweakable
# from web settings.
BEAT_INTERVAL = 10

try:
    from redbot.settings_local import *
except ImportError:
    pass
