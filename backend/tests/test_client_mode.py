"""P0-3: client_mode resolution (body vs X-Client-Mode) and schema."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.generate import _resolve_client_mode
from app.api.v1.generate_schemas import GenerateRequest
from app.config import settings
from app.main import app
from app.services.ai_service import _rag_top_k_for_client_mode


def test_resolve_body_wins_over_header() -> None:
    assert _resolve_client_mode("citizen", "lawyer") == "citizen"
    assert _resolve_client_mode("lawyer", "citizen") == "lawyer"


def test_resolve_header_aliases() -> None:
    assert _resolve_client_mode(None, "Lawyer") == "lawyer"
    assert _resolve_client_mode(None, "legal_professional") == "lawyer"
    assert _resolve_client_mode(None, "pro") == "lawyer"
    assert _resolve_client_mode(None, "public") == "citizen"
    assert _resolve_client_mode(None, None) == "citizen"


def test_generate_request_client_mode_optional() -> None:
    g = GenerateRequest.model_validate({"user_input": "police complaint help"})
    assert g.client_mode is None
    g2 = GenerateRequest.model_validate({"user_input": "x", "client_mode": "lawyer"})
    assert g2.client_mode == "lawyer"


def test_invalid_x_client_mode_422() -> None:
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages dispute"},
        headers={"X-Client-Mode": "not-a-mode"},
    )
    assert r.status_code == 422
    d = r.json().get("detail")
    assert isinstance(d, dict)
    assert d.get("error_code") == "invalid_client_mode"


@pytest.mark.rag
def test_rag_top_k_for_client_mode_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rag_top_k_citizen", 8, raising=False)
    monkeypatch.setattr(settings, "rag_top_k_lawyer", 16, raising=False)
    assert _rag_top_k_for_client_mode("citizen") == 8
    assert _rag_top_k_for_client_mode("lawyer") == 16


def test_generate_accepts_client_mode_body_when_openai_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional client_mode must not break validation before the OpenAI gate."""
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_user_id", False, raising=False)
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages dispute", "client_mode": "lawyer"},
    )
    assert r.status_code == 503
    assert r.json()["detail"].get("error_code") == "generate_openai_unconfigured"


def test_lawyer_mode_requires_sign_in_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_user_id", True, raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages dispute", "client_mode": "lawyer"},
    )
    assert r.status_code == 403
    assert r.json()["detail"].get("error_code") == "lawyer_mode_requires_sign_in"


def test_lawyer_mode_allowed_with_user_id_when_sign_in_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_user_id", True, raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages dispute", "client_mode": "lawyer"},
        headers={"X-User-Id": "user_abc"},
    )
    assert r.status_code == 503
    assert r.json()["detail"].get("error_code") == "generate_openai_unconfigured"


def test_lawyer_mode_requires_pro_when_stripe_and_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.pro_entitlements_store import reset_pro_entitlements_store_for_tests, upsert_row

    monkeypatch.setattr(settings, "lawyer_client_mode_requires_user_id", False, raising=False)
    monkeypatch.setattr(settings, "lawyer_client_mode_requires_pro", True, raising=False)
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "entitlements_db_path", ":memory:", raising=False)
    reset_pro_entitlements_store_for_tests()
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages dispute", "client_mode": "lawyer"},
        headers={"X-User-Id": "clerk_not_pro"},
    )
    assert r.status_code == 403
    assert r.json()["detail"].get("error_code") == "lawyer_mode_requires_pro"

    reset_pro_entitlements_store_for_tests()
    upsert_row(
        clerk_user_id="clerk_pro_u",
        stripe_customer_id="cus_x",
        stripe_subscription_id="sub_x",
        status="active",
        current_period_end=2_000_000_000,
    )
    r2 = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages dispute", "client_mode": "lawyer"},
        headers={"X-User-Id": "clerk_pro_u"},
    )
    assert r2.status_code == 503
    assert r2.json()["detail"].get("error_code") == "generate_openai_unconfigured"
    reset_pro_entitlements_store_for_tests()
