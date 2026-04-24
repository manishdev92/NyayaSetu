"""
Highest-priority emergency text layer (before normal legal drafting).

Complements `infer_emergency_triple_confirmed` (structured yes/no) with direct
natural-language signals: ongoing harm, communal violence, injury accidents.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from app.services.police_station_incident_cues import alleges_arson_or_fire_at_police_station


class EmergencyLayerResult(TypedDict):
    bypass_recommended: bool
    triggers: list[str]
    categories: list[str]


def detect_emergency_layer(text: str) -> EmergencyLayerResult:
    raw = (text or "").strip()
    low = raw.lower()
    triggers: list[str] = []
    categories: list[str] = []
    if not low:
        return EmergencyLayerResult(bypass_recommended=False, triggers=[], categories=[])

    ongoing = bool(
        re.search(
            r"\b(happening\s+now|right\s+now|still\s+going|currently\s+happening|ongoing)\b",
            low,
        )
    ) or bool(re.search(r"\bongoing\s*[:=]\s*yes\b", low))
    injury = bool(
        re.search(
            r"\b(injured|injuries|injury|bleeding|wounded|unconscious|"
            r"ambulance|hospital\s+now|need\s+doctor|critically)\b",
            low,
        )
    )
    violence = bool(
        re.search(
            r"\b(fight|fighting|brawl|riot|mob|assault|attack|beating|beaten|"
            r"violence|violent|marpit|jhagda|communal\s+clash|clash|stone\s+pelting)\b",
            low,
        )
    )
    communal = bool(re.search(r"\b(communal|two\s+religions?|religious\s+riot)\b", low)) and (
        violence or ongoing
    )
    accident = bool(re.search(r"\b(accident|crash|collision|vehicle\s+overturned)\b", low))
    fire = bool(re.search(r"\b(fire|blaze|burning\s+building|smoke\s+everywhere)\b", low))
    medical = bool(re.search(r"\b(heart\s+attack|stroke|can'?t\s+breathe|choking|poisoning)\b", low))

    bypass = False
    if communal:
        bypass = True
        triggers.append("communal_or_group_violence")
        categories.extend(["police", "unified_emergency", "ambulance"])
    if ongoing and violence:
        bypass = True
        triggers.append("ongoing_violence")
        for c in ("police", "unified_emergency"):
            if c not in categories:
                categories.append(c)
        if injury and "ambulance" not in categories:
            categories.append("ambulance")
    if ongoing and injury and not bypass:
        bypass = True
        triggers.append("ongoing_medical_harm")
        for c in ("unified_emergency", "ambulance"):
            if c not in categories:
                categories.append(c)
    if accident and injury:
        bypass = True
        triggers.append("accident_with_injury")
        for c in ("unified_emergency", "ambulance", "police"):
            if c not in categories:
                categories.append(c)
    if fire and (ongoing or injury or bool(re.search(r"\btrapped\b", low))):
        bypass = True
        triggers.append("fire_emergency")
        for c in ("fire", "unified_emergency"):
            if c not in categories:
                categories.append(c)
    if medical and ongoing:
        bypass = True
        triggers.append("medical_emergency")
        for c in ("unified_emergency", "ambulance"):
            if c not in categories:
                categories.append(c)

    # De-dupe preserve order
    seen: set[str] = set()
    cat_out: list[str] = []
    for c in categories:
        if c not in seen:
            seen.add(c)
            cat_out.append(c)

    return EmergencyLayerResult(
        bypass_recommended=bypass,
        triggers=list(dict.fromkeys(triggers)),
        categories=cat_out,
    )


def emergency_categories_for_issue(
    *,
    user_input: str,
    classifier_domain: str,
    classifier_category: str,
    issue_type: str,
    fine_intent: str,
    sub_type: str = "",
    severity: str = "",
    layer: EmergencyLayerResult,
) -> list[str]:
    """Merge detector categories with issue-based helplines (cyber, women/child, etc.)."""
    _ = classifier_category
    low = (user_input or "").lower()
    dom = str(classifier_domain or "").lower()
    it = str(issue_type or "").lower()
    fi = str(fine_intent or "")
    st = str(sub_type or "")
    sev = str(severity or "").lower()
    out: list[str] = list(layer.get("categories") or [])

    if it == "cyber" or dom == "cyber" or ("fraud" in low and "online" in low):
        if "cybercrime" not in out:
            out.append("cybercrime")
    if it == "women_child" or dom == "women_child":
        if "women_safety" not in out:
            out.append("women_safety")
        if "child_protection" not in out and bool(re.search(r"\b(child|minor|school\s+kid)\b", low)):
            out.append("child_protection")
    if fi in ("sexual_offence", "women_child") or st in ("sexual_offence", "harassment", "abuse"):
        if "women_safety" not in out:
            out.append("women_safety")
    if bool(re.search(r"\b(harass|molest|outrage\s+modesty|woman|women|girl)\b", low)):
        if "women_safety" not in out:
            out.append("women_safety")
    if bool(re.search(r"\b(traffick|trafficked|forced\s+labour\s+abroad)\b", low)):
        if "human_trafficking" not in out:
            out.append("human_trafficking")
    if bool(re.search(r"\b(flood|earthquake|cyclone|landslide|tsunami)\b", low)):
        if "disaster" not in out:
            out.append("disaster")

    # Vehicle/property theft and other cognizable high-priority police routes: surface 112 / 100 in registry UI.
    if fi == "theft" or st in ("theft", "stolen_vehicle") or bool(
        re.search(r"\b(stolen|theft|chori|चोरी|snatched?|snatching|robbed|burglar)\b", low)
    ):
        for c in ("unified_emergency", "police"):
            if c not in out:
                out.append(c)
    if sev == "high" and it in ("police", "police_oversight") and dom in ("criminal", "police_complaint", "cyber", "general"):
        for c in ("unified_emergency", "police"):
            if c not in out:
                out.append(c)
    if alleges_arson_or_fire_at_police_station(user_input):
        for c in ("unified_emergency", "police", "fire", "ambulance"):
            if c not in out:
                out.append(c)

    if layer.get("bypass_recommended") and "unified_emergency" not in out:
        out.insert(0, "unified_emergency")

    seen: set[str] = set()
    merged: list[str] = []
    for c in out:
        if c not in seen:
            seen.add(c)
            merged.append(c)
    return merged
