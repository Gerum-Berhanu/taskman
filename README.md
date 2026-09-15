# Taskman

REST API for workspace-scoped task management, built with FastAPI. JWT access tokens plus refresh-token sessions, SQLModel persistence (SQLite by default), Alembic migrations, and role-based access on workspaces (`viewer` / `editor` / `owner`).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
cp .env.example .env   # set SECRET_KEY; DATABASE_URL defaults to local SQLite
uv run alembic upgrade head
```

## Run

```bash
uv run uvicorn app.main:app --reload
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
| [docs/project-structure.md](docs/project-structure.md) | Folders, layers, where to add code |
| [docs/project-requirements.md](docs/project-requirements.md) | Capstone spec (target features) |
| [docs/commit-messages.md](docs/commit-messages.md) | Commit message conventions |
| [docs/README.md](docs/README.md) | Index of all docs |
