from __future__ import annotations

from app.ai.llm_intent_engine import classify_intent_pipeline
from app.services.clarification_followup import inject_classification_hints, parse_followup_signals
from app.services.clarification_structured_llm import rule_based_structured_fallback


def test_parse_comma_separated_additional_details_line() -> None:
    text = "Land issue\n\nAdditional details:\nForce/threat involved, Documents: Yes"
    sig = parse_followup_signals(text)
    assert sig.force_or_threat_yes is True
    assert sig.documents_yes is True


def test_parse_followup_force_and_documents() -> None:
    text = (
        "Land dispute\n\n"
        "Additional details (structured):\n"
        "Force/threat: Yes, Documents: Yes"
    )
    sig = parse_followup_signals(text)
    assert sig.force_or_threat_yes is True
    assert sig.documents_yes is True


def test_parse_no_force_disables_hybrid_signal() -> None:
    text = "Issue\n\nAdditional details (structured):\nForce/threat: No, Documents: Yes"
    sig = parse_followup_signals(text)
    assert sig.no_force_peaceful is True
    assert sig.documents_yes is True


def test_inject_classification_hints_appends_tokens() -> None:
    t = "x\n\nAdditional details (structured):\nForce/threat: Yes"
    out = inject_classification_hints(t)
    assert "nyayasetu_signal_force_or_threat_reported" in out


def test_rule_based_structured_fallback_two_points() -> None:
    q, pts = rule_based_structured_fallback("something vague about my boundary")
    assert len(pts) == 2
    assert all(len(p["options"]) <= 3 for p in pts)
    assert len(pts[0]["label"]) > 0


def test_structured_followup_boosts_classification_confidence() -> None:
    base = "property dispute neighbour occupying side of plot"
    follow = (
        f"{base}\n\n"
        "Additional details (structured):\n"
        "Documents: Yes, Force/threat: No"
    )
    _, _, meta1 = classify_intent_pipeline(base, city=None)
    _, _, meta2 = classify_intent_pipeline(follow, city=None)
    assert float(meta2.get("confidence") or 0) >= float(meta1.get("confidence") or 0)
