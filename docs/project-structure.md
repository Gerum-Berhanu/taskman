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
│   ├── deps.py             # dependency injection — wire stores → services → routes
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
│   ├── database/           # persistence layer
│   │   ├── stores.py       # in-memory TaskStore / UserStore (temporary)
│   │   ├── session.py      # SQLAlchemy engine + session (future)
│   │   └── models.py       # ORM table models (future)
│   │
│   ├── models/             # Pydantic API contracts (request/response shapes)
│   │   ├── task.py         # TaskCreate, TaskRead, TaskUpdate, TaskStatus
│   │   └── user.py         # UserCreate, UserRead, Token, etc.
│   │
│   └── services/           # business logic ("the business seam")
│       ├── task_service.py
│       ├── user_service.py
│       └── auth_service.py
│
├── tests/                  # automated tests (mirror app/ layout when added)
└── docs/                   # handbook
```

> **Naming note:** `app/models/` holds **Pydantic schemas** (API contract). `app/database/models.py` will hold **ORM models** (database tables). Same word, different layers — check the path.

---

## Layers at a glance

| Layer | Folder | Knows about | Must NOT contain |
|---|---|---|---|
| HTTP | `api/v1/` | HTTP status codes, request/response shapes, auth headers | Business rules, DB queries, password hashing |
| Services | `services/` | Domain rules, orchestration | FastAPI types, HTTP exceptions (mostly) |
| Persistence | `database/` | How data is stored and retrieved | HTTP concerns, route logic |
| API contract | `models/` | Validation of JSON in/out | Business logic, SQL |
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
database/*       ← read/write data (stores today, SQLAlchemy later)
  │
  ▼
models/*.py      ← shape the JSON response (response_model)
  │
  ▼
Client
```

**Example — `POST /tasks` (authenticated):**

1. `tasks.py` receives JSON → validated as `TaskCreate` (from `models/task.py`).
2. `deps.py` resolves `TaskServiceDep` and ensures `get_current_user` ran (router-level dependency).
3. `TaskService.create()` calls `TaskStore.create()` with the task fields.
4. `TaskStore` assigns `id`, `status`, timestamps and saves to the in-memory dict.
5. Route returns the dict; FastAPI serializes it as `TaskRead`.

---

## File-by-file guide

### `main.py`

- Creates the `FastAPI` app.
- Calls `setup_logging()` once at startup.
- Registers routers from `api/v1/`.
- Keeps **no** business logic — only bootstrap.

### `deps.py`

The **wiring layer**. FastAPI `Depends()` functions live here:

- `get_task_store` / `get_user_store` → return singleton stores.
- `get_task_service` / `get_user_service` / `get_auth_service` → build services with their dependencies.
- `get_current_user` → decode JWT, load user (used by protected routes).
- `get_task_or_404` → shared 404 lookup for task routes.

Routes import typed aliases like `TaskServiceDep` instead of constructing services themselves.

When you swap in-memory stores for a real DB session, you change wiring **here** — routes and services stay the same.

### `api/v1/`

One file per resource. Each file defines an `APIRouter` with a URL prefix.

**Do here:** route decorators, `response_model`, status codes, map domain errors → `HTTPException`.

**Don't do here:** password hashing, JWT encoding, direct store access, complex validation rules.

### `services/`

One service class per resource (or cross-cutting concern like auth).

| Service | Responsibility |
|---|---|
| `TaskService` | Task CRUD — delegates to `TaskStore` |
| `UserService` | User lookup, registration (hashing password before save) |
| `AuthService` | Login verification, JWT create/decode |

Services raise **domain exceptions** (e.g. `EmailAlreadyRegisteredError`). Routes catch those and pick the HTTP status.

Services are easy to unit-test: pass a fake store, no HTTP involved.

### `database/`

| File | Status | Purpose |
|---|---|---|
| `stores.py` | **Active** | In-memory `TaskStore` / `UserStore` — temporary until SQLAlchemy |
| `session.py` | Placeholder | Engine + `get_db()` session factory |
| `models.py` | Placeholder | SQLAlchemy / SQLModel table classes |

Stores should only **persist and retrieve** — no password hashing (that lives in `UserService`).

### `models/` (Pydantic)

Request and response schemas per resource. FastAPI uses these for:

- Automatic validation of incoming JSON.
- OpenAPI docs at `/docs`.
- Serializing outgoing responses (`response_model=...`).

If you add a field to the API, start here.

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

1. **`models/workspace.py`** — `WorkspaceCreate`, `WorkspaceRead`, …
2. **`database/stores.py`** (or future ORM repo) — persistence methods.
3. **`services/workspace_service.py`** — business rules.
4. **`deps.py`** — `get_workspace_service`, `WorkspaceServiceDep`.
5. **`api/v1/workspaces.py`** — routes; call the service, return schemas.
6. **`main.py`** — `app.include_router(workspaces.router)` (already registered).

For a new endpoint on an existing resource, touch `models/` → `services/` → `api/v1/` in that order.

---

## Dependency injection rule

Start with FastAPI built-in `Depends()` (what we use now). Only introduce a DI container if the app grows many cross-cutting dependencies.

Current chain:

```
Route
  └─ TaskServiceDep
       └─ get_task_service
            └─ TaskStore (singleton via get_task_store)
```

For tests, override dependencies on the app — e.g. swap `get_task_store` with a fresh in-memory store — without changing route code.

---

## What changes later

| Today | Next slice |
|---|---|
| `database/stores.py` (in-memory dicts) | `database/session.py` + `database/models.py` (SQLAlchemy) |
| Services call `TaskStore` directly | Services call store/repo through a DB session from `deps.py` |
| No `tests/` yet | `tests/api/v1/` mirroring `app/api/v1/` |

The layer boundaries stay the same; only the persistence implementation swaps out.

---

## Quick rules

1. **Routes stay thin** — call a service, return a schema.
2. **Business logic lives in services** — not in routes or stores.
3. **Stores/repos only persist** — no hashing, no JWT, no HTTP.
4. **Pydantic in `app/models/`** — ORM in `app/database/models.py`.
5. **Wire in `deps.py`** — routes never import singleton stores directly.
6. **Shared utilities in `core/`** — not scattered across services.

Project title: **Taskman**
