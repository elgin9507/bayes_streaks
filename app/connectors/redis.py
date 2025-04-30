"""Redis connection manager."""

import redis.asyncio as aioredis

from app import settings

_redis: aioredis.Redis = None


async def get_redis_connection() -> aioredis.Redis:
    """Get a connection to Redis."""
    global _redis

    if _redis is None:
        _redis = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)

    return _redis
