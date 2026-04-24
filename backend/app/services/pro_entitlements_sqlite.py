"""
SQLite backend for Stripe → Clerk subscription rows (P2-02).

Default file `var/entitlements.sqlite` under the API cwd unless `ENTITLEMENTS_DB_PATH` is set.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_db_path_seen: str | None = None

PRO_STATUSES = frozenset({"active", "trialing"})


def entitlements_db_path_resolved() -> str:
    p = (getattr(settings, "entitlements_db_path", None) or "").strip()
    return p if p else "var/entitlements.sqlite"


def reset_pro_entitlements_store_for_tests() -> None:
    """Close DB handle so the next operation reconnects (tests / path changes)."""
    global _conn, _db_path_seen
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except sqlite3.Error:
                pass
            _conn = None
        _db_path_seen = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_conn() -> sqlite3.Connection:
    global _conn, _db_path_seen
    path = entitlements_db_path_resolved()
    with _lock:
        if _conn is not None and _db_path_seen == path:
            return _conn
        if _conn is not None:
            try:
                _conn.close()
            except sqlite3.Error:
                pass
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _db_path_seen = path
        _init_schema(_conn)
        return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS clerk_entitlements (
            clerk_user_id TEXT PRIMARY KEY,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            status TEXT NOT NULL,
            current_period_end INTEGER,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_clerk_entitlements_subscription
        ON clerk_entitlements(stripe_subscription_id)
        WHERE stripe_subscription_id IS NOT NULL AND stripe_subscription_id != '';
        """
    )
    conn.commit()


def clerk_has_pro_entitlement(clerk_user_id: str) -> bool:
    if settings.billing_mode != "stripe" or not clerk_user_id.strip():
        return False
    row = get_row(clerk_user_id.strip())
    if row is None:
        return False
    return str(row["status"]) in PRO_STATUSES


def get_row(clerk_user_id: str) -> sqlite3.Row | None:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM clerk_entitlements WHERE clerk_user_id = ?",
        (clerk_user_id,),
    )
    return cur.fetchone()


def find_clerk_by_subscription_id(subscription_id: str) -> str | None:
    if not subscription_id.strip():
        return None
    conn = _get_conn()
    cur = conn.execute(
        "SELECT clerk_user_id FROM clerk_entitlements WHERE stripe_subscription_id = ?",
        (subscription_id.strip(),),
    )
    r = cur.fetchone()
    return str(r[0]) if r else None


def upsert_row(
    *,
    clerk_user_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    status: str,
    current_period_end: int | None,
) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO clerk_entitlements (
            clerk_user_id, stripe_customer_id, stripe_subscription_id,
            status, current_period_end, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(clerk_user_id) DO UPDATE SET
            stripe_customer_id = excluded.stripe_customer_id,
            stripe_subscription_id = excluded.stripe_subscription_id,
            status = excluded.status,
            current_period_end = excluded.current_period_end,
            updated_at = excluded.updated_at
        """,
        (
            clerk_user_id,
            stripe_customer_id or None,
            stripe_subscription_id or None,
            status,
            current_period_end,
            _now_iso(),
        ),
    )
    conn.commit()


def apply_checkout_session_completed(session: dict) -> None:
    if str(session.get("mode") or "") != "subscription":
        return
    clerk = str(session.get("client_reference_id") or "").strip()
    if not clerk:
        md = session.get("metadata")
        if isinstance(md, dict):
            clerk = str(md.get("clerk_user_id") or "").strip()
    if not clerk:
        logger.warning("checkout.session.completed: missing clerk user id (client_reference_id / metadata)")
        return
    sub = session.get("subscription")
    cust = session.get("customer")
    sub_id = str(sub).strip() if sub else ""
    cust_id = str(cust).strip() if cust else ""
    upsert_row(
        clerk_user_id=clerk,
        stripe_customer_id=cust_id,
        stripe_subscription_id=sub_id,
        status="active",
        current_period_end=None,
    )
    logger.info(
        "entitlements: checkout.session.completed clerk=%s sub=%s",
        clerk[:48],
        sub_id[:32] if sub_id else "",
    )


def apply_subscription_object(obj: dict) -> None:
    sub_id = str(obj.get("id") or "").strip()
    status = str(obj.get("status") or "").strip() or "canceled"
    cust = str(obj.get("customer") or "").strip()
    cpe = obj.get("current_period_end")
    cpe_int: int | None = int(cpe) if cpe is not None and str(cpe).isdigit() else None

    clerk = ""
    md = obj.get("metadata")
    if isinstance(md, dict):
        clerk = str(md.get("clerk_user_id") or "").strip()
    if not clerk and sub_id:
        clerk = find_clerk_by_subscription_id(sub_id) or ""
    if not clerk:
        logger.info(
            "entitlements: subscription event without clerk mapping sub=%s status=%s",
            sub_id[:24],
            status,
        )
        return

    upsert_row(
        clerk_user_id=clerk,
        stripe_customer_id=cust,
        stripe_subscription_id=sub_id,
        status=status,
        current_period_end=cpe_int,
    )
    logger.info(
        "entitlements: subscription sync clerk=%s status=%s sub=%s",
        clerk[:48],
        status,
        sub_id[:32] if sub_id else "",
    )


def handle_stripe_event(event_type: str, data_object: dict) -> None:
    if settings.billing_mode != "stripe":
        return
    et = str(event_type or "")
    if et == "checkout.session.completed":
        apply_checkout_session_completed(data_object)
    elif et in ("customer.subscription.updated", "customer.subscription.deleted"):
        apply_subscription_object(data_object)
