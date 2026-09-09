# Project structure

Taskman uses a **pragmatic layered layout**: thin HTTP routes, a services layer for business logic, a database layer for persistence, and a core layer for cross-cutting concerns. Folders are organized by responsibility, not by framework.

## Folder tree

```
task_mng/
├── README.md
├── .gitignore
├── pyproject.toml          # uv project + dependencies
├── uv.lock
├── .env.example            # safe template for env vars
├── app/
│   ├── main.py             # app entrypoint — create FastAPI app, register routers
│   ├── deps.py             # dependency injection — wire repos → services → routes
│   │
│   ├── api/v1/             # HTTP layer (routes only)
│   │   ├── auth.py         # POST /auth/register, /auth/login; GET /auth/me
│   │   ├── tasks.py        # CRUD /tasks/*
│   │   └── workspaces.py   # /workspaces/* (stub)
│   │
│   ├── core/               # cross-cutting concerns (used everywhere)
│   │   ├── config.py       # Pydantic settings from .env
│   │   ├── logging.py      # centralized logging setup
│   │   ├── security.py     # password hashing / verification
│   │   ├── timeutils.py    # utcnow() helper
│   │   └── exceptions.py   # app-level errors (mapped to HTTP in routes)
│   │
│   ├── database/           # SQL wiring (engine, ORM models)
│   │   ├── session.py      # SQLModel engine + create_db_and_tables
│   │   └── models.py       # ORM table models (User, Task)
│   │
│   ├── repositories/       # one SQL repository per domain
│   │   ├── task.py         # TaskRepository + TaskRecord
│   │   ├── user.py         # UserRepository + UserRecord
│   │   └── user_session.py # UserSessionRepository + UserSessionRecord
│   │
│   ├── schemas/            # Pydantic API contracts (request/response shapes)
│   │   ├── task.py         # TaskCreate, TaskRead, TaskUpdate, TaskStatus
│   │   └── user.py         # UserCreate, UserRead, Token, etc.
│   │
│   └── services/           # business logic ("the business seam")
│       ├── task.py
│       ├── user.py
│       └── auth.py
│
├── tests/                  # pytest API tests with isolated temporary databases
│   ├── conftest.py         # test database and client fixtures
│   └── test_api.py         # endpoint behavior tests
└── docs/                   # handbook
```

> **Naming note:** `app/schemas/` holds **Pydantic schemas** (API contract). Each `repositories/*.py` holds that domain’s **row shape** (`*Record` Pydantic models) next to its repository. ORM table models live under `app/models/`. Check the path.

---

## Layers at a glance

| Layer | Folder | Knows about | Must NOT contain |
|---|---|---|---|
| HTTP | `api/v1/` | HTTP status codes, request/response shapes, auth headers | Business rules, DB queries, password hashing |
| Services | `services/` | Domain rules, orchestration | FastAPI types, HTTP exceptions (mostly) |
| Persistence | `repositories/` + `database/` | How data is stored and retrieved | HTTP concerns, route logic |
| API contract | `schemas/` | Validation of JSON in/out | Business logic, SQL |
| Cross-cutting | `core/` | Config, logging, crypto, shared errors | Feature-specific logic |
| Wiring | `deps.py`, `main.py` | How layers connect | Business logic |

---

## Request flow

```
Client
  │
  ▼
main.py          ← creates app, calls setup_logging(), mounts routers
  │
  ▼
api/v1/*.py      ← parse HTTP, validate body (Pydantic), return status codes
  │
  ▼
deps.py          ← inject TaskService, UserService, AuthService, current user
  │
  ▼
services/*.py    ← business logic (register user, authenticate, CRUD tasks)
  │
  ▼
repositories/        ← persist/retrieve via UnitOfWork (SQL repos)
  │
  ▼
schemas/*.py     ← shape the JSON response (response_model)
  │
  ▼
Client
```

**Example — `POST /tasks` (authenticated):**

1. `tasks.py` receives JSON → validated as `TaskCreate` (from `schemas/task.py`).
2. `deps.py` resolves `TaskServiceDep` and ensures `get_current_user` ran (router-level dependency).
3. `TaskService.create()` calls `TaskRepository.create()` through the unit of work.
4. The SQL repository persists the row and returns a `TaskRecord`.
5. Route returns the record; FastAPI serializes it as `TaskRead`.

---

## File-by-file guide

### `main.py`

- Creates the `FastAPI` app.
- Calls `setup_logging()` once at startup.
- Registers routers from `api/v1/`.
- Keeps **no** business logic — only bootstrap.

### `deps.py`

