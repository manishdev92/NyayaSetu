from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_ready_includes_config_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "sk-test", raising=False)
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini", raising=False)
    monkeypatch.setattr(settings, "rag_vector_store", "local", raising=False)
    monkeypatch.setattr(settings, "pinecone_api_key", "", raising=False)
    monkeypatch.setattr(settings, "pinecone_index", "nyaya-legal-kb", raising=False)
    r = TestClient(app).get("/ready")
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "ok"
    assert d.get("openai_configured") is True
    assert d.get("openai_model") == "gpt-4o-mini"
    assert d.get("rag_vector_store") == "local"
    assert d.get("pinecone_configured") is False
    assert d.get("stripe_checkout_ready") is False
    assert d.get("stripe_portal_ready") is False
    assert d.get("client_modes_supported") == ["citizen", "lawyer"]
    assert d.get("lawyer_mode_requires_sign_in") is False
    assert d.get("lawyer_mode_requires_pro") is False
    assert d.get("lawyer_pro_gate_active") is False


@pytest.mark.rag
def test_ready_pinecone_configured_only_with_key_and_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    monkeypatch.setattr(settings, "rag_vector_store", "pinecone", raising=False)
    monkeypatch.setattr(settings, "pinecone_api_key", "pc-xxx", raising=False)
    monkeypatch.setattr(settings, "pinecone_index", "index-1", raising=False)
    r = TestClient(app).get("/ready")
    d = r.json()
    assert d.get("pinecone_configured") is True
    assert d.get("client_modes_supported") == ["citizen", "lawyer"]
