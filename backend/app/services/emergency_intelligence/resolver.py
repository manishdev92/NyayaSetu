"""
Location-aware emergency contact resolution.

Numbers are served from a versioned local registry (with official source URLs),
optionally supplemented by search-backed *reference links* (not scraped numbers).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.search.tavily_client import search_tavily

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).resolve().with_name("registry.json")


@lru_cache(maxsize=1)
def _load_registry_cached() -> dict[str, Any]:
    try:
        with open(_REGISTRY_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to load emergency registry: %s", e)
        return {"national": [], "disclaimer": "", "states": {}}
    if not isinstance(data, dict):
        return {"national": [], "disclaimer": "", "states": {}}
    return data


def registry_disclaimer() -> str:
    reg = _load_registry_cached()
    return str(reg.get("disclaimer") or "").strip()


def resolve_emergency_contacts(
    *,
    categories_needed: list[str],
    state_label: str | None = None,
    city_label: str | None = None,
) -> list[dict[str, Any]]:
    """
    Map abstract categories to registry rows. State/city reserved for future
    state-scoped JSON overrides (`registry.json` → `states`).
    """
    _ = state_label, city_label  # future: merge state-specific rows
    reg = _load_registry_cached()
    national = reg.get("national")
    if not isinstance(national, list):
        return []
    by_cat: dict[str, dict[str, Any]] = {}
    for row in national:
        if isinstance(row, dict):
            cat = str(row.get("category") or "").strip()
            if cat:
                by_cat[cat] = row

    out: list[dict[str, Any]] = []
    seen_cat: set[str] = set()
    for cat in categories_needed:
        row = by_cat.get(cat)
        if not row:
            continue
        nums = row.get("numbers")
        num_list = [str(n).strip() for n in nums if str(n).strip()] if isinstance(nums, list) else []
        if cat in seen_cat:
            continue
        seen_cat.add(cat)
        out.append(
            {
                "category": cat,
                "label": str(row.get("label") or cat),
                "numbers": num_list,
                "notes": str(row.get("notes") or ""),
                "provenance": "cached_registry",
                "source_url": row.get("source_url"),
            }
        )
    return out


def fetch_emergency_reference_links(
    *,
    state_label: str | None,
    city_label: str | None,
    categories_needed: list[str] | None = None,
) -> list[dict[str, str]]:
    """
    Optional web search (Tavily) for official .gov.in pages — never treated as numeric truth.
    Returns curated links only; callers still use `resolve_emergency_contacts` for dial strings.
    """
    _ = categories_needed
    key = getattr(settings, "tavily_api_key", "") or ""
    if not str(key).strip():
        return []
    queries: list[str] = []
    loc = " ".join(p for p in (city_label or "", state_label or "") if p).strip()
    if loc:
        queries.append(f"site:gov.in {loc} emergency helpline police fire ambulance official")
    queries.append("site:gov.in national emergency number 112 MHA official")
    queries.append("site:gov.in NDMA helpline state disaster management official")
    out: list[dict[str, str]] = []
    seen_url: set[str] = set()
    for q in queries[:3]:
        try:
            cands = search_tavily(q)
        except Exception as e:
            logger.debug("Emergency link search skip: %s", e)
            continue
        for c in cands[:4]:
            if not isinstance(c, dict):
                continue
            url = (c.get("url") or "").strip()
            if not url or url.lower() in seen_url:
                continue
            if "gov.in" not in url.lower() and "nic.in" not in url.lower():
                continue
            seen_url.add(url.lower())
            out.append(
                {
                    "title": (c.get("name") or "Official resource")[:240],
                    "url": url,
                    "source": "tavily_search",
                }
            )
            if len(out) >= 8:
                return out
    return out
