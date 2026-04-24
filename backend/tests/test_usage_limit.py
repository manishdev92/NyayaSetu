"""Daily limiter + usage snapshot."""

from __future__ import annotations

import uuid

from app.services import usage_limit as ul


def test_http_rate_limit_headers() -> None:
    snap = ul._snap_from_count(5, 20)
    h = ul.http_rate_limit_headers(snap)
    assert h["X-RateLimit-Limit"] == "20"
    assert h["X-RateLimit-Remaining"] == "15"
    assert str(h["X-RateLimit-Reset"]).isdigit()


def test_consume_request_increments_for_unique_user() -> None:
    uid = f"usage-test-{uuid.uuid4()}"
    ok1, s1 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok1 is True
    ok2, s2 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok2 is True
    assert s2.used == s1.used + 1
    assert s2.limit == s1.limit
