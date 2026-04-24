"""Lightweight quality gate — score draft + routing; optional one regeneration."""

from __future__ import annotations

import re
from typing import Any

_FAKE_PHONE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
_FIR_PHRASE = re.compile(
    r"register\s+an\s+FIR|registration\s+of\s+FIR|kindly\s+register",
    re.I,
)
# Model sometimes pastes SHO / routing blurbs inside "Police Station (...)" — invalid.
_GARBLED_PS_LINE = re.compile(
    r"Police\s+Station\s*\([^)]*(?:Station\s+House\s+Officer|\bSHO\b|FIR\s+or\s+written)",
    re.I,
)


def evaluate_generation_output(
    *,
    document: str,
    issue_profile: dict[str, Any],
    authority_block: dict[str, Any],
    classifier_category: str,
) -> tuple[float, dict[str, Any]]:
    """
    Returns (score 0–10, detail dict). Score >= 8 is acceptable.
    Heuristic only — not a substitute for human review.
    """
    score = 5.0
    reasons: list[str] = []

    primary = str(authority_block.get("primary") or "").strip()
    if len(primary) >= 12:
        score += 1.5
        reasons.append("authority_primary_present")
    else:
        reasons.append("authority_primary_weak")

    cat = str(issue_profile.get("category") or "")
    if cat == "criminal" and _FIR_PHRASE.search(document):
        score += 2.0
        reasons.append("fir_language_present")
    elif cat == "criminal":
        score += 0.5
        reasons.append("criminal_without_explicit_fir_phrase")

    ul = str(issue_profile.get("severity") or "medium")
    if ul == "high" and ("112" in document or "100" in document or "police" in document.lower()):
        score += 1.0
        reasons.append("urgency_echo_in_document")

    if _FAKE_PHONE.search(document) and authority_block.get("status") != "verified":
        score -= 3.0
        reasons.append("possible_invented_phone_in_document")

    if classifier_category == "criminal" and "district collector" in document.lower() and "police" not in document.lower():
        score -= 2.0
        reasons.append("possible_wrong_forum_collector_only")

    if _GARBLED_PS_LINE.search(document):
        score -= 2.5
        reasons.append("garbled_police_station_line_sho_in_parentheses")

    score = max(0.0, min(10.0, score))
    return score, {"reasons": reasons, "score": score}


def should_regenerate(score: float) -> bool:
    return score < 8.0


# Alias for external callers (evaluation agent).
evaluate_output = evaluate_generation_output
