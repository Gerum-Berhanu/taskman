# Rate limiting

Redis **sliding-window counter** limits apply when `RATE_LIMIT_ENABLED=true` (default in non-test overlays). Auth `POST` routes use a tighter policy. Blocked requests return **429** with `Retry-After` and log `rate_limit_exceeded`.

Redis keys look like `rl_sliding_window_counter:{policy}:{identity}` (e.g. `…:default:testclient`).

## Layout

| Path | Role |
|------|------|
| `app/http/middleware/rate_limit.py` | HTTP policy selection and 429 / fail-open responses |
| `app/infrastructure/redis/rate_limit_algorithms.py` | Hit helpers (`hit_sliding_window_counter` is what middleware uses) |
| `app/infrastructure/redis/client.py` | Redis client + registered Lua scripts |
| `app/infrastructure/redis/lua.py` | Declared script names and packaged source loading |
| `app/infrastructure/redis/scripts/sliding_window_counter.lua` | Active approximate counter (fixed cycles + weighted previous bucket) |
| `app/infrastructure/redis/scripts/sliding_window_log.lua` | Alternate exact log/ZSET algorithm (kept for comparison; not used by middleware) |

## Fail-open on backend errors

Rate limiting is **not** on the critical path for API availability:

- If Redis is down at startup, the app still boots (`redis_unavailable_at_startup`) and leaves the client uninitialized.
- If a limit check fails at request time (Redis down, timeouts, uninitialized client, script errors), the middleware logs `rate_limit_backend_error` and **allows the request**.
- Real **429** responses only happen when Redis answered and the client is over the limit.

During a Redis outage, limits (including auth) are effectively off until Redis is healthy again and the process has a working client (today that means a successful init, typically after restart).

Pytest keeps limiting off globally; dedicated tests in `tests/test_rate_limit.py` turn it on via monkeypatch.

See also: [log-events.md](log-events.md) (`rate_limit_exceeded`, `rate_limit_backend_error`, `redis_unavailable_at_startup`).
