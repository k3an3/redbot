import redis

targets = []
modules = []
storage = redis.StrictRedis(host='localhost', port=6379, db=1)