"""
Auth router — register, login, logout, and current-user.

Session cookie policy: httpOnly (no JS access), Secure + SameSite from settings.
On Render, the static frontend and API live on different subdomains, so
production uses `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none` to allow the
cross-site credentialed request.
"""

from fastapi import APIRouter, Cookie, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.redis import get_redis
from app.core.security import create_session, destroy_session
from app.models.user import User
from app.schemas.user import UserLogin, UserOut, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Create an account and start a session (auto-login)."""
    user = await auth_service.register_user(db, payload)
    session_id = await create_session(redis, user.id)
    _set_session_cookie(response, session_id)
    return user


@router.post("/login", response_model=UserOut)
async def login(
    payload: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Verify credentials and establish a session cookie."""
    user = await auth_service.authenticate_user(db, payload)
    session_id = await create_session(redis, user.id)
    _set_session_cookie(response, session_id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session_cookie: str | None = Cookie(
        default=None, alias=settings.SESSION_COOKIE_NAME
    ),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    """Destroy the server-side session (Redis DEL) and clear the cookie."""
    await destroy_session(redis, session_cookie or "")
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user (used by the frontend to bootstrap state)."""
    return current_user
