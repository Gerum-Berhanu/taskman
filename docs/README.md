# Taskman docs

| File | Purpose |
|------|---------|
| [auth-cookies.md](auth-cookies.md) | Access Bearer + HttpOnly refresh/device cookies; session purge via Beat |
| [caching.md](caching.md) | Task summary Redis cache (TTL, keys, fail-open, invalidation) |
| [commit-messages.md](commit-messages.md) | How we write git commits |
| [services.md](services.md) | Public vs private service methods (API DTOs vs `_` helpers) |
| [email.md](email.md) | SMTP + Jinja HTML; Celery worker + Beat (mail, export, session purge) |
| [registration-otp.md](registration-otp.md) | Email OTP registration tickets (202 start / 201 verify) |
| [pr-guide.md](pr-guide.md) | How we write pull request descriptions |
| [log-events.md](log-events.md) | Log event tags, `log_event` / `after_commit`, scope modules, sinks |
| [project-requirements.md](project-requirements.md) | Capstone project spec (target system) |
| [rate-limiting.md](rate-limiting.md) | Redis rate limiting (fail-closed **503**; **429** when over budget) |
| [writing-readme.md](writing-readme.md) | Standards for the root README |

## App package layout (high level)

| Path | Role |
|------|------|
| `app/core/` | Shared primitives (config, security, time, request context) |
| `app/observability/` | Logging setup, `log_event`, event tag modules (`events/`) |
| `app/exceptions/` | Domain error types + FastAPI JSON error handlers |
| `app/middleware/` | ASGI middleware (`AccessLogMiddleware`, request id) |
| `app/dependencies/` | FastAPI DI (session/UoW, services, rate limits, RBAC) |
| `app/infrastructure/database/` | Engine / session factory |
| `app/infrastructure/email/` | Mail orchestration + providers + templates |
| `app/infrastructure/redis/` | Redis client, cache helpers, rate-limit algorithms, Lua scripts |
| `app/jobs/` | Out-of-request runners (`export/`, `purge/`; purge also on Celery Beat) |
| `app/dto/api/` | HTTP request/response DTOs (public contract) |
| `app/dto/repository/` | Persistence DTOs (`*Record` / `*CreateData` / `*UpdateData`) |
| `app/repositories/` | Persistence repos + `UnitOfWork`; shared `create` / `get` on `BaseRepository` |
| `app/services/` | Application services (see [services.md](services.md)) |
| `app/api/`, `app/models/` | Routes (`dto.api` only), ORM models |
