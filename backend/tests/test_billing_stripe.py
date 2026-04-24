"""Stripe billing routes (P2-01) — Stripe SDK mocked."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_create_checkout_requires_stripe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    r = TestClient(app).post("/billing/create-checkout-session")
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "billing_not_stripe_mode"


def test_create_checkout_503_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_secret_key", "", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id", "", raising=False)
    r = TestClient(app).post("/billing/create-checkout-session")
    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "stripe_checkout_not_configured"


def test_create_checkout_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake", raising=False)
    monkeypatch.setattr(settings, "stripe_price_id", "price_test_fake", raising=False)
    monkeypatch.setattr(settings, "public_app_url", "http://localhost:3000", raising=False)

    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/c/pay/cs_test_123"

    def fake_create(**kwargs: object) -> MagicMock:
        assert kwargs.get("mode") == "subscription"
        assert kwargs.get("client_reference_id") == "user_clerk_1"
        sd = kwargs.get("subscription_data")
        assert isinstance(sd, dict) and sd.get("metadata", {}).get("clerk_user_id") == "user_clerk_1"
        return fake_session

    monkeypatch.setattr("app.api.v1.billing.stripe.checkout.Session.create", fake_create)
    r = TestClient(app).post(
        "/billing/create-checkout-session",
        headers={"X-User-Id": "user_clerk_1"},
    )
    assert r.status_code == 200
    assert r.json()["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_123"


def test_create_portal_requires_stripe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    r = TestClient(app).post("/billing/create-portal-session", headers={"X-User-Id": "u1"})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "billing_not_stripe_mode"


def test_create_portal_503_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_secret_key", "", raising=False)
    r = TestClient(app).post("/billing/create-portal-session", headers={"X-User-Id": "u1"})
    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "stripe_portal_not_configured"


def test_create_portal_400_without_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake", raising=False)
    r = TestClient(app).post("/billing/create-portal-session")
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "billing_portal_user_required"


def test_create_portal_404_without_customer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake", raising=False)
    monkeypatch.setattr(settings, "entitlements_db_path", ":memory:", raising=False)
    from app.services.pro_entitlements_store import reset_pro_entitlements_store_for_tests

    reset_pro_entitlements_store_for_tests()
    r = TestClient(app).post("/billing/create-portal-session", headers={"X-User-Id": "user_no_customer"})
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "stripe_customer_missing"


def test_create_portal_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake", raising=False)
    monkeypatch.setattr(settings, "entitlements_db_path", ":memory:", raising=False)
    monkeypatch.setattr(settings, "public_app_url", "http://localhost:3000", raising=False)
    from app.services.pro_entitlements_store import reset_pro_entitlements_store_for_tests, upsert_row

    reset_pro_entitlements_store_for_tests()
    upsert_row(
        clerk_user_id="user_with_cust",
        stripe_customer_id="cus_test_1",
        stripe_subscription_id="sub_test_1",
        status="active",
        current_period_end=1_700_000_000,
    )

    fake_session = MagicMock()
    fake_session.url = "https://billing.stripe.com/session/test_1"

    def fake_portal_create(**kwargs: object) -> MagicMock:
        assert kwargs.get("customer") == "cus_test_1"
        assert "return_url" in kwargs
        return fake_session

    monkeypatch.setattr("app.api.v1.billing.stripe.billing_portal.Session.create", fake_portal_create)
    r = TestClient(app).post(
        "/billing/create-portal-session",
        headers={"X-User-Id": "user_with_cust"},
    )
    assert r.status_code == 200
    assert r.json()["portal_url"] == "https://billing.stripe.com/session/test_1"


def test_webhook_503_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "", raising=False)
    r = TestClient(app).post("/billing/stripe-webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})
    assert r.status_code == 503


def test_webhook_400_missing_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test", raising=False)
    r = TestClient(app).post("/billing/stripe-webhook", content=b"{}")
    assert r.status_code == 400


def test_webhook_ok_mocked_construct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test", raising=False)

    def fake_construct(payload: bytes, sig: str, secret: str) -> dict:
        return {
            "type": "checkout.session.completed",
            "id": "evt_test_1",
            "data": {"object": {"id": "cs_test_1", "metadata": {"clerk_user_id": "u1"}}},
        }

    monkeypatch.setattr("app.api.v1.billing.stripe.Webhook.construct_event", fake_construct)
    r = TestClient(app).post(
        "/billing/stripe-webhook",
        content=b'{"x":1}',
        headers={"stripe-signature": "t=1,v1=abc"},
    )
    assert r.status_code == 200
    assert r.json() == {"received": True}
