"""Redis-backed daily limiter (optional `REDIS_URL`)."""

from __future__ import annotations

import uuid

import fakeredis
import pytest

from app.config import settings
from app.services import usage_limit as ul


@pytest.fixture(autouse=True)
def _cleanup_redis_test(monkeypatch: pytest.MonkeyPatch) -> None:
    ul.set_redis_client_override_for_tests(None)
    monkeypatch.setattr(settings, "redis_url", "", raising=False)
    ul.reset_usage_backends_for_tests()
    yield
    ul.set_redis_client_override_for_tests(None)
    monkeypatch.setattr(settings, "redis_url", "", raising=False)
    ul.reset_usage_backends_for_tests()


def test_consume_via_redis_respects_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    ul.set_redis_client_override_for_tests(fake)
    monkeypatch.setattr(settings, "redis_url", "redis://localhost/0", raising=False)
    monkeypatch.setattr(settings, "daily_limit_authenticated", 2, raising=False)

    uid = f"redis-cap-{uuid.uuid4().hex[:8]}"
    ok1, s1 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok1 and s1.used == 1
    ok2, s2 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok2 and s2.used == 2
    ok3, s3 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok3 is False
    assert s3.used == 2
    assert s3.remaining == 0
