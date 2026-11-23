# Taskman

REST API for workspace-scoped task management, built with FastAPI. JWT access tokens plus refresh-token sessions, SQLModel persistence, Alembic migrations, Redis-backed rate limiting, and role-based access on workspaces (`viewer` / `editor` / `owner`).

## Contents

- [Requirements](#requirements)
- [Setup](#setup)
  - [Environment files](#environment-files)
- [Redis before local API runs](#redis-before-local-api-runs)
- [Run (host)](#run-host)
  - [Port already in use](#port-already-in-use)
- [Run (Docker Compose)](#run-docker-compose)
  - [Commands inside containers](#commands-inside-containers)
- [API (implemented)](#api-implemented)
- [Documentation](#documentation)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 18+ (local profiles and Compose)
- Redis 7+ / 8.x (cache / rate limit / registration indexes; preferred at startup, app still boots if a client fails init)
- Optional: [Just](https://github.com/casey/just), [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Setup

```bash
uv sync
cp -r env-example env          # Windows: Copy-Item -Recurse env-example env
# edit env/.env.development, REDIS_*_URL, DATABASE_URL, SECRET_KEY, etc.
# start a local Redis that matches REDIS_CACHE_URL / REDIS_RATE_LIMIT_URL / REDIS_REGISTRATION_URL (see below)
uv run alembic upgrade head
```

### Environment files

| Path | Role | Git? |
|------|------|------|
| `env-example/` | Templates (same layout as runtime) | Yes |
| `env/` | Real values (copy of templates, then edit) | No (`env/` is gitignored) |

| File under `env/` | Role |
|-------------------|------|
| `.env` | Shared defaults (no secrets) |
| `.env.development` | Local development overlay (default) |
| `.env.staging` | Staging overlay (host runs + Compose base) |
| `.env.test` | Test overlay (`just pytest` / `just test`) |
| `.env.production` | Production overlay |
| `env-compose/.env.staging` | Compose-only Postgres/Redis/RabbitMQ vars for staging |
| `env-compose/.env.production` | Compose-only Postgres/Redis/RabbitMQ vars for production |

`config.py` loads `env/.env`, then `env/.env.{TASKMAN_ENV}`. On key clashes, the profile wins. Process environment (Compose, CI, Just) always wins over files. `TASKMAN_ENV` selects the profile and defaults to `development` when unset.

Compose stacks also pass `--env-file env/env-compose/.env.*` so `${POSTGRES_*}` / `${REDIS_*}` / `${RABBITMQ_*}` can be interpolated into `DATABASE_URL` / `REDIS_CACHE_URL` / `REDIS_RATE_LIMIT_URL` / `REDIS_REGISTRATION_URL` / `RABBITMQ_URL` for the `api` and `worker` containers (host overlays keep `localhost` for Windows Postgres/Redis/RabbitMQ). One Redis process is enough; the three URLs typically share host/port and use indexes `/0` (cache), `/1` (rate limit), `/2` (registration).

| Profile | Typical local `DATABASE_URL` | Typical local Redis URLs |
|---------|------------------------------|--------------------------|
| `development` | Postgres on the host | Host-published Redis (e.g. `:6379` or `:6380`) with `/0` `/1` `/2` |
| `staging` | Host Postgres **or** overridden in Compose | Same pattern |
| `test` | Overridden to temp SQLite in `conftest` | Host Redis (pytest still needs Redis up) |
| `production` | Host Postgres **or** overridden in Compose | Same pattern |

## Redis before local API runs

The app **tries to connect each Redis client during lifespan** (`init_all_fail_open`). If a client fails, the API still starts and logs `redis_unavailable_at_startup` with that client's `role`. At request time, policies differ: **cache** stays fail-open (summary falls through to Postgres); **rate limit** and **registration** Redis fail closed with **503**; see [docs/rate-limiting.md](docs/rate-limiting.md), [docs/caching.md](docs/caching.md), and [docs/registration-otp.md](docs/registration-otp.md). For `just dev`, `just staging`, `just prod`, `just test`, or `just pytest`, start a Redis that matches those profile URLs first so limits and registration tickets actually work (Docker example):

```powershell
docker start redis_development   # or: docker run -d --name redis_development -p 6379:6379 redis:8.6
```

Use a separate container/port per environment if you isolate Redis that way. Compose staging/prod start their own `redis` service; no manual container needed for those stacks.

## RabbitMQ + Celery worker and Beat (host)

OTP mail, welcome mail, and task export enqueue onto RabbitMQ. Expired client sessions are purged on a schedule (`SESSION_PURGE_INTERVAL_SECONDS`): **Celery Beat** publishes the purge task; a **worker** runs it. For `just dev` you need a broker, one worker, and one Beat process (Compose stacks already include `rabbitmq` + `worker` + `beat`). Run only **one** Beat per environment.

```powershell
docker start rabbitmq_development
# or: docker run -d --name rabbitmq_development -p 5672:5672 -p 15672:15672 rabbitmq:4-management-alpine

uv run celery -A app.workers.celery_app worker --loglevel=INFO --pool=solo
uv run celery -A app.workers.celery_app beat --loglevel=INFO
```

Point `RABBITMQ_URL` in private `env/.env.development` at that broker. Manual purge without Beat: `just purge-expired-sessions`. Details: [docs/email.md](docs/email.md#background-jobs-celery--rabbitmq).

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
just purge-expired-sessions   # delete expired client_sessions (manual; + -staging/-prod/-test)
```

- Health: `GET /health`
- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Authorize in `/docs` by pasting the `access_token` from `POST /auth/login` (`{"email", "password"}`). Access stays in the JSON body (`Bearer`); refresh and `device_id` are HttpOnly cookies - see [docs/auth-cookies.md](docs/auth-cookies.md).

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

Staging is the base stack (`compose.yaml`: `api` + Postgres + Redis + RabbitMQ + Celery `worker` + Celery `beat`). Production is the same file plus `compose.prod.yaml` overrides (no published API port by default, separate volumes, production env).

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

`exec` uses the **already-running** container environment (`DATABASE_URL`, `REDIS_*_URL`, etc.). You do not need `--env-file` on `exec` for that; `--env-file` matters for `up`/`build` interpolation in this project.

## API (implemented)

| Area | Paths |
|------|--------|
| Auth | `POST /auth/register`, `/login`, `/refresh`, `/logout`; `GET /auth/me`, `/sessions`; `DELETE /auth/sessions`, `/sessions/{id}` |
| Workspaces | `POST /workspaces`; `POST /workspaces/{id}/members` (owner) |
| Tasks | CRUD under `/workspaces/{workspace_id}/tasks` (RBAC: viewer / editor / owner) |

Full target spec (including not-yet-built pieces): [docs/project-requirements.md](docs/project-requirements.md).

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/project-requirements.md](docs/project-requirements.md) | Capstone spec (target features) |
| [docs/auth-cookies.md](docs/auth-cookies.md) | Access Bearer + HttpOnly refresh/device cookies; session purge via Beat |
| [docs/rate-limiting.md](docs/rate-limiting.md) | Redis rate limiting (fail-closed **503**) |
| [docs/caching.md](docs/caching.md) | Task summary Redis cache (fail-open) |
| [docs/registration-otp.md](docs/registration-otp.md) | Email OTP registration (Redis DB 2; broker fail-closed) |
| [docs/email.md](docs/email.md) | SMTP/Resend + Celery worker/Beat (OTP/export **503**; welcome best-effort; session purge) |
| [docs/commit-messages.md](docs/commit-messages.md) | Commit message conventions |
| [docs/pr-guide.md](docs/pr-guide.md) | Pull request description guide |
| [docs/log-events.md](docs/log-events.md) | Stable log event tags |
| [docs/README.md](docs/README.md) | Index of all docs |
