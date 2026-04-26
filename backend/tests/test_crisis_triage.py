from __future__ import annotations

from app.core.legal_classifier import classify_legal_issue
from app.services.crisis_triage import crisis_triage_lock
from app.services.hybrid_case_routing import apply_hybrid_civil_criminal_overlay


def test_crisis_lock_on_emergency_meta() -> None:
    lc, meta = classify_legal_issue("ongoing fight people injured call 112", None)
    lc, meta = apply_hybrid_civil_criminal_overlay("ongoing fight people injured call 112", lc, meta)
    assert crisis_triage_lock(meta, {**lc, "issue_type": lc["issue_type"]}) is True


def test_crisis_lock_sexual_offence() -> None:
    lc, meta = classify_legal_issue("I was molested at work", None)
    assert crisis_triage_lock(meta, {**lc, "issue_type": lc["issue_type"]}) is True


def test_crisis_lock_fired_up_thana_by_text() -> None:
    lc, meta = classify_legal_issue("someone fired up the police thana", None)
    assert (
        crisis_triage_lock(
            meta, {**lc, "issue_type": lc["issue_type"]}, user_input="someone fired up the police thana"
        )
        is True
    )


def test_crisis_lock_no_force_followup_prevents_false_police_triage() -> None:
    meta = {
        "is_emergency": False,
        "fine_intent": "land_dispute",
        "sub_type": "ownership_dispute",
        "domain": "civil",
        "phase6_priority": "law_and_order",
        "is_hybrid": True,
    }
    taxonomy = {"issue_type": "land", "severity": "high"}
    text = (
        "Land mutation dispute in Varanasi.\n"
        "Additional detail: Was there any threat, violence, or force involved in this dispute?: No"
    )
    assert crisis_triage_lock(meta, taxonomy, user_input=text) is False
