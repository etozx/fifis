"""
Application entrypoint / factory.

Wires middleware, mounts the versioned router tree under `/api/v1`, runs startup
tasks (create tables + seed advice for the scaffold), and — when a built frontend
is present — serves the React SPA from the same service so one deployment hosts
both the API and the UI (same origin, so no cross-site cookie/CORS needed).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


# ---------------------------------------------------------------------------
# Serve the built React SPA (single-service deployment).
#
# If the Vite `dist` directory exists, mount it so this one service hosts both
# the API and the UI. The catch-all returns real files when they exist and falls
# back to index.html for client-side routes (e.g. /goals/4), which is what makes
# React Router work on a hard refresh. It is registered LAST so /api/v1/*, /docs,
# and /openapi.json (registered earlier) always win.
# ---------------------------------------------------------------------------
_dist = Path(settings.FRONTEND_DIST_DIR).resolve()

if _dist.is_dir():
    # Hashed build assets under /assets are served directly (efficient + cached).
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve a static file if it exists, else the SPA shell (index.html)."""
        # Never let the SPA shadow the API surface.
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404, detail="Not found")

        candidate = (_dist / full_path).resolve()
        # Guard against path traversal, then serve the concrete file if present.
        if (
            full_path
            and _dist in candidate.parents
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")

else:
    @app.get("/")
    async def root():
        """Fallback root when no built frontend is bundled (API-only mode)."""
        return {
            "service": settings.APP_NAME,
            "docs": "/docs",
            "health": f"{API_V1_PREFIX}/health",
        }
