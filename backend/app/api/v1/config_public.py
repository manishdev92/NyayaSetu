"""Read-only public client config (no secrets)."""

from __future__ import annotations

import shutil

from fastapi import APIRouter

from app.api.v1.billing import stripe_checkout_ready, stripe_portal_ready
from app.config import settings

router = APIRouter()


def _ingest_ocr_ready() -> bool:
    p = str(settings.ingest_ocr_provider).strip().lower()
    if p == "none":
        return False
    if p == "openai":
        return bool(settings.openai_api_key.strip())
    if p == "textract":
        return True
    if p == "tesseract":
        return bool(shutil.which("tesseract"))
    return False


@router.get("/config")
def public_config() -> dict[str, str | bool | int]:
    """
    Billing / product flags. Set `BILLING_MODE=none|stub|stripe` in the API env.
    - none: no paywall copy in the app (default).
    - stub: show "Pro coming soon" (no real charges).
    - stripe: show upgrade UI; Checkout when `stripe_checkout_ready`; Portal when `stripe_portal_ready` (see `billing.py`).
    """
    mode = str(settings.billing_mode)
    rag = str(settings.rag_vector_store)
    if rag not in ("local", "pinecone"):
        rag = "local"
    checkout = stripe_checkout_ready()
    portal = stripe_portal_ready()
    ent_be = "postgres" if (getattr(settings, "entitlements_database_url", None) or "").strip() else "sqlite"
    rl_be = "redis" if (getattr(settings, "redis_url", None) or "").strip() else "memory"
    return {
        "evaluator_dual_draft_enabled": bool(getattr(settings, "evaluator_dual_draft_enabled", False)),
        "billing_mode": mode,
        "paywall_visible": mode in ("stub", "stripe"),
        "stripe_checkout_ready": checkout,
        "stripe_portal_ready": portal,
        "stripe_webhook_ready": bool(settings.stripe_webhook_secret.strip()),
        "entitlements_store": ent_be,
        "rate_limit_backend": rl_be,
        "rag_vector_store": rag,
        "max_upload_bytes": int(settings.max_upload_bytes),
        "daily_limit_authenticated": int(settings.daily_limit_authenticated),
        "daily_limit_pro": int(settings.daily_limit_pro),
        "ingest_ocr_provider": str(settings.ingest_ocr_provider).strip().lower(),
        "ingest_ocr_ready": _ingest_ocr_ready(),
    }
