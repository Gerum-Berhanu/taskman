# Email (SMTP + Jinja HTML)

Taskman sends HTML emails over SMTP. Bodies are Jinja2 templates under `app/infrastructure/email/templates/`, with shared layout and CSS in `base.html`.

## Welcome email

After a successful `POST /auth/register` commit, Taskman sends a welcome email in a FastAPI `BackgroundTasks` job.

### Flow

1. `UserService.register` creates the user and queues work with `UnitOfWork.after_commit`.
2. One callback logs `user_registered`.
3. Another schedules `bg_tasks.add_task(...)` to send the welcome email.
4. Session / UoW use `scope="function"`, so commit (and those `after_commit` callbacks) run after the path function returns and **before** the response is sent. That way `add_task` lands on `BackgroundTasks` in time.
5. After the 201 is sent, Starlette runs the background task → `send_welcome_email` → `send_mail`.

`send_mail` is the transport control point: if `EMAIL_ENABLED=false` it logs `email_skipped` and returns; on SMTP success/failure it logs `email_sent` / `email_send_failed` and never raises (registration stays 201).

## Task export email

A workspace **viewer** (or higher) calls `POST /workspaces/{workspace_id}/tasks/export`. The API responds immediately with **202 Accepted** and **no response body**. Heavy work runs afterward in a FastAPI `BackgroundTasks` job.

### Flow

1. `TaskService.export` schedules `run_tasks_export` on `BackgroundTasks` with the requester’s email and `actor_id` from request context.
2. The HTTP response is sent (202) before the background job runs.
3. `run_tasks_export` opens its **own** async session + `UnitOfWork` (never the request-scoped UoW), loads all tasks in the workspace, builds CSV via `tasks_to_csv`, then calls `send_tasks_export_email` inside `asyncio.to_thread` so SMTP stays off the event loop.
4. On success the worker logs `task_export_sent`. Any load/CSV/worker failure logs `task_export_failed` with traceback; the client already got 202 (fail-soft).

Unlike registration, export does not use `after_commit` — the request path does not persist export state.

### Message shape

| Item | Value |
|------|--------|
| Subject | `Taskman export [{workspace_id}]` |
| Body | HTML from `tasks_export.html` (extends `base.html`) |
| Attachment | `tasks-{workspace_id}.csv` (`text/csv`) |
| CSV columns | `id`, `title`, `description`, `status`, `due_date`, `assigned_user_id`, `created_at`, `updated_at` (ISO datetimes, empty cells for nulls) |

Transport behavior (`EMAIL_ENABLED`, `email_sent`, `email_send_failed`, `email_skipped`) is unchanged and lives in `send_mail`.

## Layout

| Path | Role |
|------|------|
| `app/core/config.py` | `EMAIL_*` / `SMTP_*` settings |
| `app/infrastructure/email/smtp.py` | Sync `smtplib` send helpers + Jinja render (`email_enabled` + transport logs) |
| `app/infrastructure/email/templates/base.html` | Shared HTML shell and internal CSS |
| `app/infrastructure/email/templates/welcome.html` | Welcome body (`{% extends "base.html" %}`) |
| `app/infrastructure/email/templates/tasks_export.html` | Export body (`{% extends "base.html" %}`) |
| `app/infrastructure/export/tasks_csv.py` | Pure CSV builder (`tasks_to_csv`) |
| `app/infrastructure/export/task_export.py` | Background worker (`run_tasks_export`) |
| `app/services/user.py` | `after_commit` + background welcome send |
| `app/services/task.py` | Schedules export background job |
| `app/api/v1/tasks.py` | `POST …/tasks/export` → 202 |

## Env

| Variable | Purpose |
|----------|---------|
| `EMAIL_ENABLED` | Master switch for all SMTP sends (`false` in test). Enforced in `send_mail`. |
| `SMTP_HOST` | SMTP host (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (e.g. `587` for STARTTLS) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password / Gmail App Password |
| `EMAIL_FROM` | From address on outgoing messages |

Put real secrets only in local `env/.env.*` (gitignored). `env-example/` keeps placeholders.

## Tests

Pytest keeps email off in the test overlay. Dedicated tests mock SMTP / the welcome helper so CI never hits a real mailbox.

See also: [log-events.md](log-events.md) (`email_sent`, `email_send_failed`, `email_skipped`).
