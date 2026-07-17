"""
Test fixtures.

Keeps the smoke test hermetic — no external Postgres/Redis needed:
  - DATABASE_URL is pointed at a temp async-SQLite file *before* the app config
    is imported (settings are cached at import time).
  - Redis is replaced with a tiny in-process fake via dependency override.
"""

import os
import tempfile

# Must run before any `app.*` import so cached Settings pick these up.
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
os.environ["ENV"] = "test"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import init_models  # noqa: E402
from app.core.deps import get_db  # noqa: E402  (imported for symmetry / clarity)
from app.core.redis import get_redis  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_advice_if_empty  # noqa: E402


class FakeRedis:
    """Minimal async Redis stand-in supporting the ops the app uses."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def set(self, key, value, ex=None):  # noqa: ARG002 - TTL ignored in tests
        self._store[key] = str(value)

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, *keys):
        for key in keys:
            self._store.pop(key, None)

    async def ping(self):
        return True

    async def aclose(self):
        self._store.clear()


_fake_redis = FakeRedis()


async def _override_get_redis():
    return _fake_redis


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_schema():
    """Create tables + seed advice once for the whole test session."""
    await init_models()
    await seed_advice_if_empty()
    yield
    os.close(_DB_FD)
    os.remove(_DB_PATH)


@pytest_asyncio.fixture
async def client():
    """An httpx client wired to the ASGI app with Redis faked out."""
    app.dependency_overrides[get_redis] = _override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
