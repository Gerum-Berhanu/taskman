# Rate limiting

Per-route Redis limits apply when `RATE_LIMIT_ENABLED=true` (default in non-test overlays; pytest keeps it off unless a test opts in). Routes attach a named dependency alias from `app/dependencies/rate_limit.py` (for example `dependencies=[DomainWriteLimit]`). Before the handler runs, `RequireIPLimit` or `RequireUserLimit` resolves identity, hits Redis through `HITTERS`, and either allows the request or raises `RateLimitExceededError` (**429**, detail `Too many requests`, `Retry-After` from the algorithm). Backend failures log `rate_limit_backend_error` and **fail open**.

Scopes are shared **budget classes**, not one counter per URL. Same scope name => same Redis key family for that identity.

## Layout

| Path | Role |
|------|------|
| `app/dependencies/rate_limit.py` | `SCOPES` presets, `RequireIPLimit` / `RequireUserLimit`, module aliases |
| `app/infrastructure/redis/rate_limit/` | `algorithm.py` (strategies + `HITTERS`); `__init__.py` re-exports only |
| `app/infrastructure/redis/client.py` | Async Redis client + registered Lua scripts |
| `app/infrastructure/redis/lua_loader.py` | Declared script names and packaged source loading |
| `app/infrastructure/redis/scripts/*.lua` | One script per algorithm (see catalog below) |

## Scope model

| Scope | Identity | Intent | Default budget | Default algorithm |
|-------|----------|--------|----------------|-------------------|
| `auth.register` | IP | Account spam | 3 / 1m | `leaky_bucket` |
| `auth.login` | IP | Credential stuffing | 5 / 1m | `leaky_bucket` |
| `auth.refresh` | IP | Refresh storms; keep separate from login | 30 / 1m | `token_bucket` |
| `auth.logout` | IP | Logout + `DELETE /auth/sessions` (all) share one budget | 10 / 1m | `sliding_window_counter` |
| `domain.read` | user id | Light reads (list/get/summary/`/me`) | 100 / 1m | `sliding_window_counter` |
| `domain.write` | user id | CUD (create/update/delete, add member, ...) | 30 / 1m | `sliding_window_counter` |
| `domain.export` | user id | Export job outlier | 5 / 1m | `leaky_bucket` |

Tune budgets and algorithms in the `SCOPES` dict in `app/dependencies/rate_limit.py`. Each `ScopeSpec` takes `window: timedelta` (default `timedelta(minutes=1)`). `RateLimitAlgorithm.hit` converts that to whole milliseconds for Lua. Aliases (`AuthLoginLimit`, `DomainWriteLimit`, ...) are built from that registry.

### Call sites

```python
dependencies=[AuthLoginLimit]
dependencies=[AuthRefreshLimit]
dependencies=[DomainReadLimit]
dependencies=[DomainWriteLimit, Depends(RequireRole(EDITOR))]
dependencies=[DomainExportLimit, Depends(RequireRole(VIEWER))]
```

Auth: register / login / refresh / logout / delete-all-sessions use the auth aliases; `GET /auth/me` and `GET /auth/sessions` use `DomainReadLimit`; `DELETE /auth/sessions/{id}` uses `DomainWriteLimit`. Domain routers attach read / write / export accordingly.

## Redis key and 429 contract

```text
Redis key:  rl:{algorithm}:{scope}:{identity}
429 body:   {"detail": "Too many requests"}
429 header: Retry-After: <seconds>
```

Example key: `rl:leaky_bucket:auth.login:203.0.113.10`.

Every Lua script returns `{allowed (0|1), retry_after_ms}`. On allow, `retry_after_ms` is `0`. On deny, it is milliseconds until a retry may succeed (gap remaining, next window, token refill, and so on). The dependency converts that to whole seconds for `Retry-After` (`max(1, ceil(ms / 1000))`).

## Algorithm catalog

| Name | Script | Role |
|------|--------|------|
| `sliding_window_counter` | `sliding_window_counter.lua` | Approximate counter (weighted previous + current cycle) |
| `sliding_window_log` | `sliding_window_log.lua` | Exact ZSET log |
| `fixed_window_counter` | `fixed_window_counter.lua` | Fixed cycle counter |
| `token_bucket` | `token_bucket.lua` | Burst + steady refill |
| `leaky_bucket` | `leaky_bucket.lua` | Strict min-gap (no burst); `limit`/`window` set the gap |

Dispatch is only via `HITTERS` (name -> `RateLimitAlgorithm` instance). The HTTP layer picks `SCOPES[scope].algorithm` and calls `.hit(...)` on the mapped strategy.

## Identity

| Class | Identity | Typical scopes |
|-------|----------|----------------|
| `RequireIPLimit` | `request.client.host` | `auth.*` |
| `RequireUserLimit` | authenticated user id (`CurrentUserDep`) | `domain.*` |

Unknown client address on the IP path raises `UnknownClientError` (400).

## Fail-open on backend errors

Rate limiting is **not** on the critical path for API availability:

- If Redis is down at startup, the app still boots (`redis_unavailable_at_startup`) and leaves the client uninitialized.
- If a limit check hits a backend failure at request time (`redis.exceptions.RedisError`, `TimeoutError`, or `KeyError` when scripts were never registered after a failed init), `_enforce_limit` logs `rate_limit_backend_error` (fields: `scope` + `ip` or `user_id`) and **allows the request**. Other exceptions are not swallowed.
- Real **429** responses only happen when Redis answered and the client is over the limit.

During a Redis outage, limits are effectively off until Redis is healthy again and the process has a working client (today that means a successful init, typically after restart).

Kill switch: `settings.rate_limit_enabled` / `RATE_LIMIT_ENABLED`.

See also: [log-events.md](log-events.md) (`rate_limit_exceeded`, `rate_limit_backend_error`, `redis_unavailable_at_startup`).
