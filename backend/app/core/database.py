"""
Async SQLAlchemy setup.

System Design Primer principle applied: the API layer stays stateless and I/O to
the database is async, so a single worker can serve many concurrent focus-timer /
analytics requests without blocking on the network.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# libpq/psycopg-style query params that asyncpg does not accept and that must be
# stripped from the URL. Render's *external* Postgres URL appends `sslmode=require`;
# TLS for asyncpg is passed via `connect_args={"ssl": ...}` instead (see below).
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "gssencmode"}


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _normalize_async_url(url: str) -> tuple[str, dict]:
    """
    Coerce a sync Postgres URL to the async driver and return matching connect args.

    Render's managed Postgres exposes a `postgresql://...` (or legacy
    `postgres://...`) connection string, so the same env var works locally and on
    Render with no manual editing. Two Render-specific quirks are handled:
      - the scheme is rewritten to `postgresql+asyncpg`;
      - libpq-only params like `sslmode=require` (present on the *external* URL)
        are removed and translated into asyncpg's `ssl` connect arg, since asyncpg
        rejects them outright.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Only Postgres/asyncpg needs the param surgery; leave sqlite et al. untouched.
    if not url.startswith("postgresql+asyncpg://"):
        return url, {}

    parts = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(parts.query)]
    require_ssl = any(
        k == "sslmode" and v in {"require", "verify-ca", "verify-full"}
        for k, v in params
    )
    kept = [(k, v) for k, v in params if k not in _LIBPQ_ONLY_PARAMS]
    cleaned = urlunsplit(parts._replace(query=urlencode(kept)))
    connect_args = {"ssl": True} if require_ssl else {}
    return cleaned, connect_args


_db_url, _db_connect_args = _normalize_async_url(settings.DATABASE_URL)

# `echo` off by default; flip via a future setting if query logging is needed.
engine = create_async_engine(
    _db_url, echo=False, pool_pre_ping=True, connect_args=_db_connect_args
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
