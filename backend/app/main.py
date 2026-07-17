"""
Application entrypoint / factory.

Wires middleware, mounts the versioned router tree under `/api/v1`, and runs
startup tasks (create tables + seed advice for the scaffold). CORS is configured
for credentialed cross-origin requests from the known frontend origin(s), which
is required for the session cookie to travel between the static site and the API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_models
from app.core.redis import close_redis
from app.routers import (
    advice,
    agent,
    analytics,
    auth,
    focus,
    goals,
    health,
    reminders,
)

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks."""
    # Scaffold-time schema creation + advice seeding. Production replaces the
    # create_all with Alembic migrations and seeds via a one-off job.
    await init_models()
    from app.seed import seed_advice_if_empty

    await seed_advice_if_empty()
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Goal tracking & focus-enhancement API.",
    lifespan=lifespan,
)

# Credentialed CORS: explicit origins only (wildcard is invalid with credentials).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers under the versioned API prefix.
for module in (health, auth, goals, focus, reminders, advice, analytics, agent):
    app.include_router(module.router, prefix=API_V1_PREFIX)


@app.get("/")
async def root():
    """Friendly root pointing at docs and health."""
    return {
        "service": settings.APP_NAME,
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
    }
