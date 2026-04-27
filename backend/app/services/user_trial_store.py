"""
First sign-in (Clerk) tracking for a time-limited free trial of higher daily usage.

- On first authenticated request, we record `first_seen_utc`.
- For `TRIAL_PERIOD_DAYS` (default 7) after that moment, the user uses `DAILY_LIMIT_TRIAL` per day.
- After the trial window, they use `DAILY_LIMIT_AUTHENTICATED` (default 10) as the post-trial base plan.

`TRIAL_PERIOD_DAYS=0` disables the trial: everyone on the base plan uses `DAILY_LIMIT_AUTHENTICATED` only.

SQLite: `TRIAL_DB_PATH` or `var/trial_users.sqlite` under the API working directory. Tests should set
`TRIAL_DB_PATH` to a temp file or use `reset_trial_store_for_tests`.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_db_path_bound: str | None = None


def _default_db_path() -> str:
    return "var/trial_users.sqlite"


def _db_path() -> str:
    p = (getattr(settings, "trial_db_path", None) or "").strip()
    return p if p else _default_db_path()


def _connect() -> sqlite3.Connection:
    global _conn, _db_path_bound
    path = _db_path()
    with _lock:
        if _conn is not None and _db_path_bound == path:
            return _conn
        if _conn is not None:
            try:
                _conn.close()
            except OSError:
                pass
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _db_path_bound = path
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS user_trial ("
            "user_id TEXT NOT NULL PRIMARY KEY, "
            "first_seen_utc TEXT NOT NULL)"
        )
        _conn.commit()
        return _conn


def reset_trial_store_for_tests() -> None:
    """Close in-memory or temp DB between tests; next call reopens on current path."""
    global _conn, _db_path_bound
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except OSError:
                pass
        _conn = None
        _db_path_bound = None


def ensure_first_seen_utc(user_id: str) -> str:
    """Idempotent: returns ISO-8601 first_seen_utc (UTC) for this user, creating a row on first use."""
    uid = user_id.strip()
    if not uid:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    conn = _connect()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with _lock:
        cur = conn.execute("SELECT first_seen_utc FROM user_trial WHERE user_id = ?", (uid,))
        row = cur.fetchone()
        if row and row[0]:
            return str(row[0])
        try:
            conn.execute("INSERT INTO user_trial (user_id, first_seen_utc) VALUES (?, ?)", (uid, now))
            conn.commit()
        except sqlite3.IntegrityError:
            cur2 = conn.execute("SELECT first_seen_utc FROM user_trial WHERE user_id = ?", (uid,))
            row2 = cur2.fetchone()
            if row2 and row2[0]:
                return str(row2[0])
    return now


def _parse_iso(iso: str) -> datetime | None:
    try:
        s = str(iso or "").replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except (OSError, ValueError, TypeError):
        return None


def trial_ends_at_utc(user_id: str) -> str | None:
    """End of the trial window (ISO, Z), or None if trial is disabled (period 0) or unparseable."""
    if int(getattr(settings, "trial_period_days", 0) or 0) <= 0:
        return None
    uid = user_id.strip()
    if not uid:
        return None
    first = ensure_first_seen_utc(uid)
    start = _parse_iso(first)
    if start is None:
        return None
    end = start + timedelta(days=int(getattr(settings, "trial_period_days", 7)))
    return end.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_in_trial(user_id: str) -> bool:
    if int(getattr(settings, "trial_period_days", 0) or 0) <= 0:
        return False
    uid = user_id.strip()
    if not uid:
        return False
    first = ensure_first_seen_utc(uid)
    start = _parse_iso(first)
    if start is None:
        return False
    days = int(getattr(settings, "trial_period_days", 7) or 7)
    end = start + timedelta(days=days)
    return datetime.now(timezone.utc) < end


def trial_info(user_id: str) -> dict[str, Any]:
    in_t = is_in_trial(user_id)
    ends = trial_ends_at_utc(user_id) if in_t else None
    first = None
    if (user_id or "").strip() and int(getattr(settings, "trial_period_days", 0) or 0) > 0:
        first = ensure_first_seen_utc(user_id.strip())
    return {
        "in_trial": in_t,
        "trial_ends_at_utc": ends,
        "first_seen_utc": first,
    }
