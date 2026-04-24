from __future__ import annotations

from app.services.emergency_intelligence import resolver
from app.services.emergency_intelligence.resolver import (
    fetch_emergency_reference_links,
    registry_disclaimer,
    resolve_emergency_contacts,
)


def test_registry_has_disclaimer() -> None:
    d = registry_disclaimer()
    assert len(d) > 20


def test_resolve_police_and_cyber() -> None:
    rows = resolve_emergency_contacts(
        categories_needed=["unified_emergency", "police", "cybercrime"],
        state_label="Delhi",
        city_label="New Delhi",
    )
    cats = {r["category"] for r in rows}
    assert "unified_emergency" in cats
    assert "cybercrime" in cats
    nums = [n for r in rows for n in r.get("numbers", [])]
    assert "112" in nums
    assert "1930" in nums


def test_fetch_reference_links_uses_dict_candidates(monkeypatch) -> None:
    """Tavily returns AuthorityCandidate as dict (TypedDict) — must not use .url attribute access."""

    def fake_tavily(_q: str) -> list[dict[str, str]]:
        return [
            {
                "name": "MHA — emergency number",
                "url": "https://www.mha.gov.in/somepage",
                "source": "tavily",
            }
        ]

    monkeypatch.setattr(resolver, "search_tavily", fake_tavily)
    monkeypatch.setattr(resolver.settings, "tavily_api_key", "test-key", raising=False)
    out = fetch_emergency_reference_links(
        state_label="Uttar Pradesh",
        city_label="Mau",
        categories_needed=["unified_emergency"],
    )
    assert len(out) >= 1
    assert out[0]["url"].endswith("gov.in/somepage")
