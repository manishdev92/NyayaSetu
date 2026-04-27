from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_config_default_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    monkeypatch.setattr(settings, "rag_vector_store", "local", raising=False)
    monkeypatch.setattr(settings, "case_law_mode", "off", raising=False)
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_user_id", False, raising=False)
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_pro", False, raising=False)
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
    assert data.get("daily_limit_trial") == int(settings.daily_limit_trial)
    assert data.get("trial_period_days") == int(settings.trial_period_days)
    assert data.get("base_tier_price_inr") == int(settings.base_tier_price_inr)
    assert data.get("daily_limit_pro") == int(settings.daily_limit_pro)
    assert data.get("ingest_ocr_provider") == "none"
    assert data.get("ingest_ocr_ready") is False
    assert data.get("entitlements_store") == "sqlite"
    assert data.get("rate_limit_backend") == "memory"
    assert data.get("client_modes_supported") == ["citizen", "lawyer"]
    assert data.get("case_law_research_mode") == "off"
    assert data.get("lawyer_mode_requires_sign_in") is False
    assert data.get("lawyer_mode_requires_pro") is False
    assert data.get("lawyer_pro_gate_active") is False


def test_config_client_modes_supported_citizen_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    monkeypatch.setattr(settings, "client_modes_supported_csv", "citizen", raising=False)
    r = TestClient(app).get("/config")
    assert r.status_code == 200
    assert r.json().get("client_modes_supported") == ["citizen"]


def test_config_client_modes_supported_lawyer_only_adds_citizen(monkeypatch: pytest.MonkeyPatch) -> None:
    """CSV `lawyer` alone still lists citizen first (default public path)."""
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    monkeypatch.setattr(settings, "client_modes_supported_csv", "lawyer", raising=False)
    r = TestClient(app).get("/config")
    assert r.status_code == 200
    assert r.json().get("client_modes_supported") == ["citizen", "lawyer"]


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


def test_config_lawyer_mode_requires_sign_in_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_user_id", True, raising=False)
    r = TestClient(app).get("/config")
    assert r.status_code == 200
    assert r.json().get("lawyer_mode_requires_sign_in") is True


def test_config_case_law_mode_tavily_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    monkeypatch.setattr(settings, "case_law_mode", "tavily_preview", raising=False)
    r = TestClient(app).get("/config")
    assert r.status_code == 200
    assert r.json().get("case_law_research_mode") == "tavily_preview"


def test_config_lawyer_pro_gate_active_only_with_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_pro", True, raising=False)
    r = TestClient(app).get("/config")
    assert r.status_code == 200
    d = r.json()
    assert d.get("lawyer_mode_requires_pro") is True
    assert d.get("lawyer_pro_gate_active") is False

    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    r2 = TestClient(app).get("/config")
    assert r2.json().get("lawyer_pro_gate_active") is True
