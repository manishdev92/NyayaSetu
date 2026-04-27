"""
SQLite persistence for lightweight thumbs feedback (P8-02).

Default path `var/response_feedback.sqlite` under API cwd, or `FEEDBACK_DB_PATH` / `:memory:` for tests.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_db_path_seen: str | None = None


def feedback_db_path_resolved() -> str:
    p = (getattr(settings, "feedback_db_path", None) or "").strip()
    return p if p else "var/response_feedback.sqlite"


def reset_response_feedback_store_for_tests() -> None:
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
    path = feedback_db_path_resolved()
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
        _init_schema(_conn)
        _db_path_seen = path
        return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS response_feedback (
            id TEXT PRIMARY KEY,
            clerk_user_id TEXT,
            helpful INTEGER NOT NULL,
            client_mode TEXT NOT NULL,
            task_type TEXT NOT NULL,
            locale TEXT,
            generation_mode TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_response_feedback_created_at
        ON response_feedback(created_at);
        CREATE INDEX IF NOT EXISTS ix_response_feedback_user
        ON response_feedback(clerk_user_id);
        """
    )
    conn.commit()


def submit_response_feedback(
    *,
    clerk_user_id: str | None,
    helpful: bool,
    client_mode: str,
    task_type: str,
    locale: str | None = None,
    generation_mode: str | None = None,
) -> dict[str, Any]:
    cid = clerk_user_id.strip() if isinstance(clerk_user_id, str) and clerk_user_id.strip() else None
    cm = client_mode.strip().lower()
    tt = task_type.strip().lower()
    if cm not in ("citizen", "lawyer"):
        raise ValueError("invalid client_mode")
    if tt not in ("draft_letter", "qa_only", "draft_with_qa", "consumer_complaint_filing"):
        raise ValueError("invalid task_type")
    loc = (locale or "").strip().lower()[:16] or None
    gm = (generation_mode or "").strip()[:80] or None
    rid = uuid.uuid4().hex
    now = _now_iso()
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO response_feedback (
            id, clerk_user_id, helpful, client_mode, task_type, locale, generation_mode, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (rid, cid, 1 if helpful else 0, cm, tt, loc, gm, now),
    )
    conn.commit()
    return {"id": rid, "created_at": now}


def count_feedback_for_tests() -> int:
    conn = _get_conn()
    cur = conn.execute("SELECT COUNT(1) AS c FROM response_feedback")
    row = cur.fetchone()
    return int(row["c"]) if row else 0


def summarize_feedback(*, days: int = 30) -> dict[str, Any]:
    """Aggregate thumbs feedback for a rolling UTC-day window."""
    d = max(1, min(365, int(days)))
    conn = _get_conn()
    now_day = datetime.now(timezone.utc).date()
    start_day = now_day - timedelta(days=d - 1)
    since_iso = f"{start_day.isoformat()}T00:00:00Z"

    total_row = conn.execute(
        """
        SELECT
            COUNT(1) AS total,
            SUM(CASE WHEN helpful = 1 THEN 1 ELSE 0 END) AS positive
        FROM response_feedback
        WHERE created_at >= ?
        """,
        (since_iso,),
    ).fetchone()
    total = int(total_row["total"]) if total_row and total_row["total"] is not None else 0
    positive = int(total_row["positive"]) if total_row and total_row["positive"] is not None else 0

    by_mode_rows = conn.execute(
        """
        SELECT
            client_mode,
            COUNT(1) AS total,
            SUM(CASE WHEN helpful = 1 THEN 1 ELSE 0 END) AS positive
        FROM response_feedback
        WHERE created_at >= ?
        GROUP BY client_mode
        ORDER BY client_mode ASC
        """,
        (since_iso,),
    ).fetchall()
    by_mode = [
        {
            "client_mode": str(r["client_mode"]),
            "total": int(r["total"]),
            "positive": int(r["positive"]) if r["positive"] is not None else 0,
        }
        for r in by_mode_rows
    ]

    by_task_rows = conn.execute(
        """
        SELECT
            task_type,
            COUNT(1) AS total,
            SUM(CASE WHEN helpful = 1 THEN 1 ELSE 0 END) AS positive
        FROM response_feedback
        WHERE created_at >= ?
        GROUP BY task_type
        ORDER BY total DESC, task_type ASC
        """,
        (since_iso,),
    ).fetchall()
    by_task = [
        {
            "task_type": str(r["task_type"]),
            "total": int(r["total"]),
            "positive": int(r["positive"]) if r["positive"] is not None else 0,
        }
        for r in by_task_rows
    ]

    by_day_rows = conn.execute(
        """
        SELECT
            SUBSTR(created_at, 1, 10) AS day,
            COUNT(1) AS total,
            SUM(CASE WHEN helpful = 1 THEN 1 ELSE 0 END) AS positive
        FROM response_feedback
        WHERE created_at >= ?
        GROUP BY day
        ORDER BY day ASC
        """,
        (since_iso,),
    ).fetchall()
    by_day_map = {
        str(r["day"]): {
            "day": str(r["day"]),
            "total": int(r["total"]),
            "positive": int(r["positive"]) if r["positive"] is not None else 0,
        }
        for r in by_day_rows
    }
    by_day: list[dict[str, Any]] = []
    for i in range(d):
        day = (start_day + timedelta(days=i)).isoformat()
        hit = by_day_map.get(day)
        if hit:
            by_day.append(hit)
        else:
            by_day.append({"day": day, "total": 0, "positive": 0})

    return {
        "days": d,
        "total": total,
        "positive": positive,
        "positive_rate": (positive / total) if total > 0 else 0.0,
        "by_mode": by_mode,
        "by_task_type": by_task,
        "by_day": by_day,
    }

