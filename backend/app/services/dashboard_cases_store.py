"""
SQLite persistence for P8-01 dashboard saved cases (per Clerk user).

Default path `var/dashboard_cases.sqlite` under API cwd, or `CASES_DB_PATH` / `:memory:` for tests.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_db_path_seen: str | None = None

MAX_RESULT_JSON_BYTES = 400_000


def cases_db_path_resolved() -> str:
    p = (getattr(settings, "cases_db_path", None) or "").strip()
    return p if p else "var/dashboard_cases.sqlite"


def reset_dashboard_cases_store_for_tests() -> None:
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
    path = cases_db_path_resolved()
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
        CREATE TABLE IF NOT EXISTS saved_cases (
            id TEXT PRIMARY KEY,
            clerk_user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            result_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_saved_cases_user_updated
        ON saved_cases(clerk_user_id, updated_at);
        """
    )
    conn.commit()


def list_cases(clerk_user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    uid = clerk_user_id.strip()
    if not uid:
        return []
    cap = max(1, min(100, int(limit)))
    conn = _get_conn()
    cur = conn.execute(
        """
        SELECT id, title, summary, result_json, created_at, updated_at
        FROM saved_cases
        WHERE clerk_user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (uid, cap),
    )
    rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        payload: dict[str, Any] | None = None
        raw = r["result_json"]
        if raw:
            try:
                payload = json.loads(str(raw))
            except json.JSONDecodeError:
                payload = None
        out.append(
            {
                "id": str(r["id"]),
                "title": str(r["title"]),
                "summary": str(r["summary"]) if r["summary"] is not None else None,
                "result": payload,
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
            }
        )
    return out


def create_case(
    *,
    clerk_user_id: str,
    title: str,
    summary: str | None,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    uid = clerk_user_id.strip()
    if not uid:
        raise ValueError("clerk_user_id required")
    t = title.strip()
    if not t:
        raise ValueError("title required")
    cid = uuid.uuid4().hex
    now = _now_iso()
    blob = ""
    if result is not None:
        raw = json.dumps(result, ensure_ascii=False)
        if len(raw.encode("utf-8")) > MAX_RESULT_JSON_BYTES:
            raw = raw.encode("utf-8")[: MAX_RESULT_JSON_BYTES - 80].decode("utf-8", errors="ignore") + "\n/* truncated */"
        blob = raw
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO saved_cases (id, clerk_user_id, title, summary, result_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (cid, uid, t[:500], (summary or "").strip()[:4000] or None, blob or None, now, now),
    )
    conn.commit()
    logger.info("dashboard_case created id=%s clerk=%s", cid[:12], uid[:24])
    return {
        "id": cid,
        "title": t[:500],
        "summary": (summary or "").strip()[:4000] or None,
        "result": result,
        "created_at": now,
        "updated_at": now,
    }


def delete_case(clerk_user_id: str, case_id: str) -> bool:
    uid = clerk_user_id.strip()
    cid = case_id.strip()
    if not uid or not cid:
        return False
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM saved_cases WHERE id = ? AND clerk_user_id = ?",
        (cid, uid),
    )
    conn.commit()
    return cur.rowcount > 0
