# Taskman docs

| File | Purpose |
|------|---------|
| [commit-messages.md](commit-messages.md) | How we write git commits |
| [email.md](email.md) | Welcome email via SMTP (after_commit + BackgroundTasks) |
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
| `app/infrastructure/redis/` | Redis client, rate-limit algorithms, Lua scripts |
| `app/repositories/` | Persistence repos + `UnitOfWork` |
| `app/services/`, `app/api/`, `app/models/`, `app/schemas/` | Domain services, routes, models, schemas |
