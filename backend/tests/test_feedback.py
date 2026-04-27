"""P8-02 — `/feedback/response` endpoint persistence and validation."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.response_feedback_store import (
    count_feedback_for_tests,
    reset_response_feedback_store_for_tests,
)


@pytest.fixture(autouse=True)
def _feedback_db(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    db = tmp_path / f"feedback_{uuid.uuid4().hex}.sqlite"
    monkeypatch.setattr(settings, "feedback_db_path", str(db), raising=False)
    reset_response_feedback_store_for_tests()
    yield
    reset_response_feedback_store_for_tests()


def test_feedback_response_accepts_anonymous() -> None:
    c = TestClient(app)
    r = c.post(
        "/feedback/response",
        json={
            "helpful": True,
            "client_mode": "citizen",
            "task_type": "draft_letter",
            "locale": "en",
            "generation_mode": "normal",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    assert isinstance(r.json().get("id"), str)
    assert count_feedback_for_tests() == 1


def test_feedback_response_accepts_user_header() -> None:
    c = TestClient(app)
    r = c.post(
        "/feedback/response",
        headers={"X-User-Id": "clerk_feedback_1"},
        json={
            "helpful": False,
            "client_mode": "lawyer",
            "task_type": "qa_only",
            "locale": "hi",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    assert count_feedback_for_tests() == 1


def test_feedback_response_rejects_invalid_mode() -> None:
    c = TestClient(app)
    r = c.post(
        "/feedback/response",
        json={
            "helpful": True,
            "client_mode": "admin",
            "task_type": "draft_letter",
        },
    )
    assert r.status_code == 400
    d = r.json().get("detail", {})
    assert d.get("error_code") == "feedback_invalid_payload"
    assert count_feedback_for_tests() == 0


def test_feedback_summary_aggregates_counts() -> None:
    c = TestClient(app)
    c.post(
        "/feedback/response",
        json={"helpful": True, "client_mode": "citizen", "task_type": "draft_letter"},
    )
    c.post(
        "/feedback/response",
        json={"helpful": False, "client_mode": "lawyer", "task_type": "qa_only"},
    )
    c.post(
        "/feedback/response",
        json={"helpful": True, "client_mode": "lawyer", "task_type": "qa_only"},
    )
    r = c.get("/feedback/summary?days=30")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["days"] == 30
    assert d["total"] == 3
    assert d["positive"] == 2
    assert d["positive_rate"] > 0.6
    assert isinstance(d["by_mode"], list)
    assert isinstance(d["by_task_type"], list)
    assert isinstance(d["by_day"], list)
    assert len(d["by_day"]) == 30
    assert sum(int(x["total"]) for x in d["by_day"]) == 3

