"""
Password hashing and Redis-backed session management.

Auth model (justified in the plan): opaque server-side sessions stored in Redis,
delivered to the browser as an httpOnly cookie. Benefits:
  - No token material in JS -> no XSS token theft.
  - Revocation is a single Redis DEL (logout / "sign out everywhere").
  - The API stays stateless; any backend instance can validate any session.
"""

import secrets

from passlib.context import CryptContext
from redis.asyncio import Redis

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SESSION_PREFIX = "sess:"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plaintext password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _session_key(session_id: str) -> str:
    return f"{_SESSION_PREFIX}{session_id}"


async def create_session(redis: Redis, user_id: int) -> str:
    """
    Create a new session mapping a random opaque id -> user id in Redis with TTL.

    Returns the session id to be set as the cookie value.
    """
    session_id = secrets.token_urlsafe(32)
    await redis.set(
        _session_key(session_id), str(user_id), ex=settings.SESSION_TTL_SECONDS
    )
    return session_id


async def get_session_user_id(redis: Redis, session_id: str) -> int | None:
    """Resolve a session id to its user id, or None if missing/expired."""
    if not session_id:
        return None
    raw = await redis.get(_session_key(session_id))
    return int(raw) if raw is not None else None


async def destroy_session(redis: Redis, session_id: str) -> None:
    """Delete a session (used on logout)."""
    if session_id:
        await redis.delete(_session_key(session_id))
