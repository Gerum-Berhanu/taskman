# Email OTP registration

Registration is a **two-step ticket flow**. `POST /auth/register` no longer creates a user; it mints a short-lived Redis ticket, emails a one-time code, and returns **202** with `registration_id`. `POST /auth/register/verify` checks the OTP, creates the user, and returns **201**.

## Breaking change

| Before | After |
|--------|--------|
| `POST /auth/register` → **201** + user | `POST /auth/register` → **202** + `registration_id` |
| User row on register | User row only after successful verify |

Clients must call `/auth/register/verify` with `{ "registration_id", "otp" }` before login.

## HTTP contract

### Start — `POST /auth/register`

Body: `{ "email", "password" }` (same as before).

| Status | When |
|--------|------|
| **202** | Ticket created; body `RegisterPendingResponse` (`registration_id`, message) |
| **409** | Email already registered |
| **503** | Redis unavailable (fail-closed) |
| **429** | `auth.register` rate limit |

No `users` row yet. OTP mail is scheduled on `BackgroundTasks` after the ticket is written.

### Verify — `POST /auth/register/verify`

Body: `{ "registration_id": "<uuid>", "otp": "<digits>" }` (`otp` length = `REGISTRATION_OTP_LENGTH`).

| Status | When |
|--------|------|
| **201** | User created; body `UserCreateResponse` |
| **400** | Unknown/expired ticket, bad OTP, or attempts exhausted |
| **409** | Email taken on create race (ticket cleared) |
| **503** | Redis unavailable (fail-closed) |
| **429** | `auth.register.verify` rate limit |

Bad OTP increments `attempts`. When `attempts >= REGISTRATION_OTP_MAX_ATTEMPTS` on a later try, the ticket is deleted and the client must start registration again.

## Redis ticket

| Item | Value |
|------|--------|
| Key | `register:pending:{registration_id}` |
| Type | Redis hash |
| Fields | `email`, `hashed_password`, `otp_hash`, `attempts` |
| TTL | `REGISTRATION_OTP_TTL_SECONDS` (default 600) |

Passwords use the normal argon hash; OTPs are SHA-256 digests (same idea as refresh-token hashing). Plain OTP is only in the email.

## Env knobs

| Variable | Purpose | Default |
|----------|---------|---------|
| `REGISTRATION_OTP_TTL_SECONDS` | Ticket TTL | `600` |
| `REGISTRATION_OTP_LENGTH` | Digit count | `6` |
| `REGISTRATION_OTP_MAX_ATTEMPTS` | Wrong-OTP budget before clear | `5` |

Also needs Redis (`REDIS_URL`) and email settings from [email.md](email.md).

## Local Mailpit walkthrough

1. Start Mailpit and Redis; set SMTP as in [email.md](email.md#local-mailpit) (`EMAIL_ENABLED=true`, empty Resend key).
2. `POST /auth/register` with a new email → **202** + `registration_id`.
3. Open http://localhost:8025 — subject like `Your Taskman verification code`; copy the digits.
4. `POST /auth/register/verify` with that `registration_id` and OTP → **201**.
5. `POST /auth/login` with the same email/password → **200**.
6. Wrong OTP → **400** (`Invalid or expired registration code`); after the attempt cap, next verify → **400** (`Registration attempts exceeded`).

## Layout

| Path | Role |
|------|------|
| `app/api/auth.py` | `/register`, `/register/verify` |
| `app/services/user.py` | `start_registration`, `complete_registration` |
| `app/infrastructure/redis/registration/pending.py` | Hash create/get/clear/`incr_attempt` |
| `app/infrastructure/email/mails.py` | `send_registration_otp_email` |
| `app/infrastructure/email/templates/registration_otp.html` | OTP mail body |
| `app/core/security.py` | Generate / hash / verify OTP |
| `app/dependencies/rate_limit.py` | `auth.register`, `auth.register.verify` |

See also: [email.md](email.md), [rate-limiting.md](rate-limiting.md), [caching.md](caching.md) (summary cache is fail-**open**; this path is fail-**closed**).
