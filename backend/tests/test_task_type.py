"""P2: task_type on generate (schema, prompt addon, API → service)."""

from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.api.v1.generate_schemas import GenerateRequest
from app.config import settings
from app.main import app
from app.i18n_response_strings import stream_phase_preparing, stream_phase_preparing_for_task
from app.services.ai_service import (
    _document_looks_like_sho_fir_complaint_letter,
    _effective_consumer_formatter_task_type,
    _mismatch_sho_fir_for_consumer_draft,
    _normalize_task_type,
    _pasted_fir_letter_with_consumer_shopping_facts,
    _task_type_formatter_addon,
    _user_text_seeks_consumer_commission_filing,
    apply_consumer_complaint_routing_override,
    prefetch_intent,
)
from app.services.legal_taxonomy import LegalClassification
from app.core.legal_classifier import ClassifierMeta, classify_legal_issue
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
    assert "consumer commission" in _task_type_formatter_addon("consumer_complaint_filing").lower()
    assert _task_type_formatter_addon("draft_letter") == ""


def test_stream_phase_preparing_for_task_matches_draft_letter() -> None:
    assert stream_phase_preparing_for_task("en", "draft_letter") == stream_phase_preparing("en")


def test_stream_phase_preparing_for_task_distinguishes_modes() -> None:
    s = stream_phase_preparing_for_task
    assert "Q&A" in s("en", "qa_only")
    assert "short direct" in s("en", "draft_with_qa")
    assert "consumer" in s("en", "consumer_complaint_filing").lower()


def test_ecommerce_defective_phone_is_consumer_not_cyber() -> None:
    text = (
        "I bought a phone online; delivery was 20 days late and the phone's battery is defective. "
        "Seller is refusing return. Consumer complaint. Amount 45000."
    )
    _lc, meta = classify_legal_issue(text, entities=None, location=None)
    assert str(meta.get("router_intent")) == "consumer_issue"
    assert str(meta.get("category")) == "consumer"


def test_website_order_defect_routes_consumer_without_online_keyword() -> None:
    text = (
        "I placed an order on the website for a mobile. The battery is defective. Seller refuses warranty refund. "
        "Amount ₹45,000."
    )
    _lc, meta = classify_legal_issue(text, entities=None, location=None)
    assert str(meta.get("router_intent")) == "consumer_issue"
    assert str(_lc.get("issue_type")) == "consumer"


def test_apply_consumer_override_realigns_from_cyber() -> None:
    from app.services.legal_taxonomy import LegalClassification

    meta = cast(
        ClassifierMeta,
        {
            "domain": "cyber",
            "sub_type": "cybercrime_general",
            "category": "criminal",
            "fine_intent": "cybercrime",
            "router_intent": "cyber_fraud",
            "confidence": 0.94,
            "confidence_score": 0.94,
        },
    )
    tax: LegalClassification = {
        "issue_type": "cyber",
        "severity": "high",
        "jurisdiction_type": "national",
        "sub_type": "cybercrime_general",
    }
    t2, m2, ovr = apply_consumer_complaint_routing_override(
        "defective product online", "consumer_complaint_filing", tax, meta
    )
    assert ovr is True
    assert m2["router_intent"] == "consumer_issue"
    assert t2["issue_type"] == "consumer"


def test_prefetch_respects_task_type_consumer_filing() -> None:
    p = prefetch_intent(
        "Bought online; item defective; refund denied.",
        None,
        "consumer_complaint_filing",
    )
    assert str(p.classifier_meta.get("router_intent")) == "consumer_issue"
    assert str(p.classifier_meta.get("domain")) == "consumer"


def test_prefetch_heuristic_consumer_complaint_phrase_without_task_type() -> None:
    p = prefetch_intent(
        "I bought a phone online; delivery late; battery defective. I want to file a consumer complaint. ₹45000.",
        None,
        "draft_letter",
    )
    assert str(p.classifier_meta.get("router_intent")) == "consumer_issue"
    assert str(p.classifier_meta.get("domain")) == "consumer"


def test_heuristic_recognises_complaint_not_just_complain() -> None:
    assert _user_text_seeks_consumer_commission_filing(
        "online order complaint, delivery late, defect under warranty. Seller refuses."
    )


def test_pasted_fir_sho_with_online_purchase_triggers_consumer() -> None:
    blob = (
        "To,\nThe Station House Officer,\nThe police station having territorial jurisdiction"
        " over the area where the incident described below occurred\n"
        "Subject: Information for registration of FIR\n"
        "I wish to place on record a complaint. I made an online purchase, amount ₹45,000, "
        "defect in phone, seller online refuses return."
    )
    assert _pasted_fir_letter_with_consumer_shopping_facts(blob) is True
    from app.services.legal_taxonomy import LegalClassification

    m = cast(
        ClassifierMeta,
        {
            "domain": "criminal",
            "sub_type": "x",
            "category": "criminal",
            "fine_intent": "x",
            "router_intent": "criminal_police",
            "confidence": 0.5,
            "confidence_score": 0.5,
        },
    )
    t: LegalClassification = {
        "issue_type": "police",
        "severity": "medium",
        "jurisdiction_type": "district",
        "sub_type": "x",
    }
    t2, m2, ovr = apply_consumer_complaint_routing_override(blob, "draft_letter", t, m)
    assert ovr is True
    assert t2["issue_type"] == "consumer"
    assert m2.get("category") == "consumer"


def test_effective_task_type_favours_commission_for_consumer_draft_letter() -> None:
    assert (
        _effective_consumer_formatter_task_type("short", "draft_letter", category="consumer")
        == "consumer_complaint_filing"
    )
    assert _effective_consumer_formatter_task_type("short", "qa_only", category="consumer") == "qa_only"


def test_sho_mismatch_triggers_for_consumer_routing() -> None:
    sho_doc = "To,\nThe Station House Officer,\nThe police station having\nSubject: Information for registration of FIR\ndefective phone"
    u = "phone online, defective, ₹45,000, seller no refund"
    tui: LegalClassification = {
        "issue_type": "consumer",
        "severity": "medium",
        "jurisdiction_type": "state",
        "sub_type": "defective_product",
    }
    meta: ClassifierMeta = cast(
        ClassifierMeta,
        {
            "domain": "consumer",
            "sub_type": "defective_product",
            "category": "consumer",
            "fine_intent": "consumer_issue",
            "router_intent": "consumer_issue",
            "confidence": 0.9,
            "confidence_score": 0.9,
        },
    )
    assert _document_looks_like_sho_fir_complaint_letter(sho_doc) is True
    assert _mismatch_sho_fir_for_consumer_draft(u, "draft_letter", sho_doc, classifier_meta=meta, taxonomy_ui=tui) is True


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
