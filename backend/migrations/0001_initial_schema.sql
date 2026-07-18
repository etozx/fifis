-- =========================================================================
-- Momentum — initial schema (migration 0001)
-- Target: PostgreSQL
--
-- Creates every table the app needs: users, goals, tasks, focus_blocks,
-- reminders, daily_advice — plus the enum types and indexes.
--
-- This DDL is generated from and kept in sync with the SQLAlchemy models in
-- backend/app/models/. It is idempotent (guarded enum creation +
-- IF NOT EXISTS), so re-running it is safe.
--
-- Run against your Render Postgres, e.g.:
--   psql "$DATABASE_URL" -f backend/migrations/0001_initial_schema.sql
-- (Use the External connection string when running from your machine.)
-- =========================================================================

BEGIN;

-- --- Enum types ----------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE goalstatus AS ENUM ('active', 'completed', 'paused', 'archived');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE taskstatus AS ENUM ('todo', 'in_progress', 'done');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE focusstatus AS ENUM ('active', 'paused', 'completed', 'abandoned');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE scheduletype AS ENUM ('daily', 'weekly', 'custom');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- --- daily_advice (no FKs) ----------------------------------------------
CREATE TABLE IF NOT EXISTS daily_advice (
    id       SERIAL      NOT NULL,
    text     TEXT        NOT NULL,
    category VARCHAR(60) NOT NULL,
    tags     JSON        NOT NULL,
    weight   INTEGER     NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_daily_advice_id ON daily_advice (id);

-- --- users ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL       NOT NULL,
    email           VARCHAR(320) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(120) NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- --- goals ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS goals (
    id          SERIAL      NOT NULL,
    user_id     INTEGER     NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    category    VARCHAR(60) NOT NULL,
    target_date DATE,
    status      goalstatus  NOT NULL,
    tags        JSON        NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_goals_id ON goals (id);
CREATE INDEX IF NOT EXISTS ix_goals_user_id ON goals (user_id);

-- --- focus_blocks --------------------------------------------------------
CREATE TABLE IF NOT EXISTS focus_blocks (
    id                  SERIAL      NOT NULL,
    user_id             INTEGER     NOT NULL,
    goal_id             INTEGER,
    status              focusstatus NOT NULL,
    started_at          TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    ended_at            TIMESTAMP WITH TIME ZONE,
    last_resumed_at     TIMESTAMP WITH TIME ZONE,
    accumulated_seconds INTEGER     NOT NULL,
    notes               TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_focus_blocks_id ON focus_blocks (id);
CREATE INDEX IF NOT EXISTS ix_focus_blocks_user_id ON focus_blocks (user_id);
CREATE INDEX IF NOT EXISTS ix_focus_blocks_goal_id ON focus_blocks (goal_id);

-- --- reminders -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS reminders (
    id              SERIAL       NOT NULL,
    user_id         INTEGER      NOT NULL,
    goal_id         INTEGER,
    title           VARCHAR(200) NOT NULL,
    schedule_type   scheduletype NOT NULL,
    schedule_config JSON         NOT NULL,
    next_run_at     TIMESTAMP WITH TIME ZONE,
    is_active       BOOLEAN      NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_reminders_id ON reminders (id);
CREATE INDEX IF NOT EXISTS ix_reminders_user_id ON reminders (user_id);

-- --- tasks ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id           SERIAL       NOT NULL,
    goal_id      INTEGER      NOT NULL,
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    status       taskstatus   NOT NULL,
    due_date     DATE,
    position     INTEGER      NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_tasks_id ON tasks (id);
CREATE INDEX IF NOT EXISTS ix_tasks_goal_id ON tasks (goal_id);

COMMIT;
