from peewee import SqliteDatabase

DEBUG = False
SECRET_KEY = 'changeme'
TEAM_DOMAIN_SUFFIX = 'isucdc.com'
REDIS_HOST = 'localhost'
HOST = '127.0.0.1'
DB = SqliteDatabase('redbot.sql')
LDAP_HOST = ""
LDAP_PORT = 3389
LDAP_SSL = False
LDAP_DN_FORMAT = "{}@iseage.org"
# Or possibly something like
# LDAP_DN_FORMAT = "uid={},ou=Users,dc=example,dc=com"
LDAP_BASE_DN = ""
LDAP_FILTER = "sAMAccountName={}"

try:
    from redbot.settings_local import *
except ImportError:
    pass
