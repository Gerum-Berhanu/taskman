# Task summary caching

`GET /workspaces/{workspace_id}/tasks/summary` caches aggregated task status counts in Redis. TTL defaults to **5 minutes** (`TASK_SUMMARY_CACHE_TTL_SECONDS` / `settings.task_summary_cache_ttl_seconds`).

## Layout

| Path | Role |
|------|------|
| `app/infrastructure/redis/cache.py` | JSON `get` / `set` / `delete` helpers + `task_summary_key` |
| `app/services/task.py` | Cache read/write on `summary`; invalidate on create/update/delete |
| `app/infrastructure/redis/client.py` | Shared async Redis client (also used by rate limiting) |

## Key shape

```text
cache:ws:{workspace_id}:tasks:summary
```

Value is a JSON object matching the summary response (`workspace_id` stored as a string for `json.dumps`).

## Flow

1. **GET summary** — try cache; on hit return the dict (FastAPI `response_model=TaskSummaryRead` coerces types).
2. **Miss** — SQL `GROUP BY status` aggregate, return dict, then `SET` with TTL.
3. **Mutate** (create / update / delete task) — `DELETE` the workspace summary key (fail-soft). Done in the async service (not `after_commit`; that hook is sync-only today).

## Fail-open on backend errors

Caching is **not** on the critical path:

- Redis down at startup → app still boots (`redis_unavailable_at_startup`).
- Get/set/delete failures at request time → log `cache_backend_error` and continue (DB path for reads; mutation still succeeds).

See also: [log-events.md](log-events.md) (`cache_backend_error`), [rate-limiting.md](rate-limiting.md) (same Redis client, fail-open pattern).
