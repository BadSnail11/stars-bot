import os
from redis.asyncio import Redis

_redis: Redis | None = None

def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_redis_url(), decode_responses=True)
    return _redis

async def close_redis():
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
