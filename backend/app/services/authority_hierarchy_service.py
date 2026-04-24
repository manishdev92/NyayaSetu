from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.authority import district_label_from_city_key, state_for_city_key
from app.legal_ui_copy import localize_hierarchy_step
from app.services.authority_service import get_local_authority, resolve_city_key

_HIERARCHY_PATH = Path(__file__).resolve().parent.parent / "core" / "authority_hierarchy.json"


@lru_cache
def _load_templates() -> dict[str, Any]:
    with _HIERARCHY_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)
    return raw if isinstance(raw, dict) else {}


def _location_tokens(city: str | None) -> tuple[str, str]:
    """Deterministic district/state labels for template substitution only."""
    ck = resolve_city_key(city)
    dist = district_label_from_city_key(ck)
    st = state_for_city_key(ck)
    if dist and st:
        return dist, f"{dist}, {st}"
    if dist:
        return dist, dist
    return "", "your area (confirm on official .gov.in portals)"


def build_authority_hierarchy(
    router_intent: str | None,
    city: str | None,
    response_language: str = "en",
) -> list[dict[str, Any]]:
    """
    Build a structured escalation path from static templates + optional JSON directory rows.

    Safety: no LLM calls; office names only when present in authorities.json via get_local_authority.
    """
    templates = _load_templates()
    key = str(router_intent or "").strip()
    router_key_resolved = key
    block = templates.get(key)
    if not isinstance(block, dict):
        block = templates.get("general_issue") or {}
        router_key_resolved = "general_issue"
    steps_raw = block.get("steps") if isinstance(block, dict) else None
    if not isinstance(steps_raw, list) or not steps_raw:
        return []

    district_short, district_display = _location_tokens(city)
    city_str = str(city).strip() if city else ""

    out: list[dict[str, Any]] = []
    for raw in steps_raw:
        if not isinstance(raw, dict):
            continue
        try:
            order = int(raw.get("order", 0))
        except (TypeError, ValueError):
            order = 0
        label = str(raw.get("label") or "").strip()
        tmpl = str(raw.get("description_template") or "").strip()
        dept_key = raw.get("department_key")
        department_key = str(dept_key).strip() if isinstance(dept_key, str) and dept_key.strip() else None

        desc = tmpl.replace("{district}", district_display)
        label, desc = localize_hierarchy_step(
            router_key_resolved,
            order,
            label,
            desc,
            district_display,
            response_language,
        )
        verified = False
        office_name: str | None = None
        source = "template"

        if department_key and city_str:
            rec = get_local_authority(city_str, department_key)
            if rec and rec.get("found") and rec.get("name"):
                verified = True
                office_name = str(rec["name"]).strip() or None
                source = "directory"

        out.append(
            {
                "order": order,
                "label": label,
                "description": desc,
                "verified": verified,
                "office_name": office_name,
                "department_key": department_key,
                "source": source,
                "district_label": district_short or None,
            }
        )

    out.sort(key=lambda x: (x.get("order") is None, x.get("order") or 0))
    return out
