"""
Health router — used by Render's health checks.

Reports liveness plus a shallow readiness probe of the two datastores so a
failing DB/Redis surfaces as an unhealthy instance rather than 500s deep in a
request.
"""

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Return 200 with per-dependency status."""
    db_ok = True
    redis_ok = True

    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - health check reports, never raises
        db_ok = False

    try:
        await redis.ping()
    except Exception:  # noqa: BLE001
        redis_ok = False

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "service": settings.APP_NAME,
        "env": settings.ENV,
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
    }
