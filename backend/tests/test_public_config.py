from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_config_default_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    client = TestClient(app)
    r = client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert data.get("billing_mode") == "none"
    assert data.get("paywall_visible") is False
    assert data.get("rag_vector_store") == "local"
    assert data.get("max_upload_bytes") == int(settings.max_upload_bytes)
    assert isinstance(data.get("max_upload_bytes"), int)
    assert data.get("stripe_checkout_ready") is False
    assert data.get("stripe_portal_ready") is False
    assert data.get("stripe_webhook_ready") is False
    assert data.get("daily_limit_authenticated") == int(settings.daily_limit_authenticated)
    assert data.get("daily_limit_pro") == int(settings.daily_limit_pro)
    assert data.get("ingest_ocr_provider") == "none"
    assert data.get("ingest_ocr_ready") is False
    assert data.get("entitlements_store") == "sqlite"
    assert data.get("rate_limit_backend") == "memory"


def test_config_stub_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stub", raising=False)
    client = TestClient(app)
    r = client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert data.get("billing_mode") == "stub"
    assert data.get("paywall_visible") is True
    assert data.get("rag_vector_store") in ("local", "pinecone")
    assert data.get("max_upload_bytes") == int(settings.max_upload_bytes)
    assert data.get("stripe_checkout_ready") is False
