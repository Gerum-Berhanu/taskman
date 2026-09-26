# Log event tags

Stable **message prefixes** (event tags) used in application logs.  
Envelope fields (`timestamp`, `level`, `logger`, `request_id`) come from the logging setup — not listed here.

**Convention:** `snake_case_tag key=%s key=%s …`  
**Ids:** UUIDs as strings. Use `actor_id=-` when no authenticated user is on the request.

**Timing:** domain events are scheduled with `UnitOfWork.after_commit` and only emit after a successful commit (not on rollback).

Put new high-value events in **services** (after a successful write). Keep tags stable so log search stays reliable.

---

## HTTP / middleware

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `http_access` | `INFO` (or `DEBUG` for `/health`, `/favicon.ico`) | After each request | `method`, `path`, `status`, `duration_ms` |

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
- `GET` list/detail reads  
- Failed login / invalid refresh (covered by `app_error`)
