"""
Stripe subscription → Clerk user mapping (P2-02).

Backends:
- **SQLite** (default): `ENTITLEMENTS_DB_PATH` or `var/entitlements.sqlite`.
- **Postgres** (multi-instance): set `ENTITLEMENTS_DATABASE_URL` (see `docs/ENTITLEMENTS_POSTGRES.md`).
"""

from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from app.config import settings

_impl_mod: Any | None = None
_impl_tag: str | None = None


def _want_postgres() -> bool:
    return bool((getattr(settings, "entitlements_database_url", None) or "").strip())


def _impl() -> Any:
    global _impl_mod, _impl_tag
    tag = "pg" if _want_postgres() else "sqlite"
    if _impl_mod is not None and _impl_tag == tag:
        return _impl_mod
    if tag == "pg":
        from app.services import pro_entitlements_postgres as m
    else:
        from app.services import pro_entitlements_sqlite as m
    _impl_mod = m
    _impl_tag = tag
    return m


def reset_pro_entitlements_store_for_tests() -> None:
    global _impl_mod, _impl_tag
    if _impl_mod is not None:
        try:
            _impl_mod.reset_pro_entitlements_store_for_tests()
        finally:
            _impl_mod = None
            _impl_tag = None


def clerk_has_pro_entitlement(clerk_user_id: str) -> bool:
    return bool(_impl().clerk_has_pro_entitlement(clerk_user_id))


def get_row(clerk_user_id: str) -> sqlite3.Row | Mapping[str, Any] | None:
    return _impl().get_row(clerk_user_id)


def find_clerk_by_subscription_id(subscription_id: str) -> str | None:
    return _impl().find_clerk_by_subscription_id(subscription_id)


def upsert_row(
    *,
    clerk_user_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    status: str,
    current_period_end: int | None,
) -> None:
    _impl().upsert_row(
        clerk_user_id=clerk_user_id,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        status=status,
        current_period_end=current_period_end,
    )


def handle_stripe_event(event_type: str, data_object: dict) -> None:
    _impl().handle_stripe_event(event_type, data_object)
