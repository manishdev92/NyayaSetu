"""
Priority-of-harm overrides: higher-risk signals override lower-priority routing (never keyword-only).

P0 > P1 > P2 > … — applied after deterministic + LLM fallback classification.
"""

from __future__ import annotations

import re
from typing import Tuple

from app.core.legal_classifier import ClassifierMeta
from app.services.legal_taxonomy import LegalClassification
from app.services.police_station_incident_cues import alleges_arson_or_fire_at_police_station

VIOLENCE_CUES = re.compile(
    r"\b(fight|fighting|beating|beaten|attack|violence|violent|clash|riot|mob|marpit|mar\s*pit|"
    r"jhagda|jhagada|assault|brawl|lathi)\b",
    re.I,
)

CRIMINAL_CUES = re.compile(
    r"\b(stolen|stole|stealing|theft|chori|चोरी|fraud|cheated|cheating|coercion|coerced|blackmail|extortion|"
    r"threats?|threatened|threatening|intimidation|intimidated|force|forced|forcible|trespass|snatched|robbed)\b",
    re.I,
)

LAND_CUES = re.compile(
    r"\b(land|plot|property|zameen|jameen|khasra|khatoni|kabza|kabja|qabza|encroachment|boundary|possession)\b",
    re.I,
)


def apply_priority_override(
    classification: LegalClassification,
    text: str,
    meta: ClassifierMeta,
) -> Tuple[LegalClassification, ClassifierMeta]:
    """
    Override lower-priority domains when higher harm signals are present.

    Returns new (LegalClassification, ClassifierMeta) dicts; leaves input unchanged when no override.
    """
    raw = (text or "").strip()
    if not raw:
        return classification, meta

    low = raw.lower()
    lc: LegalClassification = {**classification}
    m: ClassifierMeta = {**meta}

    # Strip prior run (idempotent re-entry)
    m.pop("is_priority_override", None)
    m.pop("priority_level", None)

    # --- P0a: arson / fire at police station (public infrastructure; always high priority) ---
    if alleges_arson_or_fire_at_police_station(raw):
        conf = max(float(m.get("confidence") or 0), float(m.get("confidence_score") or 0), 0.95)
        lc = {
            **lc,
            "issue_type": "police",
            "severity": "high",
            "sub_type": "arson_or_fire_at_police_station",
            "jurisdiction_type": "district",
        }
        m = {
            **m,
            "domain": "criminal",
            "category": "criminal",
            "fine_intent": "arson_public_building",
            "router_intent": "criminal_police",
            "confidence": conf,
            "confidence_score": conf,
            "is_hybrid": False,
            "is_priority_override": True,
            "priority_level": "P0",
        }
        m.pop("secondary_domain", None)
        return lc, m

    # --- P0: immediate violence / public-order style harm ---
    if VIOLENCE_CUES.search(low):
        conf = max(float(m.get("confidence") or 0), float(m.get("confidence_score") or 0), 0.9)
        lc = {
            **lc,
            "issue_type": "police",
            "severity": "high",
            "sub_type": "violent_dispute",
            "jurisdiction_type": "district",
        }
        m = {
            **m,
            "domain": "police",
            "category": "criminal",
            "fine_intent": "assault_or_riot",
            "router_intent": "criminal_police",
            "confidence": conf,
            "confidence_score": conf,
            "is_hybrid": False,
            "is_priority_override": True,
            "priority_level": "P0",
        }
        m.pop("secondary_domain", None)
        return lc, m

    # --- P2: land + criminal cues (civil–criminal hybrid) before generic P1 ---
    land_hit = bool(LAND_CUES.search(low))
    criminal_hit = bool(CRIMINAL_CUES.search(low))
    if land_hit and criminal_hit:
        conf = max(float(m.get("confidence") or 0), float(m.get("confidence_score") or 0), 0.87)
        lc = {
            **lc,
            "issue_type": "civil_dispute",
            "severity": "high",
            "sub_type": "land_dispute",
            "jurisdiction_type": "district",
        }
        m = {
            **m,
            "domain": "civil",
            "category": "civil",
            "fine_intent": "property_civil",
            "router_intent": "civil_dispute",
            "confidence": conf,
            "confidence_score": conf,
            "is_hybrid": True,
            "secondary_domain": "criminal",
            "is_priority_override": True,
            "priority_level": "P2",
        }
        return lc, m

    # --- P1: criminal cues; skip if already on police / criminal police track ---
    if criminal_hit:
        ri = str(m.get("router_intent") or "")
        it = str(lc.get("issue_type") or "")
        if ri == "criminal_police" and it == "police":
            # Criminal cues + already on police track: normalize domain/router (classifier may still say e.g. cyber).
            conf = max(float(m.get("confidence") or 0), float(m.get("confidence_score") or 0), 0.88)
            m_out: ClassifierMeta = {
                **meta,
                "domain": "police",
                "category": "criminal",
                "router_intent": "criminal_police",
                "confidence": max(float(meta.get("confidence") or 0), conf),
                "confidence_score": max(float(meta.get("confidence_score") or 0), conf),
                "is_priority_override": True,
                "priority_level": "P1",
            }
            m_out.pop("secondary_domain", None)
            return classification, m_out
        conf = max(float(m.get("confidence") or 0), float(m.get("confidence_score") or 0), 0.88)
        lc = {
            **lc,
            "issue_type": "police",
            "severity": "high",
            "sub_type": "criminal_complaint",
            "jurisdiction_type": "district",
        }
        m = {
            **m,
            "domain": "police",
            "category": "criminal",
            "fine_intent": "criminal_complaint",
            "router_intent": "criminal_police",
            "confidence": conf,
            "confidence_score": conf,
            "is_hybrid": False,
            "is_priority_override": True,
            "priority_level": "P1",
        }
        m.pop("secondary_domain", None)
        return lc, m

    return classification, meta
