import os
from redis import Redis
from rq import Queue

_redis: Redis | None = None

def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis/0")

async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_redis_url())
    return _redis

async def close_redis():
    global _redis
    if _redis is not None:
        _redis.close()
        _redis = None

async def get_queue():
    q = Queue(connection=(await get_redis()))
    return q
