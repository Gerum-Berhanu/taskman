# Rate limiting

Redis **sliding-window counter** limits apply when `RATE_LIMIT_ENABLED=true`. Blocked requests return **429** with `Retry-After` and log `rate_limit_exceeded`.

Redis keys are still `rl_sliding_window_counter:{policy}:{identity}` (for example `rl_sliding_window_counter:task_reads:testclient`).

## Policy registry

Named policies live in `app/core/rate_limit_policies.py`:

- `default`
- `auth`
- `task_reads`
- `task_writes`

Each policy is a frozen `RateLimitPolicy` with:

- `name`
- `limit`
- `window_seconds`
- `identity_mode` (currently `ip`, future-facing only)

Policy values come from `Settings` where applicable (default/auth fields remain the source of truth).

## Route-level and group-level policies

Use the reusable dependency from `app/http/dependencies/rate_limit.py`:

- `rate_limit("policy_name")` for route-level assignment
- the same dependency in `APIRouter(..., dependencies=[...])` for group-level assignment

Current usage:

- Auth POST endpoints use `auth`
- Task GET endpoints use `task_reads`
- Task create/update/delete endpoints use `task_writes`

## Middleware fallback model

`app/http/middleware/rate_limit.py` is still global fallback protection for routes without explicit policy dependencies:

- fallback selection keeps existing behavior (`POST /auth*` => `auth`, everything else => `default`)
- routes with explicit `rate_limit(...)` dependencies are skipped by middleware so one request consumes one bucket
- `/health` and `/favicon.ico` are excluded

## Fail-open on backend errors

Rate limiting remains fail-open:

- Redis startup failures keep the app booting (`redis_unavailable_at_startup`)
- request-time backend errors log `rate_limit_backend_error` and allow the request
- this fail-open behavior applies to both middleware fallback and explicit route/group dependencies

See also: [log-events.md](log-events.md).
