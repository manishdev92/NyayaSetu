"""
Phase 6: highest-authority law-and-order / safety signals (violence, threat, weapons, Hindi cues).

Runs before routing merges; complements legal_priority_engine (P0–P2).
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from app.core.legal_classifier import ClassifierMeta
from app.services.emergency_detector import detect_emergency_layer
from app.services.police_station_incident_cues import alleges_arson_or_fire_at_police_station

VIOLENCE_KEYWORDS_EN = (
    "fight",
    "marpit",
    "attack",
    "assault",
    "beating",
    "threat",
    "gun",
    "knife",
)

HINDI_KEYWORDS = (
    "मारपीट",
    "लड़ाई",
    "धमकी",
    "हमला",
    "झगड़ा",
    "झगडा",
)
# Note: कब्ज़ा / encroachment alone is handled by hybrid_case_routing + legal_priority (P2), not law_and_order.


class LawAndOrderPriority(TypedDict):
    priority: str
    urgency: str
    override: bool
    primary_forum: str
    is_emergency: bool


def infer_emergency_triple_confirmed(text: str) -> bool:
    """
    True when the user affirms all three: ongoing situation, injury, police help.
    Supports free text and simple 'ongoing: yes' style lines.
    """
    low = (text or "").strip().lower()
    if not low:
        return False
    ongoing_yes = bool(
        re.search(
            r"(?:\bongoing\b|\bhappening\s+now\b|\bright\s+now\b|\bstill\s+going\b).{0,100}?\b(yes|yep|yeah|y\b|haan|हाँ)\b",
            low,
            re.I,
        )
    ) or bool(re.search(r"\bongoing\s*[:=]\s*yes\b", low))
    injury_yes = (
        bool(
            re.search(
                r"(?:\binjur|\bhurt\b|\bharm\b|\bbleeding\b|\bmedical\b).{0,100}?\b(yes|yep|yeah|y\b|haan|हाँ)\b",
                low,
                re.I,
            )
        )
        or bool(re.search(r"\binjury\b.{0,60}?\b(yes|yep|yeah|y\b|haan)\b", low, re.I))
        or bool(re.search(r"\bis\s+anyone\s+injured\b.{0,60}?\b(yes|yep|yeah|y\b|haan)\b", low, re.I))
    )
    police_yes = bool(
        re.search(
            r"(?:\bpolice\s+help\b|\bneed\s+police\b|\bpolice\s+immediately\b|\bcall\s+112\b|\bdial\s+112\b).{0,100}?"
            r"\b(yes|yep|yeah|y\b|haan|हाँ|immediately|right\s+away)\b",
            low,
            re.I,
        )
    ) or bool(re.search(r"\bpolice\b.{0,60}?\b(yes|immediately|right\s+away|urgent)\b", low, re.I))
    return ongoing_yes and injury_yes and police_yes


def detect_law_and_order_priority(text: str) -> LawAndOrderPriority:
    """
    Detect immediate law-and-order risk from plain text (English + Hindi tokens).
    """
    raw = (text or "").strip()
    if not raw:
        return LawAndOrderPriority(
            priority="normal",
            urgency="normal",
            override=False,
            primary_forum="",
            is_emergency=False,
        )
    low = raw.lower()
    hit_en = any(k in low for k in VIOLENCE_KEYWORDS_EN)
    hit_hi = any(k in raw for k in HINDI_KEYWORDS)
    # Word-boundary-ish for short English tokens that appear inside other words
    if not hit_en:
        hit_en = bool(
            re.search(
                r"\b(fight|fighting|marpit|attack|assault|beating|threat|threats|"
                r"gun|knife|riot|mob|violence|violent)\b",
                low,
                re.I,
            )
        )
    if alleges_arson_or_fire_at_police_station(raw):
        return LawAndOrderPriority(
            priority="law_and_order",
            urgency="high",
            override=True,
            primary_forum="police",
            is_emergency=bool(
                infer_emergency_triple_confirmed(raw)
                or bool(re.search(r"\b(ongoing|right\s+now|happening\s+now|still|today)\b", low))
            ),
        )
    if hit_en or hit_hi:
        return LawAndOrderPriority(
            priority="law_and_order",
            urgency="high",
            override=True,
            primary_forum="police",
            is_emergency=infer_emergency_triple_confirmed(raw),
        )
    return LawAndOrderPriority(
        priority="normal",
        urgency="normal",
        override=False,
        primary_forum="",
        is_emergency=False,
    )


def enrich_classifier_meta_with_priority(text: str, meta: ClassifierMeta) -> ClassifierMeta:
    """Attach Phase 6 priority snapshot to classifier meta (immutable merge)."""
    pe = detect_law_and_order_priority(text)
    layer = detect_emergency_layer(text)
    is_emergency = bool(pe.get("is_emergency")) or bool(layer.get("bypass_recommended"))
    out: dict[str, Any] = {**meta}
    out["phase6_priority"] = pe["priority"]
    out["phase6_urgency"] = pe["urgency"]
    out["phase6_priority_override"] = pe["override"]
    out["phase6_primary_forum"] = pe["primary_forum"]
    out["is_emergency"] = is_emergency
    out["emergency_layer"] = dict(layer)
    return out  # type: ignore[return-value]
