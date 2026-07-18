"""
Application configuration — the single source of truth for every environment
variable the backend reads.

ECC principle applied: configuration is centralized and typed. No module reads
`os.environ` directly; they depend on this `Settings` object instead, so the full
surface of required secrets/config is discoverable in one place and validated at
startup.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the environment / `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Runtime -----------------------------------------------------------
    ENV: str = Field(default="development", description="development | production")
    APP_NAME: str = "Momentum API"

    # --- Datastores --------------------------------------------------------
    # Async drivers are expected: postgresql+asyncpg://... and redis://...
    # A sqlite+aiosqlite fallback keeps local/dev boot friction low.
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./momentum.db")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # --- Auth / sessions ---------------------------------------------------
    # SECRET_KEY signs nothing sensitive on its own here (sessions are opaque
    # random ids stored in Redis) but is kept for future signed-cookie / CSRF use.
    SECRET_KEY: str = Field(default="dev-secret-change-me", alias="SESSION_SECRET")
    SESSION_COOKIE_NAME: str = "momentum_session"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = False  # must be True in production (HTTPS + SameSite=None)
    COOKIE_SAMESITE: str = "lax"  # "none" for cross-site static-site <-> API on Render

    # --- URLs / CORS -------------------------------------------------------
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"
    # Comma-separated list of allowed browser origins for credentialed CORS.
    # Kept as a raw string (not List[str]) so pydantic-settings doesn't try to
    # JSON-parse the env value; `cors_origins` exposes the parsed list.
    # Only relevant when the frontend is served from a *different* origin; in the
    # combined single-service deployment (API serves the built SPA) it's unused.
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Static frontend ---------------------------------------------------
    # Path to the built React app (Vite `dist`). When present, FastAPI serves it
    # so one service hosts both the API and the UI (same origin). Default is
    # relative to the backend working directory (`backend/`), i.e. `frontend/dist`
    # at the repo root.
    FRONTEND_DIST_DIR: str = "../frontend/dist"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins, parsed from the comma-separated setting."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once per process)."""
    return Settings()


settings = get_settings()
