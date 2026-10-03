# Welcome email (SMTP)

After a successful `POST /auth/register` commit, Taskman sends a plain-text welcome email in a FastAPI `BackgroundTasks` job.

## Flow

1. `UserService.register` creates the user and queues work with `UnitOfWork.after_commit`.
2. One callback logs `user_registered`.
3. Another schedules `bg_tasks.add_task(...)` to send the welcome email.
4. Session / UoW use `scope="function"`, so commit (and those `after_commit` callbacks) run after the path function returns and **before** the response is sent. That way `add_task` lands on `BackgroundTasks` in time.
5. After the 201 is sent, Starlette runs the background task: SMTP send, then `email_sent` or `email_send_failed`.

Send failures are fail-soft: the account remains created; only logs record the error.

## Layout

| Path | Role |
|------|------|
| `app/core/config.py` | `EMAIL_*` / `SMTP_*` settings |
| `app/infrastructure/email/smtp.py` | Sync `smtplib` send helpers |
| `app/infrastructure/email/templates/welcome.txt` | Welcome body copy |
| `app/services/user.py` | `after_commit` + background welcome send |

## Env

| Variable | Purpose |
|----------|---------|
| `EMAIL_ENABLED` | Feature flag in settings (`false` in test). Mailer path is still driven by register wiring today. |
| `SMTP_HOST` | SMTP host (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (e.g. `587` for STARTTLS) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password / Gmail App Password |
| `EMAIL_FROM` | From address on outgoing messages |

Put real secrets only in local `env/.env.*` (gitignored). `env-example/` keeps placeholders.

## Tests

Pytest keeps email off in the test overlay. Dedicated tests mock SMTP / the welcome helper so CI never hits a real mailbox.

See also: [log-events.md](log-events.md) (`email_sent`, `email_send_failed`).
