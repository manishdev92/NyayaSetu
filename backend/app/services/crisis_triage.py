"""
Crisis triage: hide RAG, long legal education, and escalation tree when user needs action-first
(emergency, serious crime signals, high-severity law-and-order, women/child high severity).
"""

from __future__ import annotations

import re
from typing import Any

from app.core.legal_classifier import ClassifierMeta
from app.services.clarification_followup import parse_followup_signals
from app.services.police_station_incident_cues import alleges_arson_or_fire_at_police_station


def _has_hard_emergency_signal(user_input: str) -> bool:
    low = str(user_input or "").strip().lower()
    if not low:
        return False
    return bool(
        re.search(
            r"\b("
            r"happening\s+now|right\s+now|ongoing|"
            r"injured|injury|bleeding|unconscious|critical|hospital\s+now|"
            r"gun|knife|armed|kidnap|abduct|"
            r"rape|sexual\s+assault|molested|"
            r"riot|mob|communal\s+clash|"
            r"fire|blaze|burning"
            r")\b",
            low,
        )
    )


def crisis_triage_lock(
    classifier_meta: ClassifierMeta,
    taxonomy_ui: dict[str, Any],
    *,
    user_input: str | None = None,
) -> bool:
    if user_input and alleges_arson_or_fire_at_police_station(user_input):
        return True
    if user_input:
        sig = parse_followup_signals(user_input)
        if sig.no_force_peaceful and not sig.force_or_threat_yes and not _has_hard_emergency_signal(user_input):
            # Clarification explicitly says no force/threat and no hard emergency markers: avoid false police-first triage.
            return False
    if bool(classifier_meta.get("is_emergency")):
        return True
    fi = str(classifier_meta.get("fine_intent") or "")
    st = str(classifier_meta.get("sub_type") or "")
    dom = str(classifier_meta.get("domain") or "")
    if fi in ("sexual_offence", "missing_person", "attempt_to_murder", "arson_public_building"):
        return True
    if st in ("sexual_offence", "missing_person", "attempt_to_murder", "assault", "arson_or_fire_at_police_station"):
        return True
    sev = str(taxonomy_ui.get("severity") or "")
    if str(classifier_meta.get("phase6_priority") or "") == "law_and_order" and sev == "high":
        return True
    if dom == "women_child" and sev == "high":
        return True
    if fi == "assault" and sev == "high":
        return True
    # Land + law-and-order hybrid: violence/force thread — keep UI and letter police-first, short.
    if bool(classifier_meta.get("is_hybrid")) and str(classifier_meta.get("phase6_priority") or "") == "law_and_order":
        return True
    return False
