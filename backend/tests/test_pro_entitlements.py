"""P2-02: Stripe webhook → SQLite entitlements + GET /billing/entitlements + Pro daily cap."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import usage_limit as ul
from app.services.pro_entitlements_store import reset_pro_entitlements_store_for_tests


@pytest.fixture(autouse=True)
def _reset_entitlements_db(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Isolated SQLite file per test."""
    db = tmp_path / f"ent_{uuid.uuid4().hex}.sqlite"
    monkeypatch.setattr(settings, "entitlements_db_path", str(db), raising=False)
    reset_pro_entitlements_store_for_tests()
    yield
    reset_pro_entitlements_store_for_tests()


def test_webhook_checkout_completed_then_entitlements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test", raising=False)

    def fake_construct(payload: bytes, sig: str, secret: str) -> dict:
        return {
            "type": "checkout.session.completed",
            "id": "evt_cs",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "mode": "subscription",
                    "client_reference_id": "clerk_u_webhook",
                    "subscription": "sub_testhook",
                    "customer": "cus_testhook",
                    "metadata": {"clerk_user_id": "clerk_u_webhook"},
                }
            },
        }

    monkeypatch.setattr("app.api.v1.billing.stripe.Webhook.construct_event", fake_construct)
    c = TestClient(app)
    r = c.post(
        "/billing/stripe-webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=abc"},
    )
    assert r.status_code == 200
    er = c.get("/billing/entitlements", headers={"X-User-Id": "clerk_u_webhook"})
    assert er.status_code == 200
    body = er.json()
    assert body["pro"] is True
    assert body["subscription_status"] == "active"
    assert body["daily_limit"] == int(settings.daily_limit_pro)


def test_subscription_updated_cancels_pro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test", raising=False)
    c = TestClient(app)

    def complete(_payload: bytes, _sig: str, _secret: str) -> dict:
        return {
            "type": "checkout.session.completed",
            "id": "evt_1",
            "data": {
                "object": {
                    "id": "cs_1",
                    "mode": "subscription",
                    "client_reference_id": "clerk_cancel",
                    "subscription": "sub_cancel_1",
                    "customer": "cus_1",
                    "metadata": {},
                }
            },
        }

    monkeypatch.setattr("app.api.v1.billing.stripe.Webhook.construct_event", complete)
    assert c.post("/billing/stripe-webhook", content=b"{}", headers={"stripe-signature": "x"}).status_code == 200

    def sub_canceled(_payload: bytes, _sig: str, _secret: str) -> dict:
        return {
            "type": "customer.subscription.updated",
            "id": "evt_2",
            "data": {
                "object": {
                    "id": "sub_cancel_1",
                    "status": "canceled",
                    "customer": "cus_1",
                    "metadata": {"clerk_user_id": "clerk_cancel"},
                    "current_period_end": 1700000000,
                }
            },
        }

    monkeypatch.setattr("app.api.v1.billing.stripe.Webhook.construct_event", sub_canceled)
    assert c.post("/billing/stripe-webhook", content=b"{}", headers={"stripe-signature": "x"}).status_code == 200

    er = c.get("/billing/entitlements", headers={"X-User-Id": "clerk_cancel"})
    assert er.json()["pro"] is False
    assert er.json()["subscription_status"] == "canceled"


def test_entitlements_non_stripe_returns_no_pro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "billing_mode", "none", raising=False)
    r = TestClient(app).get("/billing/entitlements", headers={"X-User-Id": "any"})
    assert r.status_code == 200
    assert r.json()["pro"] is False


def test_pro_user_daily_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.pro_entitlements_store import upsert_row

    monkeypatch.setattr(settings, "billing_mode", "stripe", raising=False)
    monkeypatch.setattr(settings, "daily_limit_authenticated", 2, raising=False)
    monkeypatch.setattr(settings, "daily_limit_pro", 5, raising=False)
    reset_pro_entitlements_store_for_tests()
    uid = f"pro-cap-{uuid.uuid4().hex}"
    upsert_row(
        clerk_user_id=uid,
        stripe_customer_id="c",
        stripe_subscription_id="s",
        status="active",
        current_period_end=None,
    )
    for _ in range(5):
        ok, _ = ul.consume_request(user_id=uid, client_ip=None)
        assert ok is True
    ok6, s6 = ul.consume_request(user_id=uid, client_ip=None)
    assert ok6 is False
    assert s6.limit == 5
