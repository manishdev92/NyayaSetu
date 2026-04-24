# Redis daily rate limits (multi-instance)

The default **`DailyLimiter`** keeps per-user and per-IP counters **in process memory**, so each API replica has its own counts. Set **`REDIS_URL`** (e.g. `redis://localhost:6379/0`) so `consume_request` in `app/services/usage_limit.py` uses **one shared counter per UTC day** across all workers.

## Behaviour

- Keys: `nyaya:daily:{YYYY-MM-DD}:user:{clerk_user_id}` and `nyaya:daily:{YYYY-MM-DD}:anon:{ip}`.
- **INCR** per allowed request; if count exceeds the cap, **DECR** and reject (same semantics as in-memory).
- TTL on each key is **172800** seconds (~48h) so keys expire after the UTC day boundary without a cron job.

## Environment

| Variable | Required | Notes |
|----------|----------|--------|
| `REDIS_URL` | For Redis mode | Non-empty enables Redis; empty keeps in-memory limiter. |

`GET /config` exposes **`rate_limit_backend`**: `"memory"` or `"redis"`.

## Dependency

`redis>=5` is listed in `backend/requirements.txt`. Use TLS URLs (`rediss://`) when your provider requires it.
