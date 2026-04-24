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
