"""
Per-user chat threads and messages (Clerk `X-User-Id`).

Default `var/chat_history.sqlite` or `CHAT_HISTORY_DB_PATH` / `:memory:` in tests.
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

MAX_CONTENT_CHARS = 200_000
MAX_META_JSON_BYTES = 400_000


def chat_history_db_path_resolved() -> str:
    p = (getattr(settings, "chat_history_db_path", None) or "").strip()
    return p if p else "var/chat_history.sqlite"


def reset_chat_history_store_for_tests() -> None:
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
    path = chat_history_db_path_resolved()
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
        _conn.execute("PRAGMA foreign_keys = ON")
        _init_schema(_conn)
        _db_path_seen = path
        return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chat_threads (
            id TEXT PRIMARY KEY,
            clerk_user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_chat_threads_user_updated
        ON chat_threads(clerk_user_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            meta_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_chat_messages_thread_created
        ON chat_messages(thread_id, created_at ASC);
        """
    )
    conn.commit()


def _truncate_content(s: str) -> str:
    if len(s) <= MAX_CONTENT_CHARS:
        return s
    return s[: MAX_CONTENT_CHARS - 20] + "\n… [truncated]"


def _normalize_meta(meta: dict[str, Any] | None) -> str | None:
    if not meta:
        return None
    raw = json.dumps(meta, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_META_JSON_BYTES:
        raw = (
            raw.encode("utf-8")[: MAX_META_JSON_BYTES - 80].decode("utf-8", errors="ignore")
            + "\n/* truncated */"
        )
    return raw


def list_threads(clerk_user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    uid = clerk_user_id.strip()
    if not uid:
        return []
    cap = max(1, min(100, int(limit)))
    conn = _get_conn()
    cur = conn.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM chat_threads
        WHERE clerk_user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (uid, cap),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        out.append(
            {
                "id": str(r["id"]),
                "title": str(r["title"]),
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
            }
        )
    return out


def list_messages_allow_empty(clerk_user_id: str, thread_id: str, *, limit: int = 500) -> list[dict[str, Any]] | None:
    """Return messages, or ``None`` if thread not found / not owned."""
    try:
        return list_messages(clerk_user_id, thread_id, limit=limit)
    except KeyError:
        return None

def create_thread(clerk_user_id: str, title: str | None = None) -> dict[str, Any]:
    uid = clerk_user_id.strip()
    if not uid:
        raise ValueError("clerk_user_id required")
    tid = uuid.uuid4().hex
    now = _now_iso()
    t = (title or "New chat").strip()[:500] or "New chat"
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO chat_threads (id, clerk_user_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (tid, uid, t, now, now),
    )
    conn.commit()
    logger.info("chat_thread created id=%s clerk=%s", tid[:12], uid[:24])
    return {"id": tid, "title": t, "created_at": now, "updated_at": now}


def _thread_owned(conn: sqlite3.Connection, clerk_user_id: str, thread_id: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM chat_threads WHERE id = ? AND clerk_user_id = ? LIMIT 1",
        (thread_id.strip(), clerk_user_id.strip()),
    )
    return cur.fetchone() is not None


def update_thread_title(clerk_user_id: str, thread_id: str, title: str) -> bool:
    uid = clerk_user_id.strip()
    tid = thread_id.strip()
    t = title.strip()[:500]
    if not uid or not tid or not t:
        return False
    conn = _get_conn()
    if not _thread_owned(conn, uid, tid):
        return False
    now = _now_iso()
    conn.execute(
        "UPDATE chat_threads SET title = ?, updated_at = ? WHERE id = ? AND clerk_user_id = ?",
        (t, now, tid, uid),
    )
    conn.commit()
    return True


def delete_thread(clerk_user_id: str, thread_id: str) -> bool:
    uid = clerk_user_id.strip()
    tid = thread_id.strip()
    if not uid or not tid:
        return False
    conn = _get_conn()
    cur = conn.execute(
        "DELETE FROM chat_threads WHERE id = ? AND clerk_user_id = ?",
        (tid, uid),
    )
    conn.commit()
    return cur.rowcount > 0


def append_message(
    clerk_user_id: str,
    thread_id: str,
    *,
    role: str,
    content: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    uid = clerk_user_id.strip()
    tid = thread_id.strip()
    r = role.strip().lower()
    if r not in ("user", "assistant"):
        raise ValueError("role must be user or assistant")
    if not uid or not tid:
        raise ValueError("user and thread_id required")
    body = _truncate_content(content or "")
    conn = _get_conn()
    if not _thread_owned(conn, uid, tid):
        raise KeyError(thread_id)
    mid = uuid.uuid4().hex
    now = _now_iso()
    meta_blob = _normalize_meta(meta)
    conn.execute(
        """
        INSERT INTO chat_messages (id, thread_id, role, content, meta_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (mid, tid, r, body, meta_blob, now),
    )
    conn.execute(
        "UPDATE chat_threads SET updated_at = ? WHERE id = ? AND clerk_user_id = ?",
        (now, tid, uid),
    )
    conn.commit()
    out_meta: dict[str, Any] | None = None
    if meta_blob:
        try:
            out_meta = json.loads(meta_blob)
        except json.JSONDecodeError:
            out_meta = None
    return {
        "id": mid,
        "thread_id": tid,
        "role": r,
        "content": body,
        "meta": out_meta,
        "created_at": now,
    }


def thread_exists_for_user(clerk_user_id: str, thread_id: str) -> bool:
    uid = clerk_user_id.strip()
    tid = thread_id.strip()
    if not uid or not tid:
        return False
    conn = _get_conn()
    return _thread_owned(conn, uid, tid)


def list_messages(clerk_user_id: str, thread_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
    uid = clerk_user_id.strip()
    tid = thread_id.strip()
    if not uid or not tid:
        return []
    cap = max(1, min(1000, int(limit)))
    conn = _get_conn()
    if not _thread_owned(conn, uid, tid):
        raise KeyError(tid)
    cur = conn.execute(
        """
        SELECT id, thread_id, role, content, meta_json, created_at
        FROM chat_messages
        WHERE thread_id = ?
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (tid, cap),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        meta: dict[str, Any] | None = None
        raw = r["meta_json"]
        if raw:
            try:
                meta = json.loads(str(raw))
            except json.JSONDecodeError:
                meta = None
        out.append(
            {
                "id": str(r["id"]),
                "thread_id": str(r["thread_id"]),
                "role": str(r["role"]),
                "content": str(r["content"]),
                "meta": meta,
                "created_at": str(r["created_at"]),
            }
        )
    return out
