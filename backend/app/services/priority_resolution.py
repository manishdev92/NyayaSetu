"""Priority when multiple legal facets appear — deterministic ordering."""

from __future__ import annotations

# Highest priority first (index 0 = wins composite cases).
PRIORITY_ORDER: list[str] = ["criminal", "cyber", "labour", "consumer", "traffic", "civil", "family", "unknown"]

_INDEX: dict[str, int] = {k: i for i, k in enumerate(PRIORITY_ORDER)}


def pick_primary_category(categories: list[str]) -> str:
    """Return the highest-priority category slug from a non-empty list."""
    if not categories:
        return "unknown"
    for p in PRIORITY_ORDER:
        if p in categories:
            return p
    return categories[0]


def split_primary_secondary(categories: list[str]) -> tuple[str, list[str]]:
    """PRIMARY = highest priority; SECONDARY = remaining unique slugs (ordered by priority)."""
    if not categories:
        return "unknown", []
    uniq: list[str] = []
    seen: set[str] = set()
    for c in sorted(categories, key=lambda x: _INDEX.get(x, 999)):
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    primary = pick_primary_category(uniq)
    rest = [x for x in uniq if x != primary]
    return primary, rest
