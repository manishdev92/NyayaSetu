from __future__ import annotations

from typing import Literal, TypedDict

IssueType = Literal[
    "salary",
    "fraud",
    "traffic",
    "land",
    "police",
    "family",
    "cyber",
    "consumer",
    "corporate",
    "general",
    "civil_dispute",
    "financial",
    "rti",
    "civic",
    "education",
    "women_child",
    "senior_citizen",
    "police_oversight",
]
Severity = Literal["low", "medium", "high"]
JurisdictionType = Literal["local", "district", "state", "national"]


class LegalClassification(TypedDict):
    # sub_type: hierarchical leaf (e.g. otp_fraud, rent_issue) — deterministic, not LLM.
    issue_type: IssueType
    severity: Severity
    jurisdiction_type: JurisdictionType
    sub_type: str


def classify_legal_issue(
    text: str,
    entities: list[str] | None = None,
    location: str | None = None,
) -> LegalClassification:
    """Delegates to deterministic `app.core.legal_classifier` (no LLM)."""
    from app.core.legal_classifier import classify_legal_issue as _classify_full

    lc, _meta = _classify_full(text, entities, location)
    return lc
