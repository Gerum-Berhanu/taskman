# Taskman

REST API for workspace-scoped task management, built with FastAPI. JWT access tokens plus refresh-token sessions, SQLModel persistence, Alembic migrations, Redis-backed rate limiting, and role-based access on workspaces (`viewer` / `editor` / `owner`).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 18+ (local profiles and Compose)
- Redis 7+ / 8.x (rate limiting; app pings Redis on startup)
- Optional: [Just](https://github.com/casey/just), [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Setup

```bash
uv sync
cp -r env.example env          # Windows: Copy-Item -Recurse env.example env
# edit env/.env.development, REDIS_URL, DATABASE_URL, SECRET_KEY, etc.
# start a local Redis that matches REDIS_URL (see below)
uv run alembic upgrade head
```

### Environment files

| Path | Role | Git? |
|------|------|------|
| `env.example/` | Templates (same layout as runtime) | Yes |
| `env/` | Real values (copy of templates, then edit) | No (`env/` is gitignored) |

| File under `env/` | Role |
|-------------------|------|
| `.env` | Shared defaults (no secrets) |
| `.env.development` | Local development overlay (default) |
| `.env.staging` | Staging overlay (host runs + Compose base) |
| `.env.test` | Test overlay (`just pytest` / `just test`) |
| `.env.production` | Production overlay |
| `env.compose/.env.staging` | Compose-only Postgres/Redis vars for staging |
| `env.compose/.env.production` | Compose-only Postgres/Redis vars for production |

`config.py` loads `env/.env`, then `env/.env.{TASKMAN_ENV}`. On key clashes, the profile wins. Process environment (Compose, CI, Just) always wins over files. `TASKMAN_ENV` selects the profile and defaults to `development` when unset.

Compose stacks also pass `--env-file env/env.compose/.env.*` so `${POSTGRES_*}` / `${REDIS_*}` can be interpolated into `DATABASE_URL` / `REDIS_URL` for the API container (host overlays keep `localhost` for Windows Postgres/Redis).

| Profile | Typical local `DATABASE_URL` | Typical local `REDIS_URL` |
|---------|------------------------------|---------------------------|
| `development` | Postgres on the host | Host-published Redis (e.g. `:6379` or `:6380`) |
| `staging` | Host Postgres **or** overridden in Compose | Same pattern |
| `test` | Overridden to temp SQLite in `conftest` | Host Redis (pytest still needs Redis up) |
| `production` | Host Postgres **or** overridden in Compose | Same pattern |

## Redis before local API runs

The app **connects to Redis during lifespan**. For `just dev`, `just staging`, `just prod`, `just test`, or `just pytest`, start a Redis that matches that profile’s `REDIS_URL` first (Docker example):

```powershell
docker start redis_development   # or: docker run -d --name redis_development -p 6379:6379 redis:8.6
```

Use a separate container/port per environment if you isolate Redis that way. Compose staging/prod start their own `redis` service — no manual container needed for those stacks.

## Run (host)

Preferred entrypoints use [Just](https://github.com/casey/just) (`just --list` for all recipes).

```bash
just dev                 # development (fastapi dev)
just run                 # development without reload
just staging             # TASKMAN_ENV=staging
just prod                # TASKMAN_ENV=production
just test                # fastapi dev on :8765 with test profile
```

Migrations and tests:

```bash
just migrate             # development
just migrate-staging
just migrate-prod
just migrate-test
just pytest              # TASKMAN_ENV=test; rate limiting off unless a test opts in
```

- Health: `GET /health`
- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Authorize in `/docs` with a token from `POST /auth/login` (use email as username).

### Port already in use

`fastapi dev` / uvicorn `--reload` runs a **parent watcher** plus a **child worker** that holds the listen socket. A non-clean stop can leave the worker orphaned so the port stays taken.

**Windows:**

```powershell
netstat -ano | findstr ":8000"
taskkill /PID <pid> /T /F
```

**Unix:**

```bash
lsof -iTCP:8000 -sTCP:LISTEN
kill -9 <pid>
```

## Run (Docker Compose)

Staging is the base stack (`compose.yaml`: `api` + Postgres + Redis). Production is the same file plus `compose.prod.yaml` overrides (no published API port by default, separate volumes, production env).

```bash
just compose-staging       # build + up
just compose-staging-down

just compose-prod
just compose-prod-down
```

After staging is up, migrate inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Staging API (when published): [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs).

### Commands inside containers

One-off command in a **Compose** service (preferred when the stack was started with Compose):

```bash
docker compose exec api <command> <args>
# example: docker compose exec api alembic upgrade head
# example: docker compose exec redis redis-cli ping
```

Same idea for any running container (Compose or `docker run`), by name or id:

```bash
docker exec <container_name_or_id> <command> <args>
# example: docker exec redis_development redis-cli ping
```

`exec` uses the **already-running** container environment (`DATABASE_URL`, `REDIS_URL`, etc.). You do not need `--env-file` on `exec` for that; `--env-file` matters for `up`/`build` interpolation in this project.

## Rate limiting

Redis sliding-window limits apply when `RATE_LIMIT_ENABLED=true` (default in non-test overlays). Auth `POST` routes use a tighter policy. Blocked requests return **429** with `Retry-After` and log `rate_limit_exceeded`. Pytest keeps limiting off globally; dedicated tests in `tests/test_rate_limit.py` turn it on via monkeypatch.

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
| [docs/log-events.md](docs/log-events.md) | Stable log event tags |
| [docs/README.md](docs/README.md) | Index of all docs |
