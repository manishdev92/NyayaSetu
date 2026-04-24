"""
Legacy adapter — deterministic classification lives in `app.core.legal_classifier`.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.ai.llm_intent_engine import classify_intent_pipeline
from app.services.legal_taxonomy import LegalClassification


class ClassifierOutput(TypedDict, total=False):
    intent: str
    category: str
    entities: list[str]
    confidence: float
    issue_type_confidence: float
    router_intent: str
    fine_intent: str


def classify_pipeline(user_input: str) -> tuple[ClassifierOutput, LegalClassification]:
    interpretation, taxonomy, meta = classify_intent_pipeline(user_input, city=None)
    c = float(meta["confidence"])
    legacy: ClassifierOutput = ClassifierOutput(
        intent=meta["router_intent"],
        category=meta["category"],
        entities=interpretation["entities"],
        confidence=c,
        issue_type_confidence=c,
        router_intent=meta["router_intent"],
        fine_intent=meta["fine_intent"],
    )
    return legacy, taxonomy


def classify_legal_intent(user_input: str, *, det: LegalClassification | None = None) -> ClassifierOutput:
    _ = det
    out, _ = classify_pipeline(user_input)
    return out
