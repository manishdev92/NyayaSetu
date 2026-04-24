from __future__ import annotations


def build_issue_keywords(department: str) -> str:
    m = {
        "labour": "labour department labour office labour commissioner",
        "land": "land records revenue department tehsildar",
        "rental": "rent control tenancy rent authority civil court",
        "police": "police station SHO FIR jurisdiction district police",
        "cyber": "cyber crime cell cyber police national cyber crime reporting portal",
        "other": "district administration government office",
    }
    return m.get(department, m["other"])


def build_queries(city: str | None, department: str, user_input: str) -> dict[str, str]:
    """Named queries for each search channel."""
    city_part = (city or "").strip() or "India"
    kw = build_issue_keywords(department)
    short = f"{kw} {city_part}"
    gov = f"(site:gov.in OR site:nic.in) {kw} {city_part}"
    context = user_input.strip()[:120]
    return {
        "main": short,
        "gov_in": gov,
        "context": f"{short} {context}",
    }
