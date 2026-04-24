"""LLM classification fallback when deterministic rules are weak or land on general."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Final

from openai import OpenAI

from app.config import settings
from app.core.legal_classifier import ClassifierMeta
from app.services.legal_router import RouterResult
from app.services.legal_taxonomy import IssueType, JurisdictionType, LegalClassification, Severity

logger = logging.getLogger(__name__)

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_FILE = _LOG_DIR / "llm_fallback_cases.json"

_ALLOWED_ROUTER_INTENTS: Final[frozenset[str]] = frozenset(
    {
        "share_dispute",
        "general_issue",
        "salary_issue",
        "civil_dispute",
        "cyber_fraud",
        "fraud_general",
        "traffic_violation",
        "land_dispute",
        "family_matters",
        "consumer_issue",
        "criminal_police",
        "police_oversight",
        "rti_grievance",
        "civic_local",
        "banking_ombudsman",
        "education_dispute",
        "women_child_route",
        "senior_maintenance",
    }
)

_ROUTER_TO_ISSUE: dict[str, IssueType] = {
    "criminal_police": "police",
    "cyber_fraud": "cyber",
    "consumer_issue": "consumer",
    "salary_issue": "salary",
    "civil_dispute": "civil_dispute",
    "fraud_general": "fraud",
    "land_dispute": "land",
    "traffic_violation": "traffic",
    "family_matters": "family",
    "rti_grievance": "rti",
    "civic_local": "civic",
    "banking_ombudsman": "financial",
    "education_dispute": "education",
    "women_child_route": "women_child",
    "senior_maintenance": "senior_citizen",
    "police_oversight": "police_oversight",
    "share_dispute": "corporate",
    "general_issue": "general",
}

_ROUTER_TO_DOMAIN: dict[str, str] = {
    "criminal_police": "criminal",
    "police_oversight": "police_complaint",
    "cyber_fraud": "cyber",
    "fraud_general": "criminal",
    "consumer_issue": "consumer",
    "salary_issue": "labour",
    "civil_dispute": "civil",
    "traffic_violation": "traffic",
    "land_dispute": "government",
    "family_matters": "family",
    "rti_grievance": "rti",
    "civic_local": "civic",
    "banking_ombudsman": "financial",
    "education_dispute": "education",
    "women_child_route": "women_child",
    "senior_maintenance": "senior_citizen",
    "share_dispute": "civil",
    "general_issue": "general",
}

_ROUTER_TO_CATEGORY: dict[str, str] = {
    "criminal_police": "criminal",
    "police_oversight": "criminal",
    "cyber_fraud": "criminal",
    "fraud_general": "criminal",
    "consumer_issue": "consumer",
    "salary_issue": "labour",
    "civil_dispute": "civil",
    "traffic_violation": "traffic",
    "land_dispute": "land_revenue",
    "family_matters": "family",
    "rti_grievance": "administrative",
    "civic_local": "administrative",
    "banking_ombudsman": "financial",
    "education_dispute": "consumer",
    "women_child_route": "family",
    "senior_maintenance": "family",
    "share_dispute": "civil_commercial",
    "general_issue": "general",
}

_SAFETY_VIOLENCE = re.compile(
    r"\b(assault|attack|beating|violence|danger|threat|threaten|beaten|hit\s+me|"
    r"pitai|maar\s*peet|domestic\s+violence|dv\b)\b",
    re.I,
)

_LLM_SYSTEM = """You classify Indian legal user messages for routing ONLY. Output ONE JSON object with EXACTLY these keys:
- issue_type: one of salary|fraud|traffic|land|police|family|cyber|consumer|corporate|general|civil_dispute|financial|rti|civic|education|women_child|senior_citizen|police_oversight
- domain: short slug (e.g. criminal, civil, consumer, labour, cyber, general)
- sub_type: short snake_case label (no spaces)
- router_intent: one of share_dispute|general_issue|salary_issue|civil_dispute|cyber_fraud|fraud_general|traffic_violation|land_dispute|family_matters|consumer_issue|criminal_police|police_oversight|rti_grievance|civic_local|banking_ombudsman|education_dispute|women_child_route|senior_maintenance
- severity: low|medium|high
- urgency: low|medium|high
- suggested_authority: ONLY a generic authority TYPE in plain words (e.g. "police station", "consumer commission", "labour office") — NEVER a specific office name, phone, email, address, PIN, or officer name
- confidence: number 0.0–1.0 for your classification confidence

