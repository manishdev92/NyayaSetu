"""Optional LLM: propose structured clarification (max 2 points × 3 options)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class ClarificationPointDict(TypedDict):
    label: str
    options: list[str]


_SYSTEM = """You output JSON ONLY for a legal triage assistant (India).

Return a short clarification request with STRUCTURED points (not prose options mixed into the question).

Rules:
- "question": one sentence introducing why you need clarification.
- "points": array of 1 to 2 objects only. Each object has "label" (short axis, e.g. "Use of force") and "options" (2 to 3 short mutually exclusive choices).
- Each point's "options" must have at most 3 strings.
- Prefer concrete disambiguation (civil vs police, documents, timeline) over vague questions.
- Do NOT invent statutes, IPC sections, office names, or phone numbers.
- Use neutral wording; user may not be fluent in legal terms.

Schema example:
{"question":"...","points":[{"label":"...","options":["...","..."]}]}

Return JSON only."""


def _coerce_points(raw: object) -> list[ClarificationPointDict] | None:
    if not isinstance(raw, list):
        return None
    out: list[ClarificationPointDict] = []
    for item in raw[:2]:
        if not isinstance(item, dict):
            continue
        lab = str(item.get("label") or "").strip()
        opts_raw = item.get("options")
        if not lab or not isinstance(opts_raw, list):
            continue
        opts = [str(o).strip() for o in opts_raw[:3] if str(o).strip()]
        if len(opts) < 2:
            continue
        out.append(ClarificationPointDict(label=lab[:200], options=opts))
    return out or None


def try_structured_clarification_from_llm(
    user_text: str,
    *,
    domain: str,
    router_intent: str,
    issue_type: str,
) -> tuple[str, list[ClarificationPointDict]] | None:
    """
    Returns (question, points) or None on failure / missing API key.
    """
    if not settings.openai_api_key:
        return None
    trimmed = (user_text or "").strip()[:8000]
    if not trimmed:
        return None
    ctx = f"domain={domain!r} router_intent={router_intent!r} issue_type={issue_type!r}\nUser text:\n{trimmed}"
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": ctx},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_txt = resp.choices[0].message.content
        if not raw_txt:
            return None
        data = json.loads(raw_txt)
        if not isinstance(data, dict):
            return None
        q = str(data.get("question") or "").strip()
        pts = _coerce_points(data.get("points"))
        if not q or not pts:
            return None
        return q, pts
    except Exception as e:
        logger.warning("structured clarification LLM failed: %s", e)
        return None


def rule_based_structured_fallback(user_text: str) -> tuple[str, list[ClarificationPointDict]]:
    """Deterministic two-axis clarification when LLM is unavailable."""
    t = (user_text or "").strip().lower()
    q = (
        "A bit more structure will help route you correctly. Please pick the closest match for each point."
    )
    force_opts = [
        "Yes — force, threat, or violence involved",
        "No — peaceful / administrative or civil only",
        "Not sure",
    ]
    doc_opts = [
        "Yes — I have deeds, agreements, or written proof",
        "Partially — some papers only",
        "No — not yet",
    ]
    if re.search(r"\b(land|property|plot|possession|tenant|lease|encroach|boundary)\b", t):
        return q, [
            ClarificationPointDict(label="Force, threat, or violence in the situation?", options=force_opts),
            ClarificationPointDict(label="Key documents available?", options=doc_opts),
        ]
    return q, [
        ClarificationPointDict(label="Is any force, threat, or criminal angle involved?", options=force_opts),
        ClarificationPointDict(label="Do you have documents or records to support your account?", options=doc_opts),
    ]
