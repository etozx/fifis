"""
Lightweight migration runner (PostgreSQL).

Applies every `backend/migrations/*.sql` file that hasn't been applied yet, in
filename order, tracking applied versions in a `schema_migrations` table. Safe to
run on every deploy/boot: already-applied migrations are skipped, so it's a no-op
once the schema is current.

Invoked from start.sh before the server starts. On non-PostgreSQL databases
(local sqlite dev) it does nothing — there `create_all` builds the schema and the
Postgres-specific SQL doesn't apply.

Usage:  python migrate.py
"""

import asyncio
import pathlib
import sys

import asyncpg

from app.core.config import settings
from app.core.database import _normalize_async_url

MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"


async def _apply() -> None:
    url, connect_args = _normalize_async_url(settings.DATABASE_URL)
    if not url.startswith("postgresql+asyncpg"):
        print("[migrate] Non-PostgreSQL database detected — skipping SQL migrations.")
        return

    # asyncpg wants a bare libpq DSN (no SQLAlchemy +asyncpg suffix).
    dsn = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn, ssl=connect_args.get("ssl"))
    try:
        # Tracking table: one row per applied migration file.
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        applied = {
            row["version"]
            for row in await conn.fetch("SELECT version FROM schema_migrations")
        }

        files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not files:
            print("[migrate] No migration files found.")
            return

        pending = [f for f in files if f.name not in applied]
        if not pending:
            print(f"[migrate] Up to date ({len(applied)} migration(s) applied).")
            return

        for path in pending:
            print(f"[migrate] Applying {path.name} ...")
            sql = path.read_text()
            # Each migration + its bookkeeping row commit atomically together.
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)", path.name
                )
            print(f"[migrate] Applied {path.name}")

        print(f"[migrate] Done — {len(pending)} migration(s) applied.")
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(_apply())
    except Exception as exc:  # noqa: BLE001 - surface failure to the deploy log
        print(f"[migrate] ERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
