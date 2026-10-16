# Taskman docs

| File | Purpose |
|------|---------|
| [caching.md](caching.md) | Task summary Redis cache (TTL, keys, fail-open, invalidation) |
| [commit-messages.md](commit-messages.md) | How we write git commits |
| [email.md](email.md) | SMTP + Jinja HTML (welcome email, task CSV export) |
| [pr-guide.md](pr-guide.md) | How we write pull request descriptions |
| [log-events.md](log-events.md) | Log event tags, text/JSON shapes (`http_access`, domain events, …) |
| [project-requirements.md](project-requirements.md) | Capstone project spec (target system) |
| [rate-limiting.md](rate-limiting.md) | Redis rate limiting (including fail-open) |
| [writing-readme.md](writing-readme.md) | Standards for the root README |

## App package layout (high level)

| Path | Role |
|------|------|
| `app/core/` | Shared primitives (config, security, time, request context) |
| `app/observability/` | Logging setup |
| `app/exceptions/` | Domain error types + FastAPI JSON error handlers |
| `app/middleware/` | ASGI middleware (`AccessLogMiddleware`, request id) |
| `app/dependencies/` | FastAPI DI (session/UoW, services, rate limits, RBAC) |
| `app/infrastructure/database/` | Engine / session factory |
| `app/infrastructure/email/` | Mail orchestration + providers + templates |
| `app/infrastructure/redis/` | Redis client, cache helpers, rate-limit algorithms, Lua scripts |
| `app/dto/api/` | HTTP request/response DTOs (public contract) |
| `app/dto/repository/` | Persistence DTOs (`*Record` / `*CreateData` / `*UpdateData`) |
| `app/repositories/` | Persistence repos + `UnitOfWork`; shared `create` / `get` on `BaseRepository` |
| `app/services/` | Application services (public: `dto.api`; persistence: `dto.repository`) |
| `app/api/`, `app/models/` | Routes (`dto.api` only), ORM models |
