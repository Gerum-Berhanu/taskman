# Log event tags

Stable message tags for app logs. Envelope (`timestamp`, `level`, `category`, `logger`, `request_id`) comes from `app/observability/`. Domain write events emit only via `UnitOfWork.after_commit` after a successful commit.

## Format

- Shape: `snake_case_tag key=%s ...` — no prose; no `category=` in the message.
- Pass the template and args to the logger (`logger.info("tag key=%s", value)`); do not pre-build the message string.
- On failure inside an `except`: prefer `logger.exception(...)` over `logger.error(..., exc_info=True)`.
- Domain success tags: past tense (`task_created`). HTTP/infra/errors: noun or `*_error` / `*_failed`.
- Ids as strings; missing actor/session/user-like ids → `-`.
- Use `repr(value)` when the value may contain spaces (e.g. `subject`, `app_error` `detail`).
- Field keys: reuse the catalog below.

## Category

Closed set: `http` | `domain` | `infra` | `ops`.  
`CategoryFilter` maps `app.<package>` → category (unknown / non-`app.*` → `ops`). No `extra=` at call sites — put the logger in the right package.

| `app.<package>` | category |
|-----------------|----------|
| `services` | `domain` |
| `infrastructure` | `infra` |
| `middleware` | `http` |
| `exception_handlers` | `http` |
| `repositories` | `ops` |
| `main` | `ops` |

**Intentional mismatches** (tag name ≠ envelope category — package wins):

| Tag | Logger package | Envelope |
|-----|----------------|----------|
| `redis_unavailable_at_startup` | `app.main` | `ops` (not `infra`) |
| `cache_backend_error` | `app.services.task` | `domain` (not `infra`) |

## Catalog

Inventory matches current `logger.*` call sites. Section header = expected envelope category.

### `http` — `app.middleware.*`, `app.exception_handlers`

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `http_access` | `INFO` (`DEBUG` for `/health`, `/favicon.ico`) | After each request | `method`, `path`, `status`, `duration_ms` |
| `rate_limit_exceeded` | `WARNING` | Redis limiter blocked (429) | `policy`, `client`, `path` |
| `rate_limit_backend_error` | `ERROR` + tb | Limiter backend failed; fail-open | `policy`, `client`, `path` |
| `app_error` | `WARNING` if 4xx else `ERROR` | Handled `AppError` | `status`, `detail`, `path`, `actor_id` |
| `unhandled_error` | `ERROR` + tb | Bare `Exception` (500 path) | `path`, `actor_id` |

Login/refresh failures surface as `app_error`, not service tags.

### `infra` — `app.infrastructure.*`

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `email_sent` | `INFO` | Mail accepted | `email`, `subject` |
| `email_send_failed` | `ERROR` + tb | Send raised; caller still succeeds | `email`, `subject` |
| `email_skipped` | `INFO` | `EMAIL_ENABLED=false` | `email`, `reason` (`email_disabled`), `subject` |
| `task_export_sent` | `INFO` | Export finished (CSV + mailer) | `workspace_id`, `email`, `actor_id`, `subject` |
| `task_export_failed` | `ERROR` + tb | Export failed after 202 | `workspace_id`, `email`, `actor_id` |

### `ops` — `app.main`, `app.repositories.*`

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `redis_unavailable_at_startup` | `ERROR` + tb | Redis init failed; app continues | — |
| `after_commit_failed` | `ERROR` + tb | `after_commit` callback raised after commit | — |

### `domain` — `app.services.*`

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `user_registered` | `INFO` | User created | `user_id`, `email` |
| `user_login_succeeded` | `INFO` | Login issued tokens | `user_id` |
| `user_logout` | `INFO` | One session revoked | `user_id`, `session_id` |
| `user_logout_all` | `INFO` | All sessions revoked | `user_id`, `session_id` |
| `workspace_created` | `INFO` | Workspace created | `workspace_id`, `owner_id` |
| `workspace_member_added` | `INFO` | Member row created | `workspace_id`, `member_id`, `role`, `actor_id` |
| `task_created` | `INFO` | Task created | `workspace_id`, `task_id`, `actor_id` |
| `task_updated` | `INFO` | Task updated | `workspace_id`, `task_id`, `actor_id` |
| `task_deleted` | `INFO` | Task deleted | `workspace_id`, `task_id`, `actor_id` |
| `cache_backend_error` | `ERROR` + tb | Task-summary Redis get/set/delete failed; fail-open | `op`, `key` (+ `workspace_id` on delete) |

### Not logged

- Successful token refresh
- `GET` list/detail reads (including summary cache hit/miss)
- Failed login / invalid refresh (covered by `app_error`)
