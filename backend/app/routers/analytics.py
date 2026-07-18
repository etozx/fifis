"""Analytics dashboard router."""

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    range_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(get_current_user),
):
    """Personal-growth summary: focus time, tasks, streaks, category split."""
    return await analytics_service.get_summary(db, redis, user.id, range_days)
