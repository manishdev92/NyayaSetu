"""
Phase 6: LLM-driven intake questions that affect routing (max 3). Fallback when no API key.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from app.config import settings
from app.core.legal_classifier import ClassifierMeta

logger = logging.getLogger(__name__)

_SYSTEM = """You are a legal intake assistant.
Ask ONLY high-impact questions that affect legal routing.

Rules:
- Max 3 questions
- Focus on: immediate danger (injury, ongoing violence), ownership / legal claim, timeline (recent vs old dispute)
- Return STRICT JSON only with this shape:
{"questions": ["question1", "question2", "question3"]}
Use fewer than 3 strings only if fewer are truly needed; never more than 3.
"""


def run_phase6_clarification_agent(user_query: str, *, max_questions: int = 3) -> list[str]:
    """
    Produce up to `max_questions` plain-string intake questions (routing-oriented).
    """
    q = (user_query or "").strip()
    if not q:
        return []
    if not settings.openai_api_key:
        return _rule_fallback_questions(q, max_questions=max_questions)
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": q[:8000]},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_txt = resp.choices[0].message.content
        if not raw_txt:
            return _rule_fallback_questions(q, max_questions=max_questions)
        data = json.loads(raw_txt)
        return _coerce_questions(data, max_questions=max_questions)
    except Exception as e:  # noqa: BLE001
        logger.info("phase6 clarification_agent fallback: %s", e)
        return _rule_fallback_questions(q, max_questions=max_questions)


def _coerce_questions(data: Any, *, max_questions: int) -> list[str]:
    if not isinstance(data, dict):
        return []
    raw = data.get("questions")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw[:max_questions]:
        s = str(item).strip()
        if len(s) >= 8:
            out.append(s[:400])
    return out[:max_questions]


def _rule_fallback_questions(user_query: str, *, max_questions: int) -> list[str]:
    low = user_query.lower()
    qs: list[str] = []
    if re.search(r"\b(land|plot|property|zameen|khasra|kabza|कब्ज़ा|कब्जा)\b", low, re.I):
        qs.append("Do you have documents showing ownership or lawful possession (sale deed, patta, tax receipts)?")
    if re.search(r"\b(threat|violence|fight|attack|assault|धमकी|मारपीट|लड़ाई)\b", user_query, re.I):
        qs.append("Is the situation currently ongoing or has it stopped?")
        qs.append("Were there any injuries or need for immediate medical help?")
    qs.append("Roughly when did the main events happen (month/year is enough)?")
    seen: set[str] = set()
    uniq: list[str] = []
    for x in qs:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq[:max_questions]


def maybe_attach_pipeline_clarification_questions(
    user_input: str,
    meta: ClassifierMeta,
    *,
    clarification_followup: str | None,
    clarification_round: int,
) -> ClassifierMeta:
    """
    When confidence is below 0.90 or the case is ambiguous, attach Phase 6 intake questions
    for the API layer (optional re-call with clarification_followup, max 2 rounds).
    """
    m: dict[str, Any] = {**meta}
    conf = max(float(m.get("confidence") or 0), float(m.get("confidence_score") or 0))
    ambiguous = bool(m.get("needs_llm_fallback")) or str(m.get("router_intent") or "") in (
        "general_issue",
        "unknown",
    )
    if clarification_round >= 2:
        m["phase6_pipeline_clarification_done"] = True
        return m  # type: ignore[return-value]
    combined = (user_input or "").strip()
    if clarification_followup:
        combined = f"{combined}\n\nUser follow-up:\n{clarification_followup.strip()}"
    if conf >= 0.90 and not ambiguous:
        return m  # type: ignore[return-value]
    qs = run_phase6_clarification_agent(combined)
    if qs:
        m["phase6_pipeline_questions"] = qs
        m["phase6_pipeline_round"] = clarification_round
        m["phase6_suggest_reclassification"] = True
    return m  # type: ignore[return-value]
