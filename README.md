# Taskman

REST API for workspace-scoped task management, built with FastAPI. JWT access tokens plus refresh-token sessions, SQLModel persistence (SQLite in development, PostgreSQL in production), Alembic migrations, and role-based access on workspaces (`viewer` / `editor` / `owner`).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 18+ (when using the production profile or a local Postgres DB)
- Optional: [Just](https://github.com/casey/just) for short cross-platform run commands

## Setup

```bash
uv sync
cp .env.example .env
cp .env.development.example .env.development
# optional Postgres / production overlay:
# cp .env.production.example .env.production
uv run alembic upgrade head
```

### Environment files

| File | Role |
|------|------|
| `.env` | Shared defaults (no secrets) |
| `.env.development` | Development overlay (default) |
| `.env.production` | Production overlay |

`config.py` loads `.env`, then `.env.{TASKMAN_ENV}`. On key clashes, the profile wins. Process environment (Compose, CI, Just) always wins over files. `TASKMAN_ENV` selects the profile (`development` | `production`) and defaults to `development` when unset.

| Profile | Typical `DATABASE_URL` |
|---------|-------------------------|
| `development` | `sqlite+aiosqlite:///./database.db` |
| `production` | `postgresql+asyncpg://user:pass@host:5432/dbname` |

## Run

Development (default — `.env` + `.env.development`):

```bash
uv run uvicorn app.main:app --reload
# or: just dev
```

Production overlay (Postgres must be running; secrets in `.env.production`):

```bash
just prod
# equivalent: set TASKMAN_ENV=production in the process, then uv run uvicorn app.main:app
```

Migrations:

```bash
just migrate        # development DB
just migrate-prod   # production DB
```

Or: `uv run fastapi dev`

- Health: `GET /health`
- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Authorize in `/docs` with a token from `POST /auth/login` (use email as username).

## API (implemented)

| Area | Paths |
|------|--------|
| Auth | `POST /auth/register`, `/login`, `/refresh`, `/logout`, `/logout-all`; `GET /auth/me` |
| Workspaces | `POST /workspaces`; `POST /workspaces/{id}/members` (owner) |
| Tasks | CRUD under `/workspaces/{workspace_id}/tasks` (RBAC: viewer / editor / owner) |

Full target spec (including not-yet-built pieces): [docs/project-requirements.md](docs/project-requirements.md).

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/project-requirements.md](docs/project-requirements.md) | Capstone spec (target features) |
| [docs/commit-messages.md](docs/commit-messages.md) | Commit message conventions |
| [docs/pr-guide.md](docs/pr-guide.md) | Pull request description guide |
| [docs/README.md](docs/README.md) | Index of all docs |
