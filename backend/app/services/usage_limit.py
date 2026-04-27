from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.services.pro_entitlements_store import clerk_has_pro_entitlement
from app.services.user_trial_store import ensure_first_seen_utc, is_in_trial, reset_trial_store_for_tests


@dataclass(frozen=True)
class UsageSnapshot:
    """Point-in-time daily counter (UTC calendar day, resets at next 00:00:00 UTC)."""

    used: int
    limit: int
    remaining: int
    reset_at_utc: str  # ISO-8601, next UTC midnight


def _next_utc_midnight_iso() -> str:
    now = datetime.now(timezone.utc)
    nxt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return nxt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _snap_from_count(used: int, limit: int) -> UsageSnapshot:
    return UsageSnapshot(
        used=used,
        limit=limit,
        remaining=max(0, limit - used),
        reset_at_utc=_next_utc_midnight_iso(),
    )


def http_rate_limit_headers(snap: UsageSnapshot) -> dict[str, str]:
    """X-RateLimit-* compatible with many API clients; Reset = epoch seconds (UTC)."""
    try:
        reset_dt = datetime.fromisoformat(snap.reset_at_utc.replace("Z", "+00:00"))
        reset_epoch = int(reset_dt.timestamp())
    except (OSError, ValueError, TypeError):
        reset_epoch = int(datetime.now(timezone.utc).timestamp() + 86400)
    return {
        "X-RateLimit-Limit": str(snap.limit),
        "X-RateLimit-Remaining": str(snap.remaining),
        "X-RateLimit-Reset": str(reset_epoch),
    }


class DailyLimiter:
    """In-memory per-key counter; resets when UTC date changes. Per-call cap."""

    def __init__(self) -> None:
        self._day: str | None = None
        self._counts: dict[str, int] = {}

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _ensure_day(self) -> None:
        d = self._today()
        if self._day != d:
            self._counts.clear()
            self._day = d

    def count_for(self, key: str) -> int:
        self._ensure_day()
        return self._counts.get(key, 0)

    def allow(self, key: str, cap: int) -> bool:
        self._ensure_day()
        if self._counts.get(key, 0) >= cap:
            return False
        self._counts[key] = self._counts.get(key, 0) + 1
        return True

    def clear(self) -> None:
        self._counts.clear()
        self._day = None


_authenticated = DailyLimiter()
_anonymous = DailyLimiter()

# Tests may assign a FakeRedis before calling consume_request when redis_url is set.
_redis_client_override: Any | None = None


def set_redis_client_override_for_tests(client: Any | None) -> None:
    """Inject a FakeRedis (or None) for unit tests; production ignores this."""
    global _redis_client_override
    _redis_client_override = client


def _use_redis() -> bool:
    return bool((getattr(settings, "redis_url", None) or "").strip())


def _redis_conn() -> Any:
    global _redis_client_override
    if _redis_client_override is not None:
        return _redis_client_override
    import redis

    return redis.Redis.from_url(settings.redis_url.strip(), decode_responses=True)


def _redis_day_key(logical_key: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"nyaya:daily:{day}:{logical_key}"


def reset_usage_backends_for_tests() -> None:
    """Clear in-memory counters, optional Redis keys, test Redis override, and trial SQLite handle."""
    global _redis_client_override
    reset_trial_store_for_tests()
    _authenticated.clear()
    _anonymous.clear()
    if _redis_client_override is not None:
        try:
            for k in _redis_client_override.scan_iter(match="nyaya:daily:*"):
                _redis_client_override.delete(k)
        except Exception:
            pass
        _redis_client_override = None
    elif _use_redis():
        try:
            r = _redis_conn()
            for k in r.scan_iter(match="nyaya:daily:*"):
                r.delete(k)
        except Exception:
            pass


def effective_daily_limit_for_user(user_id: str | None) -> int:
    """Per-UTC-day cap for generate/ingest: anonymous, Pro, trial, or post-trial base."""
    return _daily_cap_for_user(user_id)


def _daily_cap_for_user(user_id: str | None) -> int:
    if not user_id:
        return int(settings.daily_limit_anonymous)
    if clerk_has_pro_entitlement(user_id):
        return int(settings.daily_limit_pro)
    ensure_first_seen_utc(user_id)
    if is_in_trial(user_id):
        return int(settings.daily_limit_trial)
    return int(settings.daily_limit_authenticated)


def _consume_via_redis(*, user_id: str | None, client_ip: str | None) -> tuple[bool, UsageSnapshot]:
    r = _redis_conn()
    if user_id:
        cap = _daily_cap_for_user(user_id)
        key = _redis_day_key(f"user:{user_id}")
    else:
        cap = int(settings.daily_limit_anonymous)
        key = _redis_day_key(f"anon:{client_ip or 'unknown'}")
    val = int(r.incr(key))
    if val == 1:
        r.expire(key, 172800)
    if val > cap:
        r.decr(key)
        return False, _snap_from_count(val - 1, cap)
    return True, _snap_from_count(val, cap)


def consume_request(*, user_id: str | None, client_ip: str | None) -> tuple[bool, UsageSnapshot]:
    """
    Enforce one daily count per request; on success, increment and return after state.
    On failure (over limit), return (False, snapshot at limit) without increment.
    """
    if _use_redis():
        return _consume_via_redis(user_id=user_id, client_ip=client_ip)

    if user_id:
        limiter = _authenticated
        key = f"user:{user_id}"
        cap = _daily_cap_for_user(user_id)
    else:
        limiter = _anonymous
        key = f"anon:{client_ip or 'unknown'}"
        cap = int(settings.daily_limit_anonymous)
    c = limiter.count_for(key)
    if c >= cap:
        return False, _snap_from_count(c, cap)
    ok = limiter.allow(key, cap)
    c2 = limiter.count_for(key)
    if not ok:
        return False, _snap_from_count(c2, cap)
    return True, _snap_from_count(c2, cap)


def check_generation_allowed(*, user_id: str | None, client_ip: str | None) -> bool:
    """Backward-compatible boolean gate (increments when allowed)."""
    ok, _ = consume_request(user_id=user_id, client_ip=client_ip)
    return ok
