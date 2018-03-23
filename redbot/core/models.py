import os
import redis
from flask_login import UserMixin
from passlib.handlers.sha2_crypt import sha256_crypt
from peewee import OperationalError, Model, CharField, BooleanField

from redbot.settings import REDIS_HOST, DB

targets = []
modules = []
storage = redis.StrictRedis(host=os.getenv('REDIS_HOST', REDIS_HOST), port=6379, db=1, decode_responses=True)


def db_init():
    DB.connect()
    try:
        DB.create_tables([User])
        print('Creating tables...')
    except OperationalError:
        pass
    DB.close()


class BaseModel(Model):
    class Meta:
        database = DB


class User(BaseModel, UserMixin):
    username = CharField(unique=True)
    password = CharField(null=True)
    admin = BooleanField(default=False)
    ldap = BooleanField(default=False)

    def check_password(self, password: str) -> bool:
        if self.ldap:
            from redbot.core.utils import ldap_auth
            return ldap_auth(self.username, password)
        return sha256_crypt.verify(password, self.password)

    def set_password(self, password: str) -> None:
        self.password = sha256_crypt.encrypt(password)
