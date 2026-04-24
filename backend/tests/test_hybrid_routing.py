from __future__ import annotations

from app.ai.llm_fallback_classifier import deterministic_triggers_llm_fallback
from app.ai.llm_intent_engine import classify_intent_pipeline
from app.core.legal_classifier import classify_legal_issue
from app.services.hybrid_case_routing import apply_hybrid_civil_criminal_overlay, hybrid_criminal_cues_match
from app.services.legal_router import route_case


def test_hybrid_cues_match_hindi_kabza() -> None:
    assert hybrid_criminal_cues_match("someone forcefully कब्ज़ा my land")


def test_forceful_kabza_land_pipeline_civil_plus_criminal_flags() -> None:
    text = "someone forcefully कब्ज़ा my land"
    _, lc, meta = classify_intent_pipeline(text, city=None)
    assert meta.get("is_hybrid") is True
    assert meta.get("secondary_domain") == "criminal"
    assert meta.get("domain") == "civil"
    assert meta.get("router_intent") == "civil_dispute"
    assert lc.get("issue_type") == "civil_dispute"
    rr = route_case(
        str(meta.get("router_intent") or ""),
        [],
        "Varanasi",
        category=str(meta.get("category") or "civil"),
        hybrid_civil_criminal=True,
    )
    blob = (rr["primary_authority"] + rr["secondary_authority"]).lower()
    assert "civil court" in blob
    assert "police" in blob
    assert "tehsildar" not in rr["primary_authority"].lower()


def test_hybrid_blocks_llm_fallback_trigger() -> None:
    text = "someone forcefully कब्ज़ा my land"
    lc, meta = classify_legal_issue(text, [], None)
    lc2, meta2 = apply_hybrid_civil_criminal_overlay(text, lc, meta)
    assert meta2.get("is_hybrid") is True
    assert deterministic_triggers_llm_fallback(lc2, meta2) is False
