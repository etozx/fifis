"""Daily advice router."""

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.advice import AdviceOut
from app.services import advice_service

router = APIRouter(prefix="/advice", tags=["advice"])


@router.get("/today", response_model=AdviceOut)
async def advice_today(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(get_current_user),
):
    """Return today's stable advice-of-the-day for the current user."""
    advice = await advice_service.get_daily_advice(db, redis, user.id)
    if advice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No advice available. Seed the advice catalog first.",
        )
    return advice