STRICT RULES:
- Do NOT output phone numbers, emails, URLs, or addresses.
- Do NOT invent statutes or IPC sections unless quoted from the user.
- Prefer police/criminal_police for clear violence, threats, serious bodily harm, or missing-person emergencies.
- Prefer consumer_issue for defective goods / service deficiency; salary_issue for wages/PF/employer (non-violence).
- If unsure, use general_issue + general + low confidence.

Return JSON only."""


def _det_confidence(meta: ClassifierMeta) -> float:
    return max(float(meta.get("confidence") or 0), float(meta.get("confidence_score") or 0))


def deterministic_triggers_llm_fallback(lc: LegalClassification, meta: ClassifierMeta) -> bool:
    """When True, we attempt LLM re-classification (OpenAI must be configured)."""
    if bool(meta.get("is_hybrid")):
        return False
    conf = _det_confidence(meta)
    it = str(lc.get("issue_type") or "")
    ri = str(meta.get("router_intent") or "")
    if it == "police" and conf >= 0.60:
        return False
    if it in (
        "cyber",
        "fraud",
        "police_oversight",
        "women_child",
        "family",
        "land",
        "traffic",
        "consumer",
        "salary",
        "civil_dispute",
        "financial",
        "rti",
        "civic",
        "education",
        "senior_citizen",
        "corporate",
    ) and conf >= 0.65:
        return False
    # Only the weak "general" bucket — avoids overwriting borderline deterministic routes.
    return it == "general" or ri == "general_issue"


def _defer_llm_for_structured_clarification(
    user_text: str, meta: ClassifierMeta, lc: LegalClassification
) -> bool:
    """Cases handled by clarification_engine first — do not LLM-reclassify."""
    from app.services import clarification_engine as ce

    if ce._ambiguous_lost_property(user_text):
        return True
    if ce._ambiguous_missing_person(user_text):
        return True
    if ce._ambiguous_account_money(user_text):
        return True
    if ce._ambiguous_labour_threat(user_text, meta, lc):
        return True
    return False


def _violence_safety_override(user_text: str) -> dict[str, Any] | None:
    if not _SAFETY_VIOLENCE.search(user_text or ""):
        return None
    return {
        "issue_type": "police",
        "domain": "criminal",
        "sub_type": "violence_safety_override",
        "router_intent": "criminal_police",
        "severity": "high",
        "urgency": "high",
        "suggested_authority": "police",
        "confidence": 0.95,
    }


def classify_with_llm_fallback(text: str) -> dict[str, Any] | None:
    """
    Ask the LLM for a strict JSON classification. Returns None on failure.
    Does not apply safety overrides — caller merges after applying violence check on user text.
    """
    if not settings.openai_api_key:
        return None
    trimmed = (text or "").strip()[:12000]
    if not trimmed:
        return None
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": trimmed},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
        )
        raw_txt = resp.choices[0].message.content
        if not raw_txt:
            return None
        data = json.loads(raw_txt)
        if not isinstance(data, dict):
            return None
        return data
    except Exception as e:
        logger.warning("llm_fallback classify failed: %s", e)
        return None


def _normalize_router_intent(raw: str) -> str:
    s = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "police": "criminal_police",
        "police_station": "criminal_police",
        "criminal": "criminal_police",
        "fir": "criminal_police",
        "cybercrime": "cyber_fraud",
        "cyber_crime": "cyber_fraud",
        "consumer_forum": "consumer_issue",
        "consumer_commission": "consumer_issue",
        "labour": "salary_issue",
        "labor": "salary_issue",
        "employment": "salary_issue",
        "civil_court": "civil_dispute",
        "bank": "banking_ombudsman",
        "banking": "banking_ombudsman",
        "rto": "traffic_violation",
        "municipal": "civic_local",
    }
    s = aliases.get(s, s)
    if s in _ALLOWED_ROUTER_INTENTS:
        return s
    return "general_issue"


def _coerce_severity(s: object) -> Severity:
    v = str(s or "medium").strip().lower()
    if v in ("low", "medium", "high"):
        return v  # type: ignore[return-value]
    return "medium"


def _coerce_issue_type(s: object) -> IssueType:
    v = str(s or "general").strip().lower()
    allowed: set[str] = {
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
    }
    if v in allowed:
        return v  # type: ignore[return-value]
    return "general"


def _jurisdiction_for_issue(issue: IssueType) -> JurisdictionType:
    if issue == "cyber":
        return "national"
    if issue in ("consumer", "fraud", "corporate", "general", "civil_dispute", "education", "rti", "financial"):
        return "state"
    if issue in ("traffic", "civic"):
        return "local"
    return "district"


def _llm_dict_to_classification(
    d: dict[str, Any],
    *,
    user_text: str,
    raw_for_trace: dict[str, Any],
) -> tuple[LegalClassification, ClassifierMeta]:
    vio = _violence_safety_override(user_text)
    effective = vio if vio is not None else d

    router = _normalize_router_intent(str(effective.get("router_intent") or ""))
    issue_from_router = _ROUTER_TO_ISSUE.get(router, "general")
    issue_llm = _coerce_issue_type(effective.get("issue_type"))
    if router != "general_issue" and issue_from_router != "general":
        issue: IssueType = issue_from_router
    else:
        issue = issue_llm

    sev = _coerce_severity(effective.get("severity"))
    if str(effective.get("urgency") or "").lower() == "high" and sev != "high":
        sev = "high"

    sub = str(effective.get("sub_type") or "llm_inferred").strip()[:120] or "llm_inferred"
    sub = re.sub(r"[^\w\-]+", "_", sub, flags=re.ASCII)[:80]

    conf = float(effective.get("confidence") or 0.72)
    if not (0.0 <= conf <= 1.0):
        conf = 0.72

    domain = str(effective.get("domain") or _ROUTER_TO_DOMAIN.get(router, "general"))[:80]
    category = str(effective.get("category") or _ROUTER_TO_CATEGORY.get(router, "general"))[:80]

    is_llm_used = isinstance(raw_for_trace.get("llm"), dict)

    meta: ClassifierMeta = {  # type: ignore[assignment]
        "domain": domain,
        "sub_type": sub,
        "category": category,
        "fine_intent": router,
        "confidence": conf,
        "confidence_score": conf,
        "router_intent": router,
        "needs_llm_fallback": True,
        "is_llm_fallback": is_llm_used,
        "llm_fallback_confidence": conf,
        "llm_fallback_raw": dict(raw_for_trace),
    }
    lc: LegalClassification = {
        "issue_type": issue,
        "severity": sev,
        "jurisdiction_type": _jurisdiction_for_issue(issue),
        "sub_type": sub,
    }
    return lc, meta


def log_llm_fallback_case(
    user_text: str,
    llm_raw: dict[str, Any] | None,
    router_result: RouterResult,
) -> None:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "input_excerpt": (user_text or "")[:2000],
            "llm_output": llm_raw,
            "final_primary_authority": router_result.get("primary_authority"),
            "final_secondary_authority": router_result.get("secondary_authority"),
        }
        existing: list[Any] = []
        if _LOG_FILE.exists():
            try:
                existing = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(entry)
        _LOG_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("llm_fallback log write failed: %s", e)


def maybe_apply_llm_classification_fallback(
    user_text: str,
    lc: LegalClassification,
    meta: ClassifierMeta,
) -> tuple[LegalClassification, ClassifierMeta]:
    """
    If deterministic classification is weak, replace lc/meta using LLM JSON + safety overrides.
    Router intents are normalized to values accepted by route_case().
    """
    if not deterministic_triggers_llm_fallback(lc, meta):
        return lc, meta
    if _defer_llm_for_structured_clarification(user_text, meta, lc):
        return lc, meta

    meta_out: ClassifierMeta = dict(meta)  # type: ignore[assignment]
    meta_out["needs_llm_fallback"] = True

    raw_llm = classify_with_llm_fallback(user_text)
    if not raw_llm:
        vio = _violence_safety_override(user_text)
        if vio:
            trace = {"violence_only": True, "llm": None}
            merged_lc, merged_meta = _llm_dict_to_classification(
                vio, user_text=user_text, raw_for_trace=trace
            )
            merged_meta["is_llm_fallback"] = False
            return merged_lc, merged_meta
        return lc, meta_out

    trace = {"llm": raw_llm, "violence_override": bool(_violence_safety_override(user_text))}
    merged_lc, merged_meta = _llm_dict_to_classification(raw_llm, user_text=user_text, raw_for_trace=trace)

    return merged_lc, merged_meta
