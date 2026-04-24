"""Legal priority-of-harm overrides and routing."""

from __future__ import annotations

import pytest

from app.ai.llm_intent_engine import classify_intent_pipeline
from app.services.legal_router import route_case


@pytest.mark.parametrize(
    "text,expect_priority,expect_router,expect_domain",
    [
        (
            "fight between two groups for land in my village",
            "P0",
            "criminal_police",
            "police",
        ),
        (
            "someone stole my phone yesterday",
            "P1",
            "criminal_police",
            "police",
        ),
        (
            "someone कब्ज़ा my land with threats and intimidation",
            "P2",
            "civil_dispute",
            "civil",
        ),
    ],
)
def test_priority_override_levels(
    text: str,
    expect_priority: str,
    expect_router: str,
    expect_domain: str,
) -> None:
    _interp, tax, meta = classify_intent_pipeline(text, city="Lucknow")
    assert meta.get("priority_level") == expect_priority
    assert meta.get("router_intent") == expect_router
    assert meta.get("domain") == expect_domain
    assert meta.get("is_priority_override") is True


def test_mutation_revenue_no_priority_override() -> None:
    _interp, _tax, meta = classify_intent_pipeline("mutation not done for my plot khasra 42", city="Agra")
    assert meta.get("priority_level") in (None, "")
    assert meta.get("is_priority_override") is not True


def test_fight_land_routes_police_not_tehsildar_primary() -> None:
    _interp, _tax, meta = classify_intent_pipeline(
        "fight between two groups for land boundary",
        city="Varanasi",
    )
    assert meta.get("phase6_priority") == "law_and_order"
    assert meta.get("hybrid_police_primary") is True
    rr = route_case(
        str(meta["router_intent"]),
        [],
        "Varanasi",
        category=str(meta.get("category") or ""),
        hybrid_civil_criminal=bool(meta.get("is_hybrid")),
        priority_level=str(meta.get("priority_level") or "").strip() or None,
        hybrid_police_primary=bool(meta.get("hybrid_police_primary")),
    )
    primary = rr["primary_authority"].lower()
    secondary = rr["secondary_authority"].lower()
    assert "police" in primary
    assert "tehsildar" not in primary
    assert "civil" in secondary


def test_p2_hybrid_router_civil_then_police() -> None:
    _interp, _tax, meta = classify_intent_pipeline(
        "neighbor did kabza on my plot with threats",
        city="Jaipur",
    )
    assert meta.get("priority_level") == "P2"
    rr = route_case(
        str(meta["router_intent"]),
        [],
        "Jaipur",
        category=str(meta.get("category") or ""),
        hybrid_civil_criminal=True,
        priority_level="P2",
    )
    assert "civil" in rr["primary_authority"].lower()
    assert "police" in rr["secondary_authority"].lower()
