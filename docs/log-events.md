# Log event tags

Stable event tags for app logs. Tags are registered in code as category enums under `LogEvent` (`HttpLogEvent`, `InfraLogEvent`, `OpsLogEvent`, `DomainLogEvent` in `app/observability/events.py`); this doc describes fields and when they fire. Envelope (`timestamp`, `level`, `category`, `logger`, `request_id`) comes from `app/observability/`. Emit catalog events only via `log_event` in `app/observability/log_event.py`. Domain write events emit only via `UnitOfWork.after_commit` after a successful commit.

## Format

App events share one call shape: `log_event(logger, level, event, *, exc_info=False, **fields)`. Field keys come from the catalog below — no prose, no `category=` in the payload. On failure inside an `except`, pass `exc_info=True`.

**Text** (`LOG_JSON=false`): envelope then `event key=value …`. Values for `detail` / `subject` are `repr`'d (may contain spaces). Tag-only events are just the event string.

```text
2026-01-01 12:00:00Z | WARNING | http | app.exception_handlers | req-1 | validation_error actor_id=- detail='Field required at email'
```

**JSON** (`LOG_JSON=true`): same envelope keys as top-level fields, plus `event` (catalog tag) and `fields` (attr object; `{}` if tag-only). No top-level rendered `message` for app events — do not nest attrs under a `message` object. Third-party / non-catalog logs (no `event` on the record) keep a `message` string. When a traceback is attached, JSON also has `exception`.

```json
{
  "timestamp": "2026-01-01 12:00:00Z",
  "level": "WARNING",
  "category": "http",
  "logger": "app.exception_handlers",
  "request_id": "req-1",
  "event": "validation_error",
  "fields": {"actor_id": "-", "detail": "Field required at email"}
}
```

- Domain success tags: past tense (`task_created`). HTTP/infra/errors: noun or `*_error` / `*_failed`.
- Ids as strings; missing actor/session/user-like ids → `-`.
- **HTTP split:** `http_access` owns request outcome (`method`, `path`, `status`, `duration_ms`). Handler / rate-limit tags carry only extra context (`actor_id`+`detail`, or `ip`+`policy`). Join on envelope `request_id` when you need both.

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
| `cache_backend_error` | `app.services.task` | `domain` (not `infra`) |

## Catalog

Inventory matches current `log_event` call sites. Section header = expected envelope category.

### `http` — `app.middleware.*`, `app.exception_handlers`

Access log: `AccessLogMiddleware` (`app/middleware/access_log.py`).

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `http_access` | `INFO` (`DEBUG` for `/health`, `/favicon.ico`) | After each request | `method`, `path`, `status`, `duration_ms` |
| `rate_limit_exceeded` | `WARNING` | Redis limiter blocked (429) | `ip`, `policy` |
| `rate_limit_backend_error` | `ERROR` + tb | Limiter backend failed; fail-open | `ip`, `policy` |
| `app_error` | `WARNING` if 4xx else `ERROR` | Handled `AppError` | `actor_id`, `detail` |
| `validation_error` | `WARNING` | FastAPI/Pydantic `RequestValidationError` (422); client gets first error only as `"<msg> at <field>"` | `actor_id`, `detail` |
| `unhandled_error` | `ERROR` + tb | Bare `Exception` (500 path) | `actor_id`, `detail` |

Login/refresh failures surface as `app_error`, not service tags.

### `infra` — `app.infrastructure.*`

| Tag | Level | When | Fields |
|-----|-------|------|--------|
| `redis_unavailable_at_startup` | `ERROR` + tb | Redis init failed at startup; app continues (`init_redis_fail_open`) | — |
| `email_sent` | `INFO` | Mail accepted | `email`, `subject` |
| `email_send_failed` | `ERROR` + tb | Send raised; caller still succeeds | `email`, `subject` |
| `email_skipped` | `INFO` | `EMAIL_ENABLED=false` | `email`, `reason` (`email_disabled`), `subject` |
| `task_export_sent` | `INFO` | Export finished (CSV + mailer) | `workspace_id`, `email`, `actor_id`, `subject` |
| `task_export_failed` | `ERROR` + tb | Export failed after 202 | `workspace_id`, `email`, `actor_id` |

### `ops` — `app.repositories.*`

| Tag | Level | When | Fields |
|-----|-------|------|--------|
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
