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
cp -r env.example env          # Windows: Copy-Item -Recurse env.example env
# edit env/.env.development (and staging/production overlays as needed)
uv run alembic upgrade head
```

### Environment files

| Path | Role | Git? |
|------|------|------|
| `env.example/` | Templates (same filenames as runtime) | Yes |
| `env/` | Real values (copy of templates, then edit) | No (`env/` is gitignored) |

| File under `env/` | Role |
|-------------------|------|
| `.env` | Shared defaults (no secrets) |
| `.env.development` | Local development overlay (default) |
| `.env.staging` | Prod-like staging overlay |
| `.env.test` | Test-profile overlay (optional; pytest uses `conftest` DB) |
| `.env.production` | Production overlay |

`config.py` loads `env/.env`, then `env/.env.{TASKMAN_ENV}`. On key clashes, the profile wins. Process environment (Compose, CI, Just) always wins over files. `TASKMAN_ENV` selects the profile and defaults to `development` when unset.

| Profile | Typical `DATABASE_URL` |
|---------|-------------------------|
| `development` | `sqlite+aiosqlite:///./database.db` |
| `staging` | `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME` |
| `test` | `sqlite+aiosqlite:///./test.db` |
| `production` | `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME` |

## Run

Preferred entrypoints use [Just](https://github.com/casey/just) (`just --list` for all recipes).

Development (default — `env/.env` + `env/.env.development`):

```bash
just dev
# equivalent without Just: uv run fastapi dev
```

Staging / production (Postgres DBs must exist; secrets in the matching overlay):

```bash
just staging
just prod
```

Migrations and tests:

```bash
just migrate           # development
just migrate-staging
just migrate-prod
just migrate-test      # optional file-based test DB
just pytest            # pytest (isolated DB via conftest)
just test              # fastapi dev on :8765 (TASKMAN_ENV=test)
```

- Health: `GET /health`
- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Authorize in `/docs` with a token from `POST /auth/login` (use email as username).

### Dev server and port cleanup (Windows)

`fastapi dev` / uvicorn `--reload` runs a **parent watcher** plus a **child worker** that holds the listen socket. On Windows, a non-clean stop (closing the terminal, overlapping `just dev` sessions, forced kill) can leave the **worker orphaned**: the port still looks taken, but requests hang or fail.

`just dev` (and `just test` on `:8765`) therefore run a private `free-port` step first (`scripts/free-port.ps1`). It stops whoever is listening on that port **and** any child processes of that listener, then starts the app. You normally just run `just dev` — no extra flags.

`just staging` / `just prod` use `fastapi run` (no reload) and do **not** free the port automatically.

If the port is still stuck, inspect and kill manually in PowerShell:

```powershell
netstat -ano | findstr ":8000"
# note the LISTENING PID in the last column, then:
taskkill /PID <pid> /T /F
```

`/T` kills the process tree (reloader parent and worker). Confirm with `netstat -ano | findstr ":8000"` again — no `LISTENING` line means the port is free. Use `:8765` (or another port) the same way when needed.

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
