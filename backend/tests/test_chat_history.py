"""Chat history SQLite API (threads + messages per Clerk user)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.chat_history_store import reset_chat_history_store_for_tests


@pytest.fixture(autouse=True)
def _chat_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_chat_history_store_for_tests()
    p = tmp_path / f"chat_{uuid.uuid4().hex}.sqlite"
    monkeypatch.setattr(settings, "chat_history_db_path", str(p), raising=False)
    reset_chat_history_store_for_tests()
    yield
    reset_chat_history_store_for_tests()


def test_chat_threads_require_user() -> None:
    r = TestClient(app).get("/chat/threads")
    assert r.status_code == 401


def test_chat_thread_crud_and_messages() -> None:
    uid = f"user_{uuid.uuid4().hex}"
    c = TestClient(app)

    r = c.post("/chat/threads", json={"title": "Hello"}, headers={"X-User-Id": uid})
    assert r.status_code == 200
    tid = r.json()["id"]
    assert len(tid) == 32

    r = c.get("/chat/threads", headers={"X-User-Id": uid})
    assert r.status_code == 200
    assert len(r.json()["threads"]) == 1

    r = c.post(
        f"/chat/threads/{tid}/messages",
        json={"role": "user", "content": "My issue"},
        headers={"X-User-Id": uid},
    )
    assert r.status_code == 200
    mid = r.json()["id"]
    assert mid

    r = c.get(f"/chat/threads/{tid}/messages", headers={"X-User-Id": uid})
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "My issue"

    r = c.post(
        f"/chat/threads/{tid}/messages",
        json={"role": "assistant", "content": "Reply text", "meta": {"k": 1}},
        headers={"X-User-Id": uid},
    )
    assert r.status_code == 200

    r = c.get(f"/chat/threads/{tid}/messages", headers={"X-User-Id": uid})
    msgs = r.json()["messages"]
    assert len(msgs) == 2
    assert msgs[1]["meta"] == {"k": 1}

    r = c.delete(f"/chat/threads/{tid}", headers={"X-User-Id": uid})
    assert r.status_code == 200

    r = c.get(f"/chat/threads/{tid}/messages", headers={"X-User-Id": uid})
    assert r.status_code == 404


def test_chat_other_user_cannot_post() -> None:
    uid1 = f"u_{uuid.uuid4().hex}"
    uid2 = f"u_{uuid.uuid4().hex}"
    c = TestClient(app)
    tid = c.post("/chat/threads", json={}, headers={"X-User-Id": uid1}).json()["id"]
    r = c.post(
        f"/chat/threads/{tid}/messages",
        json={"role": "user", "content": "x"},
        headers={"X-User-Id": uid2},
    )
    assert r.status_code == 404
