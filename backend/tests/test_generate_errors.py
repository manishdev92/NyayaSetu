"""Structured errors on `/generate` and `/generate-stream` (P5-01)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.usage_limit import UsageSnapshot


def test_generate_429_includes_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    snap = UsageSnapshot(used=100, limit=100, remaining=0, reset_at_utc="2099-01-01T00:00:00Z")
    monkeypatch.setattr(
        "app.api.v1.generate.consume_request",
        lambda **kw: (False, snap),
    )
    monkeypatch.setattr("app.api.v1.generate.http_rate_limit_headers", lambda s: {})
    r = TestClient(app).post("/generate", json={"user_input": "hello there please"})
    assert r.status_code == 429
    d = r.json()["detail"]
    assert d["error_code"] == "generate_rate_limited"
    assert "message" in d


def test_generate_503_openai_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    r = TestClient(app).post("/generate", json={"user_input": "I need help with unpaid wages"})
    assert r.status_code == 503
    d = r.json()["detail"]
    assert d["error_code"] == "generate_openai_unconfigured"


def test_generate_stream_sse_error_includes_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    r = TestClient(app).post("/generate-stream", json={"user_input": "unpaid rent dispute text"})
    assert r.status_code == 200
    assert "generate_openai_unconfigured" in r.text
