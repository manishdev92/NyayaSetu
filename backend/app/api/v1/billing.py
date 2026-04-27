"""
Stripe Checkout (P2-01): subscription session + webhook verification.
P2-02: webhook persists subscription → Clerk mapping; Pro daily cap + GET /billing/entitlements.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.services.pro_entitlements_store import (
    clerk_has_pro_entitlement,
    get_row,
    handle_stripe_event,
)
from app.services.usage_limit import effective_daily_limit_for_user
from app.services.user_trial_store import trial_info

logger = logging.getLogger(__name__)

router = APIRouter()


def _public_base_url() -> str:
    return str(settings.public_app_url or "http://localhost:3000").rstrip("/")


def stripe_checkout_ready() -> bool:
    """True when API can create a Checkout Session (Stripe mode + secrets + price id)."""
    if settings.billing_mode != "stripe":
        return False
    return bool(
        settings.stripe_secret_key.strip()
        and settings.stripe_price_id.strip()
    )


def stripe_portal_ready() -> bool:
    """True when Customer Portal can be opened (Stripe mode + secret; needs `stripe_customer_id` in DB per user)."""
    if settings.billing_mode != "stripe":
        return False
    return bool(settings.stripe_secret_key.strip())


def _require_stripe_mode() -> None:
    if settings.billing_mode != "stripe":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Billing is not in Stripe mode. Set BILLING_MODE=stripe.",
                "error_code": "billing_not_stripe_mode",
            },
        )


def _require_checkout_ready() -> None:
    if not stripe_checkout_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Stripe Checkout is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID.",
                "error_code": "stripe_checkout_not_configured",
            },
        )


@router.get("/billing/entitlements")
def get_billing_entitlements(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, bool | str | int | None]:
    """
    Pro state for the signed-in Clerk user (from webhook-persisted subscription rows).
    When `BILLING_MODE` is not `stripe`, returns `pro: false` (no DB lookup).
    """
    base_inr = int(getattr(settings, "base_tier_price_inr", 1))
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    if settings.billing_mode != "stripe":
        if not uid:
            return {
                "pro": False,
                "subscription_status": None,
                "daily_limit": int(settings.daily_limit_authenticated),
                "in_trial": False,
                "trial_ends_at_utc": None,
                "base_tier_price_inr": base_inr,
            }
        ti = trial_info(uid)
        cap = effective_daily_limit_for_user(uid)
        return {
            "pro": False,
            "subscription_status": None,
            "daily_limit": cap,
            "in_trial": bool(ti["in_trial"]),
            "trial_ends_at_utc": ti["trial_ends_at_utc"],
            "base_tier_price_inr": base_inr,
        }
    if not uid:
        return {
            "pro": False,
            "subscription_status": None,
            "daily_limit": int(settings.daily_limit_anonymous),
            "in_trial": False,
            "trial_ends_at_utc": None,
            "base_tier_price_inr": base_inr,
        }
    pro = clerk_has_pro_entitlement(uid)
    row = get_row(uid)
    st = str(row["status"]) if row is not None else None
    cap = int(settings.daily_limit_pro) if pro else effective_daily_limit_for_user(uid)
    ti = trial_info(uid) if not pro else {"in_trial": False, "trial_ends_at_utc": None}
    return {
        "pro": pro,
        "subscription_status": st,
        "daily_limit": cap,
        "in_trial": bool(ti["in_trial"]),
        "trial_ends_at_utc": ti["trial_ends_at_utc"],
        "base_tier_price_inr": base_inr,
    }


@router.post("/billing/create-checkout-session")
def create_checkout_session(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, str]:
    """
    Returns `{ "checkout_url": "<Stripe-hosted URL>" }`.
    Sends `X-User-Id` (Clerk user id) as `client_reference_id` + `metadata` on session and subscription.
    """
    _require_stripe_mode()
    _require_checkout_ready()

    stripe.api_key = settings.stripe_secret_key.strip()
    base = _public_base_url()
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None

    metadata: dict[str, str] = {}
    if uid:
        metadata["clerk_user_id"] = uid[:500]

    create_kwargs: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": settings.stripe_price_id.strip(), "quantity": 1}],
        "success_url": f"{base}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/?checkout=cancel",
        "client_reference_id": uid,
        "metadata": metadata or {"app": "nyayasetu"},
        "allow_promotion_codes": True,
    }
    if uid:
        create_kwargs["subscription_data"] = {"metadata": {"clerk_user_id": uid[:500]}}

    try:
        session = stripe.checkout.Session.create(**create_kwargs)
    except stripe.StripeError as e:
        logger.warning("stripe_checkout_create_failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(getattr(e, "user_message", None) or e),
                "error_code": "stripe_upstream_error",
            },
        ) from e

    url = session.url
    if not url:
        raise HTTPException(
            status_code=502,
            detail={"message": "Stripe returned no checkout URL.", "error_code": "stripe_upstream_error"},
        )
    return {"checkout_url": url}


@router.post("/billing/create-portal-session")
def create_portal_session(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, str]:
    """
    Returns `{ "portal_url": "<Stripe-hosted URL>" }` for the Clerk user's Stripe customer (P2-03).
    """
    _require_stripe_mode()
    if not settings.stripe_secret_key.strip():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Stripe Customer Portal is not configured. Set STRIPE_SECRET_KEY.",
                "error_code": "stripe_portal_not_configured",
            },
        )
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    if not uid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Sign in is required to open the billing portal.",
                "error_code": "billing_portal_user_required",
            },
        )
    row = get_row(uid)
    cid = str(row["stripe_customer_id"] or "").strip() if row is not None else ""
    if not cid:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No Stripe customer on file yet. Complete checkout first, or wait for webhook sync.",
                "error_code": "stripe_customer_missing",
            },
        )
    stripe.api_key = settings.stripe_secret_key.strip()
    base = _public_base_url()
    try:
        session = stripe.billing_portal.Session.create(
            customer=cid,
            return_url=f"{base}/?portal=return",
        )
    except stripe.StripeError as e:
        logger.warning("stripe_portal_create_failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(getattr(e, "user_message", None) or e),
                "error_code": "stripe_upstream_error",
            },
        ) from e
    url = session.url
    if not url:
        raise HTTPException(
            status_code=502,
            detail={"message": "Stripe returned no portal URL.", "error_code": "stripe_upstream_error"},
        )
    return {"portal_url": url}


@router.post("/billing/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
) -> dict[str, bool]:
    """
    Verifies `Stripe-Signature` using `STRIPE_WEBHOOK_SECRET`.
    Handles `checkout.session.completed`, `customer.subscription.updated|deleted` → SQLite (P2-02).
    """
    secret = settings.stripe_webhook_secret.strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "STRIPE_WEBHOOK_SECRET is not set; webhook handler disabled.",
                "error_code": "stripe_webhook_not_configured",
            },
        )
    if not stripe_signature:
        raise HTTPException(
            status_code=400,
            detail={"message": "Missing Stripe-Signature header.", "error_code": "stripe_webhook_bad_request"},
        )

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, secret)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": f"Invalid payload: {e!s}", "error_code": "stripe_webhook_invalid_payload"},
        ) from e
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid signature.", "error_code": "stripe_webhook_invalid_signature"},
        ) from e

    et = str(event.get("type") or "")
    eid = str(event.get("id") or "")
    data_obj = event.get("data", {}).get("object") if isinstance(event.get("data"), dict) else None
    session_id = ""
    clerk_ref = ""
    if isinstance(data_obj, dict):
        session_id = str(data_obj.get("id") or "")
        md = data_obj.get("metadata")
        if isinstance(md, dict):
            clerk_ref = str(md.get("clerk_user_id") or "")

    logger.info(
        "stripe_webhook event_type=%s event_id=%s session_id=%s clerk_user_id=%s",
        et,
        eid,
        session_id[:80],
        clerk_ref[:80],
    )

    if isinstance(data_obj, dict):
        try:
            handle_stripe_event(et, data_obj)
        except sqlite3.Error as e:
            logger.exception("entitlements persist failed: %s", e)

    return {"received": True}
