# Rate limiting

Redis sliding-window limits apply when `RATE_LIMIT_ENABLED=true` (default in non-test overlays). Auth `POST` routes use a tighter policy. Blocked requests return **429** with `Retry-After` and log `rate_limit_exceeded`.

Pytest keeps limiting off globally; dedicated tests in `tests/test_rate_limit.py` turn it on via monkeypatch.

See also: [`rate_limit_exceeded` in log-events.md](log-events.md).
