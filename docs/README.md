# Taskman docs

| File | Purpose |
|------|---------|
| [caching.md](caching.md) | Task summary Redis cache (TTL, keys, fail-open, invalidation) |
| [commit-messages.md](commit-messages.md) | How we write git commits |
| [email.md](email.md) | SMTP + Jinja HTML (welcome email, task CSV export) |
| [pr-guide.md](pr-guide.md) | How we write pull request descriptions |
| [log-events.md](log-events.md) | Log event tags (`http_access`, `rate_limit_exceeded`, domain events, …) |
| [project-requirements.md](project-requirements.md) | Capstone project spec (target system) |
| [rate-limiting.md](rate-limiting.md) | Redis rate limiting (including fail-open) |
| [writing-readme.md](writing-readme.md) | Standards for the root README |

## App package layout (high level)

| Path | Role |
|------|------|
| `app/core/` | Shared primitives (config, exceptions, security, time, request context) |
| `app/observability/` | Logging setup |
| `app/http/` | Exception handlers and middleware |
| `app/infrastructure/database/` | Engine / session factory |
| `app/infrastructure/email/` | SMTP mailer + email templates |
| `app/infrastructure/redis/` | Redis client, cache helpers, rate-limit algorithms, Lua scripts |
| `app/repositories/` | Persistence repos + `UnitOfWork`; shared `create` / `get` on `BaseRepository` |
| `app/services/`, `app/api/`, `app/models/`, `app/schemas/` | Domain services, routes, models, schemas |
