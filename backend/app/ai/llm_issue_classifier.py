from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from openai import OpenAI

from app.config import settings
from app.core.legal_classifier import ClassifierMeta
from app.services.legal_taxonomy import LegalClassification


class IssueProfile(TypedDict, total=False):
    """Merged view for API + formatter (rules + LLM enrichment)."""

    category: str
    severity: str
    intent: str
    keywords: list[str]
    urgency: str  # normal | high
    source: str  # rules | llm | merged


_SYSTEM = """You extract structured cues from Indian legal user text. Output JSON ONLY.

Keys:
- category: one of criminal | civil | consumer | labour | cyber | traffic | family | unknown
- severity: one of high | medium | low
- intent: one of complaint | information | dispute | emergency
- keywords: array of short strings (max 12) from the user's text — no fabrication

Guidance (hints only — server merges with deterministic rules):
- Missing person / kidnapping / abduction → criminal, high, emergency
- Theft / stolen → criminal, high
- Online fraud / OTP → cyber, high
- Salary / PF / employer → labour, medium
- Overcharging / defective service → consumer
- Traffic fine / challan → traffic

Do NOT output authority names, phone numbers, or addresses.
Return: {"category":"...","severity":"...","intent":"...","keywords":[]}
"""


def _coerce_llm(raw: dict[str, Any]) -> dict[str, Any]:
    cat = str(raw.get("category") or "unknown").strip().lower()
    if cat not in ("criminal", "civil", "consumer", "labour", "cyber", "traffic", "family", "unknown"):
        cat = "unknown"
    sev = str(raw.get("severity") or "medium").strip().lower()
    if sev not in ("high", "medium", "low"):
        sev = "medium"
    intent = str(raw.get("intent") or "complaint").strip().lower()
    if intent not in ("complaint", "information", "dispute", "emergency"):
        intent = "complaint"
    kw_raw = raw.get("keywords")
    keywords: list[str] = []
    if isinstance(kw_raw, list):
        for k in kw_raw[:12]:
            s = str(k).strip()
            if s and len(s) < 80:
                keywords.append(s)
    return {"category": cat, "severity": sev, "intent": intent, "keywords": keywords}


def _llm_profile(user_text: str) -> dict[str, Any] | None:
    if not settings.openai_api_key:
        return None
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_text.strip()[:12000]},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
        )
        raw = resp.choices[0].message.content
        if not raw:
            return None
        data = json.loads(raw)
        return _coerce_llm(data) if isinstance(data, dict) else None
    except Exception:
        return None


def _map_issue_type_to_slug(issue_type: str, meta: ClassifierMeta) -> str:
    m: dict[str, str] = {
        "police": "criminal",
        "fraud": "criminal",
        "cyber": "cyber",
        "salary": "labour",
        "consumer": "consumer",
        "traffic": "traffic",
        "land": "civil",
        "family": "family",
        "corporate": "civil",
        "general": "unknown",
        "civil_dispute": "civil",
        "financial": "civil",
        "rti": "civil",
        "civic": "civil",
        "education": "consumer",
        "women_child": "family",
        "senior_citizen": "family",
        "police_oversight": "criminal",
    }
    base = m.get(issue_type, "unknown")
    if meta.get("category") == "labour":
        return "labour"
    if meta.get("category") == "criminal":
        return "criminal"
    if meta.get("category") == "land_revenue":
        return "civil"
    if meta.get("category") == "traffic":
        return "traffic"
    if meta.get("category") == "consumer":
        return "consumer"
    if meta.get("category") == "civil_commercial":
        return "civil"
    if meta.get("router_intent") == "civil_dispute" or issue_type == "civil_dispute" or (
        meta.get("category") == "civil" and issue_type == "general"
    ):
        return "civil"
    return base


def _max_sev_str(*levels: str) -> str:
    order = {"low": 1, "medium": 2, "high": 3}
    return max(levels, key=lambda x: order.get(x, 2))


_MISSING_PAT = re.compile(
    r"\b(missing\s+person|person\s+missing|kidnapp|abduct|abduction|lost\s+child|"
    r"child\s+missing|गुम|लापता)\b",
    re.I,
)


def merge_issue_profile(
    user_text: str,
    taxonomy: LegalClassification,
    meta: ClassifierMeta,
    llm_part: dict[str, Any] | None,
) -> IssueProfile:
    """
    Rules own category + routing; LLM enriches keywords and can raise severity / emergency intent.
    """
    slug = _map_issue_type_to_slug(str(taxonomy["issue_type"]), meta)
    sev: str = str(taxonomy["severity"])
    intent: str = "complaint"
    keywords: list[str] = []

    t = (user_text or "").lower()

    if meta.get("fine_intent") in ("missing_person", "sexual_offence") or str(meta.get("sub_type") or "") in (
        "missing_person",
        "sexual_offence",
    ):
        slug = "criminal"
        sev = _max_sev_str(sev, "high")
        intent = "emergency"
    elif _MISSING_PAT.search(t):
        slug = "criminal"
        sev = _max_sev_str(sev, "high")
        intent = "emergency"

    if llm_part:
        keywords = list(llm_part.get("keywords") or [])
        sev = _max_sev_str(sev, str(llm_part.get("severity") or "medium"))
        li = str(llm_part.get("intent") or "complaint")
        if intent != "emergency":
            if li == "emergency":
                intent = "emergency"
            elif li in ("complaint", "information", "dispute"):
                intent = li

    if meta.get("fine_intent") == "theft" or "stolen" in t:
        sev = _max_sev_str(sev, "high")
    if str(meta.get("sub_type") or "") == "assault":
        sev = _max_sev_str(sev, "high")
    if str(meta.get("sub_type") or "") == "fraud_general" and sev == "high":
        intent = "emergency"
    if meta.get("router_intent") == "cyber_fraud":
        slug = "cyber"
        sev = _max_sev_str(sev, "high")

    urgency = "high" if sev == "high" or intent == "emergency" else "normal"

    return IssueProfile(
        category=slug,
        severity=sev,
        intent=intent,
        keywords=keywords[:12],
        urgency=urgency,
        source="merged",
    )


def classify_issue_enriched(user_text: str, taxonomy: LegalClassification, meta: ClassifierMeta) -> IssueProfile:
    llm = _llm_profile(user_text)
    return merge_issue_profile(user_text, taxonomy, meta, llm)
