# Log event tags

Stable **message prefixes** (event tags) used in application logs.  
Envelope fields (`timestamp`, `level`, `logger`, `request_id`) come from `app/observability/logging_setup.py` — not listed here.

**Convention:** `snake_case_tag key=%s key=%s …`  
**Ids:** UUIDs as strings. Use `actor_id=-` when no authenticated user is on the request.

**Timing:** domain events are scheduled with `UnitOfWork.after_commit` (`app/repositories/unit_of_work.py`) and only emit after a successful commit (not on rollback).

Put new high-value events in **services** (after a successful write). Keep tags stable so log search stays reliable.

---

## HTTP / middleware

Handlers and middleware live under `app/http/` (`exception_handlers.py`, `middleware/`).

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `http_access` | `INFO` (or `DEBUG` for `/health`, `/favicon.ico`) | After each request | `method`, `path`, `status`, `duration_ms` |
| `rate_limit_exceeded` | `WARNING` | Request blocked by Redis rate limiter (429) | `policy`, `client`, `path` |
| `rate_limit_backend_error` | `ERROR` (+ traceback) | Rate-limit backend failed; request allowed (fail-open) | `policy`, `client`, `path` |

---

## Infrastructure

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `redis_unavailable_at_startup` | `ERROR` (+ traceback) | Redis init/ping failed during lifespan; app continues without Redis | — |
| `cache_backend_error` | `ERROR` (+ traceback) | Task-summary Redis get/set/delete failed; request continued (fail-open) | `op`, `key` (and `workspace_id` on delete) |

---

## Exceptions

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `app_error` | `WARNING` if 4xx, else `ERROR` | Handled `AppError` | `status`, `detail`, `path`, `actor_id` |
| `unhandled_error` | `ERROR` (+ traceback) | Bare `Exception` (outer 500 path; skipped as client body when `DEBUG=true`) | `path`, `actor_id` |

Login/refresh failures show up as `app_error`, not separate service tags.

---

## Unit of work

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `after_commit_failed` | `ERROR` (+ traceback) | An `after_commit` callback raised after a successful DB commit (request still succeeds) | — |

---

## Auth / user (services)

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `user_registered` | `INFO` | User created | `user_id`, `email` |
| `user_login_succeeded` | `INFO` | Login issued tokens | `user_id` |
| `user_logout` | `INFO` | One session revoked | `user_id`, `session_id` |
| `user_logout_all` | `INFO` | All user sessions revoked | `user_id`, `session_id` |
| `email_sent` | `INFO` | Welcome email accepted by SMTP (after commit, background task) | `email`, `subject` |
| `email_send_failed` | `ERROR` (+ traceback) | Welcome email send raised after commit (registration still succeeded) | `email` |

---

## Workspaces (services)

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `workspace_created` | `INFO` | Workspace created | `workspace_id`, `owner_id` |
| `workspace_member_added` | `INFO` | Member row created (including owner on workspace create) | `workspace_id`, `member_id`, `role`, `actor_id` |

---

## Tasks (services)

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `task_created` | `INFO` | Task created | `workspace_id`, `task_id`, `actor_id` |
| `task_updated` | `INFO` | Task updated | `workspace_id`, `task_id`, `actor_id` |
| `task_deleted` | `INFO` | Task deleted | `workspace_id`, `task_id`, `actor_id` |

---

## Not logged as domain events

- Successful token refresh  
- `GET` list/detail reads (including summary cache hit/miss)  
- Failed login / invalid refresh (covered by `app_error`)
