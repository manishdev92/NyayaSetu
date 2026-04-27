"""SQLite-backed free trial affects daily caps for signed-in non-Pro users."""

from __future__ import annotations

import uuid

import pytest

from app.config import settings
from app.services import usage_limit as ul
from app.services.user_trial_store import reset_trial_store_for_tests


@pytest.fixture(autouse=True)
def _trial_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    reset_trial_store_for_tests()
    monkeypatch.setattr(settings, "trial_period_days", 7, raising=False)
    monkeypatch.setattr(settings, "daily_limit_trial", 40, raising=False)
    monkeypatch.setattr(settings, "daily_limit_authenticated", 3, raising=False)
    p = tmp_path / f"trial_{uuid.uuid4().hex}.sqlite"
    monkeypatch.setattr(settings, "trial_db_path", str(p), raising=False)
    monkeypatch.setattr(settings, "redis_url", "", raising=False)
    ul.reset_usage_backends_for_tests()
    yield
    ul.reset_usage_backends_for_tests()
    reset_trial_store_for_tests()


def test_new_user_gets_trial_cap_until_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    uid = f"trial-u-{uuid.uuid4().hex}"
    ok, s = ul.consume_request(user_id=uid, client_ip=None)
    assert ok and s.limit == 40

    monkeypatch.setattr(settings, "trial_period_days", 0, raising=False)
    ok2, s2 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok2 and s2.limit == 3
