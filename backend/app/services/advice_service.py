"""
Daily advice selection.

Rule-based now: pick a weighted-random item from the seeded catalog, but make it
*stable per user per day* (so the "advice of the day" doesn't change on every
refresh) and cache it in Redis. The selection is deterministic via a seed derived
from user id + calendar day.

Extension point: swapping this for an AI-generated line means replacing
`_choose_advice` — the caching and endpoint contract stay identical.
"""

import hashlib
import json
import random
from datetime import date

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_advice import DailyAdvice

_CACHE_TTL_SECONDS = 60 * 60 * 12  # advice of the day is stable for the day


def _daily_seed(user_id: int, day: date) -> int:
    """Deterministic integer seed from user id + ISO day."""
    digest = hashlib.sha256(f"{user_id}:{day.isoformat()}".encode()).hexdigest()
    return int(digest[:12], 16)


def _choose_advice(items: list[DailyAdvice], seed: int) -> DailyAdvice:
    """Weighted-random pick using a deterministic seed."""
    rng = random.Random(seed)
    weights = [max(item.weight, 1) for item in items]
    return rng.choices(items, weights=weights, k=1)[0]


async def get_daily_advice(
    db: AsyncSession, redis: Redis, user_id: int
) -> dict | None:
    """Return today's advice for a user, using a Redis cache."""
    today = date.today()
    cache_key = f"advice:{user_id}:{today.isoformat()}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    items = list(await db.scalars(select(DailyAdvice)))
    if not items:
        return None

    chosen = _choose_advice(items, _daily_seed(user_id, today))
    payload = {
        "id": chosen.id,
        "text": chosen.text,
        "category": chosen.category,
        "tags": chosen.tags,
    }
    await redis.set(cache_key, json.dumps(payload), ex=_CACHE_TTL_SECONDS)
    return payload
