# Momentum — Goal Tracking & Focus App

A goal-tracking and focus-enhancement app: set goals, break them into
milestones, run focus sessions, get a daily nudge and an AI-style recommendation
for what to work on next, and see your progress as **personal growth
intelligence** — not just a log.

- **Backend:** FastAPI (async) · PostgreSQL · Redis
- **Frontend:** React · Vite · Tailwind CSS · Recharts
- **Hosting:** Render — one web service (API serves the built UI) + Postgres + Redis

---

## Repository layout

```
backend/          FastAPI app (layered: core / models / schemas / routers / services)
frontend/         React + Vite + Tailwind SPA
render.yaml       One-click Render blueprint for all four resources
```

The backend follows a clean layered architecture (thin routers → services →
models) so business rules are testable without HTTP and ownership/auth logic
lives in one place.

---

## Features

| Area | What it does |
|------|--------------|
| **Goals & Tasks** | CRUD goals (title, description, category, target date, status, tags); each goal has ordered milestone tasks with their own lifecycle. |
| **Focus blocks** | Start / pause / resume / complete a focus session. Elapsed time is computed **server-side** from timestamps, so stats can't be gamed by a client timer. Full history retained. |
| **Reminders** | CRUD reminders (daily / weekly / custom) with `next_run_at` computed on write. (Delivery worker is a marked extension point.) |
| **Daily advice** | A stable-per-day motivational nudge from a seeded, weighted catalog. Cached in Redis. |
| **AI Focus Agent** | Recommends the next goal to work on, a focus duration, and a contextual nudge. Rule-based today, behind an interface built for a drop-in LLM later. |
| **Analytics dashboard** | Focus time per day, completed tasks, current/longest streak, and time distribution across categories — with Recharts visualizations. |

---

## Local development

### Prerequisites
- Python 3.11+, Node 18+
- Optional: a local PostgreSQL and Redis. Without them, the backend falls back to
  async SQLite; Redis, however, is required for sessions/cache when running the
  server (use a local Redis or Docker: `docker run -p 6379:6379 redis`).

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit DATABASE_URL / REDIS_URL as needed
uvicorn app.main:app --reload
```
- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

Run the smoke test (hermetic — uses async SQLite + an in-process fake Redis):
```bash
cd backend && pytest
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env          # leave VITE_API_BASE_URL empty to use the dev proxy
npm run dev                    # http://localhost:5173
```
The Vite dev server proxies `/api` to `http://localhost:8000`, so the session
cookie is same-origin locally and cross-site cookie friction is avoided.

---

## System design

### Architecture

```
        ┌────────────────┐        cookie (httpOnly session)        ┌────────────────┐
        │  React SPA     │  ───────────────────────────────────▶   │  FastAPI API   │
        │ (static site)  │  ◀───────────  JSON /api/v1  ─────────   │  (web service) │
        └────────────────┘                                          └───────┬────────┘
                                                                            │
                                              ┌─────────────────────────────┼───────────────┐
                                              ▼                             ▼                 ▼
                                       ┌────────────┐               ┌────────────┐    ┌──────────────┐
                                       │ PostgreSQL │               │   Redis    │    │ Focus Agent  │
                                       │ (durable)  │               │ sessions + │    │  (module,    │
                                       │            │               │  cache     │    │  LLM-ready)  │
                                       └────────────┘               └────────────┘    └──────────────┘
```

The API is **stateless** — no session state lives in process memory — so it
scales horizontally: any instance can serve any request because the session and
cache state live in Redis and the durable state in Postgres.

### Data flow (example: completing a focus block)
1. Browser calls `POST /api/v1/focus/{id}/complete` with the session cookie.
2. `get_current_user` resolves the cookie → Redis → user id → DB user.
3. `focus_service` banks the running interval into `accumulated_seconds` using
   **server timestamps** and marks the block completed.
4. Next dashboard load calls `GET /analytics/summary`; the service aggregates
   focus/tasks/streaks/categories and **caches the result in Redis** (short TTL).

### How Redis is used
- **Sessions (auth):** login stores `sess:<random-id> → user_id` with a TTL; the
  browser holds only the opaque id in an httpOnly cookie. Logout is a single
  `DEL` — clean server-side revocation, and no token material exposed to JS.
- **Read cache:** analytics summaries and the daily-advice pick are cached with a
  short TTL to absorb repeated dashboard loads without recomputing aggregates.

### How the AI agent integrates
The agent lives in `backend/app/services/focus_agent.py` behind an abstract
`FocusAgent` interface with one method, `recommend(context) → AgentRecommendation`.
The router builds an `AgentContext` (goals, tasks, recent focus history) and
delegates. Today's `RuleBasedFocusAgent` scores goals by deadline urgency,
staleness, and open-task count, and adapts the suggested duration from the user's
recent sessions. Swapping in an `LLMFocusAgent` later means implementing the same
interface and changing one line in `get_focus_agent()` — **no router, schema, or
frontend changes**. The daily-advice service is structured the same way for a
future AI generator.

### Auth choice — session cookies (justification)
Session cookies backed by Redis were chosen over JWT because:
- **Revocation is trivial** (delete the Redis key) — no token-blocklist plumbing.
- **No token in JavaScript**, so no XSS token-theft surface (cookie is httpOnly).
- It gives **Redis a first-class role** already needed for caching.

The tradeoff — cross-site cookies between the static frontend and the API on
different Render subdomains — is handled with `Secure` + `SameSite=None` cookies
and credentialed CORS restricted to an explicit origin allowlist.

### Deployment on Render (single service)
The app deploys as **one web service** that builds the React frontend and serves
it from FastAPI, so the UI and API share a single origin (no cross-site cookie or
CORS setup). `render.yaml` provisions three resources:
- **momentum** — Python web service that also serves the built SPA.
  `healthCheckPath: /api/v1/health`; `DATABASE_URL`/`REDIS_URL` wired
  automatically from the managed resources.
  - **Build:** `cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt`
  - **Start:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **momentum-db** — managed PostgreSQL. (The app normalizes the `postgresql://`
  connection string to the `+asyncpg` driver at startup, so no manual editing.)
- **momentum-redis** — managed Redis with `noeviction` so sessions aren't dropped.

FastAPI serves `frontend/dist` when present (`FRONTEND_DIST_DIR`), returning
`index.html` for client-side routes so React Router works on a hard refresh; API
routes (`/api/v1/*`) and `/docs` always take precedence. Nothing to wire up
manually after deploy. (To split into a separate static site instead, host
`frontend/dist` on a CDN and set `COOKIE_SAMESITE=none` + `CORS_ORIGINS` on the
API.)

---

## API surface (all under `/api/v1`)

```
POST   /auth/register        POST /auth/login       POST /auth/logout    GET /auth/me
GET    /goals                POST /goals            GET/PATCH/DELETE /goals/{id}
POST   /goals/{id}/tasks     PATCH/DELETE /goals/{id}/tasks/{task_id}
POST   /focus/start          POST /focus/{id}/pause|resume|complete      GET /focus/history
GET    /reminders            POST /reminders        PATCH/DELETE /reminders/{id}
GET    /advice/today
GET    /analytics/summary?range_days=30
GET    /agent/recommendation
GET    /health
```

---

## Notable extension points (intentionally left as stubs)
- **Reminder delivery:** a Render Cron Job polling `reminders WHERE is_active AND
  next_run_at <= now()`, dispatching notifications, and advancing `next_run_at`.
- **LLM agent / advice:** drop-in implementations behind the existing interfaces.
- **Migrations:** Alembic replaces the scaffold's `create_all` for production
  schema management.
