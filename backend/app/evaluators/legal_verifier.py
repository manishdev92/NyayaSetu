from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

_HALLUC_PHONE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b|\b\d{5}[-\s]?\d{5}\b")
_HALLUC_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class VerifierResult(TypedDict):
    accuracy_score: float
    hallucination_risk: Literal["low", "medium", "high"]
    authority_validity: bool
    fix_required: bool


def evaluate_response(
    draft: str,
    authority: dict[str, Any] | None,
    law_refs: list[dict[str, Any]],
) -> VerifierResult:
    """
    Deterministic legal judge — not an LLM. Flags invented contact risk in draft text.
    """
    st = (authority or {}).get("status")
    authority_validity = st == "verified"
    risk: Literal["low", "medium", "high"] = "low"
    fix_required = False

    if _HALLUC_PHONE.search(draft) or _HALLUC_EMAIL.search(draft):
        if not authority_validity:
            risk = "high"
            fix_required = True
        else:
            # Even with verified authority, extra numbers not in block are suspicious
            risk = "medium"

    if not law_refs:
        if risk == "low":
            risk = "medium"

    acc = 8.0 if authority_validity and risk == "low" else 5.0
    if risk == "high":
        acc = 2.0
    elif risk == "medium":
        acc = min(acc, 6.0)

    return VerifierResult(
        accuracy_score=round(acc, 1),
        hallucination_risk=risk,
        authority_validity=authority_validity,
        fix_required=fix_required,
    )
