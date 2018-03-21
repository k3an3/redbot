import os
import redis

from redbot.settings import REDIS_HOST

targets = []
modules = []
storage = redis.StrictRedis(host=os.getenv('REDIS_HOST', REDIS_HOST), port=6379, db=1, decode_responses=True)
