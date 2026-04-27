from __future__ import annotations

import json
from typing import Any, TypedDict

from openai import OpenAI

from app.config import settings
from app.ai.llm_fallback_classifier import maybe_apply_llm_classification_fallback
from app.core.legal_classifier import classify_legal_issue as classify_deterministic_full
from app.services.clarification_followup import inject_classification_hints
from app.services.clarification_agent import maybe_attach_pipeline_clarification_questions
from app.services.hybrid_case_routing import (
    apply_hybrid_civil_criminal_overlay,
    apply_law_and_order_land_hybrid_merge,
)
from app.services.legal_priority_engine import apply_priority_override
from app.services.legal_taxonomy import LegalClassification


class InterpretationOutput(TypedDict):
    """LLM interpretation only — MUST NOT drive legal category or routing."""

    entities: list[str]
    intent_hint: str
    context: str


_SYSTEM = """You help parse user text for a legal assistant. Output JSON ONLY.

Keys:
- entities: short strings explicitly mentioned (places, product names, amounts if any). Do NOT invent.
- intent_hint: one short phrase describing what the user seems worried about (plain language). NOT a legal category label.
- context: one sentence paraphrase for tone. Do NOT name government offices, courts, or statutes.

FORBIDDEN:
- legal category (criminal/civil/labour/etc.)
- jurisdiction or which authority to visit
- phone numbers, emails, addresses
- IPC sections or Act names unless quoted from the user

Return: {"entities":[],"intent_hint":"","context":"}
"""


def _coerce_interp(raw: dict[str, Any]) -> InterpretationOutput:
    ent_raw = raw.get("entities")
    entities: list[str] = []
    if isinstance(ent_raw, list):
        for e in ent_raw[:16]:
            s = str(e).strip()
            if s and len(s) < 120:
                entities.append(s)
    return InterpretationOutput(
        entities=entities,
        intent_hint=str(raw.get("intent_hint") or "").strip()[:400],
        context=str(raw.get("context") or "").strip()[:600],
    )


def interpret_user_text(user_input: str) -> InterpretationOutput:
    """Optional LLM layer — rules always win for classification."""
    if not settings.openai_api_key:
        return InterpretationOutput(entities=[], intent_hint="", context="")
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_input.strip()[:12000]},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_txt = resp.choices[0].message.content
        if not raw_txt:
            return InterpretationOutput(entities=[], intent_hint="", context="")
        data = json.loads(raw_txt)
        if not isinstance(data, dict):
            return InterpretationOutput(entities=[], intent_hint="", context="")
        return _coerce_interp(data)
    except Exception:
        return InterpretationOutput(entities=[], intent_hint="", context="")


def _merge_entities(rule_entities: list[str], interp: InterpretationOutput) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for e in list(rule_entities) + interp["entities"]:
        k = e.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(e.strip())
    return out[:20]


def classify_intent_pipeline(
    user_input: str,
    *,
    city: str | None = None,
    clarification_followup: str | None = None,
    clarification_round: int = 0,
) -> tuple[InterpretationOutput, LegalClassification, dict[str, Any]]:
    """
    Deterministic classification first; LLM only adds entities/context.
    Optional clarification follow-up (round cap from CLARIFICATION_MAX_ROUNDS) appends user answers for re-classification.

    Returns (interpretation, legal_classification, classifier_meta dict).
    """
    raw_in = (user_input or "").strip()
    if clarification_followup and clarification_followup.strip():
        raw_in = f"{raw_in}\n\nClarification from user:\n{clarification_followup.strip()}"
    interp = interpret_user_text(raw_in)
    entities = _merge_entities([], interp)
    classified_text = inject_classification_hints(raw_in)
    lc, meta = classify_deterministic_full(classified_text, entities, city)
    lc, meta = apply_hybrid_civil_criminal_overlay(classified_text, lc, meta)
    lc, meta = maybe_apply_llm_classification_fallback(raw_in, lc, meta)
    lc, meta = apply_priority_override(lc, classified_text, meta)
    lc, meta = apply_hybrid_civil_criminal_overlay(classified_text, lc, meta)
    lc, meta = apply_law_and_order_land_hybrid_merge(classified_text, lc, meta)
    meta = maybe_attach_pipeline_clarification_questions(
        raw_in,
        meta,
        clarification_followup=clarification_followup,
        clarification_round=clarification_round,
    )
    return interp, lc, meta


