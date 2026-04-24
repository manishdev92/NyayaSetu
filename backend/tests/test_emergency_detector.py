from __future__ import annotations

from app.services.emergency_detector import detect_emergency_layer, emergency_categories_for_issue


def test_layer_communal_bypass() -> None:
    out = detect_emergency_layer("communal clash happening now between groups")
    assert out["bypass_recommended"] is True
    assert "communal_or_group_violence" in out["triggers"]


def test_layer_accident_injury() -> None:
    out = detect_emergency_layer("road accident people injured need ambulance")
    assert out["bypass_recommended"] is True
    assert "accident_with_injury" in out["triggers"]


def test_layer_no_false_positive_past_injury() -> None:
    out = detect_emergency_layer("I had a minor injury last year at work")
    assert out["bypass_recommended"] is False


def test_emergency_categories_adds_cyber() -> None:
    layer = detect_emergency_layer("someone used my card online")
    cats = emergency_categories_for_issue(
        user_input="online fraud on my card",
        classifier_domain="cyber",
        classifier_category="criminal",
        issue_type="cyber",
        fine_intent="cybercrime",
        severity="high",
        layer=layer,
    )
    assert "cybercrime" in cats


def test_emergency_categories_theft_adds_112_police() -> None:
    layer = detect_emergency_layer("my car is fine")
    cats = emergency_categories_for_issue(
        user_input="someone stolen my car from ratanpura",
        classifier_domain="criminal",
        classifier_category="criminal",
        issue_type="police",
        fine_intent="theft",
        sub_type="theft",
        severity="high",
        layer=layer,
    )
    assert "unified_emergency" in cats
    assert "police" in cats
