"""Police inaction / follow-up after complaint — not acute crisis triage."""

from __future__ import annotations

from app.services.crisis_triage import (
    crisis_triage_lock,
    is_police_complaint_followup_escalation,
)


def test_detects_complaint_filed_no_action() -> None:
    t = (
        "I already filed a complaint in local police station but no action has been taken for 10 days."
    )
    assert is_police_complaint_followup_escalation(t) is True


def test_not_detected_fresh_fir_intent() -> None:
    t = "Someone stole my bike yesterday. I want to file an FIR at the police station."
    assert is_police_complaint_followup_escalation(t) is False


def test_crisis_triage_unlocks_for_followup_law_and_order() -> None:
    meta = {
        "is_emergency": False,
        "fine_intent": "theft",
        "sub_type": "theft",
        "domain": "criminal",
        "phase6_priority": "law_and_order",
        "is_hybrid": False,
    }
    taxonomy = {"issue_type": "police", "severity": "high"}
    text = "I filed a complaint at the police station; no action for 10 days."
    assert crisis_triage_lock(meta, taxonomy, user_input=text) is False
