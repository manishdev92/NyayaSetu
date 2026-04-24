"""Multi-facet legal intent detection — LLM + keyword groups."""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from openai import OpenAI

from app.config import settings
from app.core.legal_classifier import ClassifierMeta
from app.services.priority_resolution import PRIORITY_ORDER, pick_primary_category, split_primary_secondary
from app.services.legal_taxonomy import LegalClassification

_LABOUR = re.compile(
    r"\b(salary|wage|wages|unpaid|pf\b|gratuity|employer|termination|bonus|overtime|labour|labor)\b",
    re.I,
)
_CRIMINAL = re.compile(
    r"\b(threat|threatened|assault|beat|attack|hurt|harm|fir\b|police|crime|criminal|"
    r"theft|robbery|murder|rape|kidnap|missing|weapon|ipc\b|section\s+\d+)\b",
    re.I,
)
_CYBER = re.compile(
    r"\b(cyber|online\s+fraud|phishing|upi|otp|hacking|data\s+breach|internet\s+crime)\b",
    re.I,
)
_CONSUMER = re.compile(
    r"\b(consumer|defective|warranty|refund|overcharg|service\s+deficiency|cpa\b)\b",
    re.I,
)
_TRAFFIC = re.compile(r"\b(challan|traffic\s+fine|rto\b|licen[cs]e|dl\b)\b", re.I)
_CIVIL = re.compile(
    r"\b(contract|breach|money\s+recovery|civil\s+suit|partition|eviction|"
    r"property\s+dispute|share\s+dispute|specific\s+performance)\b",
    re.I,
)
_FAMILY = re.compile(r"\b(divorce|custody|maintenance|498a|marriage|alimony)\b", re.I)


class MultiIntentResult(TypedDict):
    intents: list[str]
    primary: str
    secondaries: list[str]
    confidence_split: bool
    source: str


_LLM_SYSTEM = """You detect whether an Indian legal user message involves MULTIPLE distinct legal facets.

Output JSON ONLY:
{
  "intents": ["criminal"|"cyber"|"labour"|"consumer"|"traffic"|"civil"|"family"|"unknown"],
  "confidence_split": boolean
}

Rules:
- "not paid salary and employer threatened me" → ["labour","criminal"], confidence_split true
- Single-topic messages → one intent, confidence_split false
- Do not invent facts; intents must be plausible from the text.
"""


def _heuristic_intents(text: str) -> set[str]:
    t = (text or "").lower()
    out: set[str] = set()
    if _LABOUR.search(t):
        out.add("labour")
    if _CRIMINAL.search(t):
        out.add("criminal")
    if _CYBER.search(t):
        out.add("cyber")
    if _CONSUMER.search(t):
        out.add("consumer")
    if _TRAFFIC.search(t):
        out.add("traffic")
    if _CIVIL.search(t):
        out.add("civil")
    if _FAMILY.search(t):
        out.add("family")
    return out


def _llm_multi_intent(user_text: str) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": user_text.strip()[:12000]},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = r.choices[0].message.content
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _slug_from_classifier(taxonomy: LegalClassification, meta: ClassifierMeta) -> str:
    it = str(taxonomy["issue_type"])
    cat = str(meta.get("category") or "")
    ri = str(meta.get("router_intent") or "")
    if ri == "civil_dispute" or it == "civil_dispute" or (cat == "civil" and it == "general"):
        return "civil"
    if it == "cyber" or ri == "cyber_fraud":
        return "cyber"
    if it in ("police", "fraud") or cat == "criminal":
        return "criminal"
    if it == "salary" or cat == "labour":
        return "labour"
    if it == "consumer":
        return "consumer"
    if it == "traffic":
        return "traffic"
    if it in ("land", "corporate") and cat in ("civil", "civil_commercial", "land_revenue"):
        return "civil"
    if it == "family":
        return "family"
    if it in ("financial", "rti", "civic", "education", "women_child", "senior_citizen"):
        return "civil"
    if it == "police_oversight":
        return "criminal"
    return "unknown"


def detect_multi_intent_list(user_text: str) -> list[str]:
    """
    Convenience API: returns category slugs only (uses deterministic classifier + merge).
    For full routing metadata use `detect_multi_intent`.
    """
    from app.core.legal_classifier import classify_legal_issue

    lc, meta = classify_legal_issue(user_text)
    return list(detect_multi_intent(user_text, lc, meta)["intents"])


def detect_multi_intent(
    user_text: str,
    taxonomy: LegalClassification,
    meta: ClassifierMeta,
) -> MultiIntentResult:
    """
    Combine keyword groups + optional LLM. Always includes classifier-derived primary slug.
    """
    h = _heuristic_intents(user_text)
    llm = _llm_multi_intent(user_text)
    llm_ints: list[str] = []
    conf_split = False
    if llm:
        raw_list = llm.get("intents")
        if isinstance(raw_list, list):
            allowed = frozenset(PRIORITY_ORDER + ["unknown"])
            for x in raw_list:
                s = str(x).strip().lower()
                if s in allowed:
                    llm_ints.append(s)
        conf_split = bool(llm.get("confidence_split"))

    merged = set(h) | set(llm_ints)
    base = _slug_from_classifier(taxonomy, meta)
    merged.add(base)

    # Cyber often also matches "criminal" heuristics — keep both; primary resolver picks cyber vs criminal.
    intents_list = list(merged)
    primary, secondaries = split_primary_secondary(intents_list)

    # If only unknown slipped in with real tags, drop unknown
    if len(intents_list) > 1 and "unknown" in intents_list:
        intents_list = [x for x in intents_list if x != "unknown"]
        primary, secondaries = split_primary_secondary(intents_list)

    confidence_split = conf_split or len([x for x in intents_list if x != "unknown"]) >= 2

    return MultiIntentResult(
        intents=intents_list,
        primary=primary,
        secondaries=secondaries,
        confidence_split=confidence_split,
        source="merged",
    )
