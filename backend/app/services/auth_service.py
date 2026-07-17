"""
Authentication business logic.

ECC principle: routers handle HTTP; the rules of "can this person register /
log in" live here so they're testable without a web request.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserLogin, UserRegister


async def register_user(db: AsyncSession, payload: UserRegister) -> User:
    """Create a new user, rejecting duplicate emails."""
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, payload: UserLogin) -> User:
    """Return the user if credentials are valid, else raise 401."""
    user = await db.scalar(select(User).where(User.email == payload.email))
    # Verify even when the user is missing is unnecessary here; a generic error
    # message avoids leaking which emails exist.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return user
