"""Smoke tests for POST /transcribe (no live OpenAI calls)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_transcribe_requires_openai_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    client = TestClient(app)
    files = {"file": ("x.webm", io.BytesIO(b"\x00" * 512), "audio/webm")}
    data = {"response_language": "hi"}
    res = client.post("/transcribe", files=files, data=data)
    assert res.status_code == 503
    body = res.json()
    assert body["detail"]["error_code"] == "transcribe_openai_unconfigured"
