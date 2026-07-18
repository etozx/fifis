"""
Async Redis client.

Redis plays two first-class roles in this app (System Design Primer patterns):
  1. Session store — opaque session ids -> user id, with TTL-based expiry. This
     keeps the API stateless and makes logout / revocation a single DEL.
  2. Read-path cache — analytics aggregates and the daily-advice pick are cached
     with a short TTL to absorb repeated dashboard loads.
"""

from redis.asyncio import Redis, from_url

from app.core.config import settings

# `decode_responses=True` so we work with str keys/values rather than bytes.
redis_client: Redis = from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> Redis:
    """FastAPI dependency returning the shared async Redis client."""
    return redis_client


async def close_redis() -> None:
    """Close the Redis connection pool on application shutdown."""
    await redis_client.aclose()
