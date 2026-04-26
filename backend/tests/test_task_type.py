"""P2: task_type on generate (schema, prompt addon, API → service)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.generate_schemas import GenerateRequest
from app.config import settings
from app.main import app
from app.services.ai_service import _normalize_task_type, _task_type_formatter_addon
from app.services.usage_limit import UsageSnapshot


def test_generate_request_task_type_default() -> None:
    g = GenerateRequest.model_validate({"user_input": "help with rent"})
    assert g.task_type == "draft_letter"


def test_generate_request_task_type_values() -> None:
    g = GenerateRequest.model_validate({"user_input": "x", "task_type": "qa_only"})
    assert g.task_type == "qa_only"
    g2 = GenerateRequest.model_validate({"user_input": "x", "task_type": "consumer_complaint_filing"})
    assert g2.task_type == "consumer_complaint_filing"


def test_normalize_task_type() -> None:
    assert _normalize_task_type(None) == "draft_letter"
    assert _normalize_task_type("  QA_ONLY  ") == "qa_only"
    assert _normalize_task_type("nope") == "draft_letter"


def test_task_type_formatter_addon_branches() -> None:
    assert "TASK_TYPE" in _task_type_formatter_addon("qa_only")
    assert "directly answer" in _task_type_formatter_addon("draft_with_qa").lower()
    assert "consumer complaint" in _task_type_formatter_addon("consumer_complaint_filing").lower()
    assert _task_type_formatter_addon("draft_letter") == ""


def test_generate_accepts_task_type_openai_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "unpaid wages", "task_type": "qa_only"},
    )
    assert r.status_code == 503
    assert r.json()["detail"].get("error_code") == "generate_openai_unconfigured"


def test_generate_passes_task_type_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    cap: dict[str, object] = {}
    snap = UsageSnapshot(used=0, limit=100, remaining=100, reset_at_utc="2099-01-01T00:00:00Z")

    def fake(
        _user: str,
        _details: object | None = None,
        *,
        task_type: str = "draft_letter",
        **kwargs: object,
    ) -> dict[str, object]:
        cap["task_type"] = task_type
        return {
            "document": "d",
            "explanation": "e",
            "next_steps": ["one"],
            "clarification_needed": False,
            "authority": None,
            "authority_disclaimer": "ad",
            "task_type": task_type,
        }

    monkeypatch.setattr("app.api.v1.generate.consume_request", lambda **kw: (True, snap))
    monkeypatch.setattr("app.api.v1.generate.http_rate_limit_headers", lambda s: {})
    monkeypatch.setattr("app.api.v1.generate.generate_legal_response", fake)
    r = TestClient(app).post(
        "/generate",
        json={"user_input": "tenant not returning deposit", "task_type": "draft_with_qa"},
    )
    assert r.status_code == 200
    assert cap.get("task_type") == "draft_with_qa"
    body = r.json()
    assert body.get("task_type") == "draft_with_qa"