The **wiring layer**. FastAPI `Depends()` functions live here:

- `get_uow` → one `UnitOfWork` (and DB session) per request.
- `get_task_service` / `get_user_service` / `get_auth_service` → build services with that UoW.
- `get_current_user` → decode JWT, load user (used by protected routes).

Routes import typed aliases like `TaskServiceDep` instead of constructing services themselves.

### `api/v1/`

One file per resource. Each file defines an `APIRouter` with a URL prefix.

**Do here:** route decorators, `response_model`, status codes, map domain errors → `HTTPException`.

**Don't do here:** password hashing, JWT encoding, direct repository access, complex validation rules.

### `services/`

One service class per resource (or cross-cutting concern like auth).

| Service | Responsibility |
|---|---|
| `TaskService` | Task CRUD — delegates to `TaskRepository` |
| `UserService` | Registration (hash password, reject duplicate email) |
| `AuthService` | Login verification, JWT create/decode, load user from token |

Services raise **domain exceptions** (e.g. `EmailAlreadyRegisteredError`). Routes catch those and pick the HTTP status.

### `database/`

| File | Status | Purpose |
|---|---|---|
| `session.py` | **Active** | SQLModel engine + `create_db_and_tables()` |
| `unit_of_work.py` | **Active** | Per-request transaction; exposes domain repositories |

### `repositories/`

| File | Purpose |
|---|---|
| `task.py` | `TaskRepository` + `TaskRecord` / `TaskUpdateData` |
| `user.py` | `UserRepository` + `UserRecord` |
| `user_session.py` | `UserSessionRepository` + `UserSessionRecord` |

One **SQL** repository class per domain. Row shapes (`*Record`) live in the same file. Repositories **persist and retrieve** — password hashing and JWT stay in services.

Services talk to repositories through `UnitOfWork`, not by constructing repos themselves.

### `schemas/` (Pydantic)

Request and response schemas per resource. FastAPI uses these for:

- Automatic validation of incoming JSON.
- OpenAPI docs at `/docs`.
- Serializing outgoing responses (`response_model=...`).

If you add a field to the API, start here. Do **not** reuse these as storage types (`UserRead` has no `hashed_password`; `UserRecord` does).

### `core/`

Shared infrastructure with no feature-specific knowledge:

- **`config.py`** — `Settings` from `.env` (`SECRET_KEY`, token expiry, etc.).
- **`logging.py`** — one `setup_logging()` called from `main.py`.
- **`security.py`** — `get_password_hash`, `verify_password`.
- **`timeutils.py`** — `utcnow()` for consistent timestamps.
- **`exceptions.py`** — errors that services raise and routes translate to HTTP.

---

## Where to add things

Use this checklist when building a new feature (e.g. workspaces):

1. **`schemas/workspace.py`** — `WorkspaceCreate`, `WorkspaceRead`, …
2. **`repositories/workspace.py`** — `WorkspaceRepository` + `WorkspaceRecord`.
3. **`services/workspace.py`** — business rules.
4. Wire the repo on `UnitOfWork`; add `get_workspace_service` in `deps.py`.
5. **`api/v1/workspaces.py`** — routes; call the service, return schemas.
6. **`main.py`** — `app.include_router(workspaces.router)` if not already registered.

For a new endpoint on an existing resource, touch `schemas/` → `services/` → `api/v1/` in that order.

---

## Dependency injection rule

Start with FastAPI built-in `Depends()` (what we use now). Only introduce a DI container if the app grows many cross-cutting dependencies.

Current chain:

```
Route
  └─ TaskServiceDep
       └─ get_task_service
            └─ UnitOfWork.tasks (TaskRepository)
```

Tests use the same SQL repositories against an isolated SQLite database (override `get_uow` / session wiring in fixtures).

---

## What changes later

| Today | Next slice |
|---|---|
| SQL repositories via `UnitOfWork` | Alembic migrations; later Postgres |
| API tests with temporary SQLite | Expand coverage as features are added |

The layer boundaries stay the same; only the database backend swaps out.

---

## Quick rules

1. **Routes stay thin** — call a service, return a schema.
2. **Business logic lives in services** — not in routes or repositories.
3. **Repos only persist** — no JWT, no HTTP; keep crypto at clear boundaries.
4. **Pydantic in `app/schemas/`** — `*Record` Pydantic models in `repositories/*.py` — ORM in `app/models/`.
5. **Wire in `deps.py` / `UnitOfWork`** — routes never construct repositories.
6. **Shared utilities in `core/`** — not scattered across services.

Project title: **Taskman**
