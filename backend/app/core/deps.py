"""
Shared FastAPI dependencies: database session, Redis client, and the
authenticated-user resolver.

ECC principle applied: cross-cutting wiring lives in one place so routers stay
thin and declarative (`user = Depends(get_current_user)`), never re-implementing
auth or session plumbing.
"""

from typing import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.security import get_session_user_id
from app.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, guaranteed to close after the request."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    session_cookie: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Resolve the current user from the session cookie.

    Raises 401 if the cookie is missing, the session has expired, or the user no
    longer exists.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
    user_id = await get_session_user_id(redis, session_cookie)
    if user_id is None:
        raise unauthorized

    user = await db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
