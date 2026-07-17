"""
Async SQLAlchemy setup.

System Design Primer principle applied: the API layer stays stateless and I/O to
the database is async, so a single worker can serve many concurrent focus-timer /
analytics requests without blocking on the network.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _normalize_async_url(url: str) -> str:
    """
    Coerce a sync Postgres URL to the async driver.

    Render's managed Postgres exposes a `postgresql://...` (or legacy
    `postgres://...`) connection string, but we run on asyncpg. Rewriting the
    scheme here means the same env var works locally and on Render with no manual
    editing.
    """
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# `echo` off by default; flip via a future setting if query logging is needed.
engine = create_async_engine(
    _normalize_async_url(settings.DATABASE_URL), echo=False, pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def init_models() -> None:
    """
    Create tables from ORM metadata.

    Used at startup for this scaffold. In production this is replaced by Alembic
    migrations (noted as the follow-up in the plan) so schema changes are
    reviewable and reversible.
    """
    # Import models so they register on Base.metadata before create_all runs.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
