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


def is_police_complaint_followup_escalation(user_input: str | None) -> bool:
    """
    User already engaged police (complaint filed) and reports delay/inaction — escalation / oversight,
    not an acute “happening now” emergency. Suppresses crisis-style triage and generic ERSS blocks when True.

    Returns False if text suggests ongoing violence or sexual/offence victim priority (different handling).
    """
    low = str(user_input or "").strip().lower()
    if not low:
        return False
    if re.search(
        r"\b(molest|rape|sexual\s+assault|acid\s+attack|domestic\s+violence|"
        r"traffick|kidnap|abduct|stabbed|shot|beaten\s+now)\b",
        low,
    ):
        return False
    has_prior = bool(
        re.search(
            r"\b("
            r"already\s+filed|filed\s+a\s+complaint|complaint\s+filed|registered\s+a\s+complaint|"
            r"complaint\s+at\s+(the\s+)?(local\s+)?police|complaint\s+to\s+police|police\s+complaint|"
            r"reported\s+to\s+(the\s+)?police|went\s+to\s+(the\s+)?police\s+station|"
            r"submitted\s+(at|to)\s+(the\s+)?police|gave\s+complaint"
            r")\b",
            low,
        )
    )
    has_inaction = bool(
        re.search(
            r"\b("
            r"no\s+action|no\s+response|nothing\s+done|not\s+taken|ignored|"
            r"delay|delayed|not\s+registered|did\s+not\s+register|refused\s+to\s+register|"
            r"for\s+\d+\s+days?|since\s+\d+|past\s+\d+\s+days?|"
            r"still\s+waiting|waiting\s+for|has\s+not\s+been|have\s+not\s+taken"
            r")\b",
            low,
        )
    )
    police_ctx = bool(re.search(r"\b(police|station|than[ea]|chowki|fir|complaint)\b", low))
    return bool(has_prior and has_inaction and police_ctx)


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
    # Complaint already filed + police inaction/delay → oversight / escalation, not acute crisis UI.
    if user_input and is_police_complaint_followup_escalation(user_input) and not _has_hard_emergency_signal(
        user_input
    ):
        fi = str(classifier_meta.get("fine_intent") or "")
        st = str(classifier_meta.get("sub_type") or "")
        if fi not in ("sexual_offence", "missing_person", "attempt_to_murder") and st not in (
            "sexual_offence",
            "missing_person",
            "attempt_to_murder",
        ):
            return False
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
