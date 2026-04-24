"""Clarification layer: prefer asking over guessing before full generation."""

from __future__ import annotations

import re
from typing import TypedDict

from app.ai.llm_issue_classifier import IssueProfile
from app.core.legal_classifier import ClassifierMeta
from app.services.clarification_structured_llm import (
    rule_based_structured_fallback,
    try_structured_clarification_from_llm,
)
from app.services.legal_taxonomy import LegalClassification

CLARIFICATION_CONFIDENCE_THRESHOLD = 0.75

LAW_ORDER_SAFETY_QUESTIONS = [
    "Is the situation happening right now?",
    "Is anyone injured?",
    "Do you want police help immediately?",
]

_DEFAULT_QUESTION = (
    "Can you clarify whether this relates to salary or employment, a police or criminal matter, "
    "a consumer or service dispute, property or civil court issues, banking, or something else? "
    "One or two more details (what happened, when, and who was involved) will help route you correctly."
)


class ClarificationPoint(TypedDict):
    """One clarification axis with exclusive chip options."""

    label: str
    options: list[str]


class ClarificationIntent(TypedDict, total=False):
    """Intent snapshot for conversational clarification gates (covers urgency + key-fact heuristics)."""

    is_hybrid: bool
    domain: str
    router_intent: str
    issue_type: str
    category: str
    jurisdiction_type: str
    taxonomy_severity: str
    profile_urgency: str
    profile_intent: str


CLARIFICATION_ASK_CONFIDENCE_THRESHOLD = 0.9

_DATE_HINT = re.compile(
    r"\b(20\d{2}|19\d{2}|january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|yesterday|today|last week|last month|"
    r"\d{1,2}[/-]\d{1,2}[/-]?\d{0,4}|months?\s+ago|weeks?\s+ago|days?\s+ago)\b",
    re.I,
)


def build_clarification_intent(
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
) -> ClarificationIntent:
    return {
        "is_hybrid": bool(meta.get("is_hybrid")),
        "domain": str(meta.get("domain") or ""),
        "router_intent": str(meta.get("router_intent") or ""),
        "issue_type": str(taxonomy.get("issue_type") or ""),
        "category": str(issue_profile.get("category") or ""),
        "jurisdiction_type": str(taxonomy.get("jurisdiction_type") or ""),
        "taxonomy_severity": str(taxonomy.get("severity") or ""),
        "profile_urgency": str(issue_profile.get("urgency") or ""),
        "profile_intent": str(issue_profile.get("intent") or ""),
    }


def _should_skip_clarification_from_intent(intent: ClarificationIntent) -> bool:
    if str(intent.get("taxonomy_severity") or "") == "high":
        return True
    if str(intent.get("profile_urgency") or "") == "high":
        return True
    if str(intent.get("profile_intent") or "") == "emergency":
        return True
    return False


def key_facts_missing(text: str, meta: ClassifierMeta, intent: ClarificationIntent) -> bool:
    """Heuristic: timeline, property relationship, or loss/theft axis unclear."""
    t = (text or "").strip()
    if len(t) < 14:
        return True
    low = t.lower()
    it = str(intent.get("issue_type") or "")
    ri = str(meta.get("router_intent") or "")
    dom = str(meta.get("domain") or "").lower()

    time_sensitive = it in ("salary", "police", "fraud") or ri in (
        "salary_issue",
        "criminal_police",
        "civil_dispute",
    )
    if time_sensitive and len(t) < 220 and not _DATE_HINT.search(low):
        return True

    propertyish = bool(
        re.search(
            r"\b(land|property|flat|house|plot|tenant|landlord|kabza|possession|boundary|eviction|lease)\b",
            low,
        )
    )
    if propertyish and not re.search(
        r"\b(owner|ownership|title|deed|sale deed|registry|khasra|survey|lease|rent agreement|tenant)\b",
        low,
    ):
        return True

    if re.search(r"\b(missing|lost|misplaced|cannot find|can\s*'?t find|gone)\b", low) and not re.search(
        r"\b(stolen|theft|robbed|snatched|fir|police complaint)\b",
        low,
    ):
        return True

    if str(intent.get("category") or "") == "consumer" and re.search(r"\b(fraud|cheat|scam)\b", low):
        if not re.search(r"\b(product|service|refund|warranty|defect|bank|otp|online)\b", low):
            return True

    if dom == "labour" and "salary" in low and not re.search(r"\b\d{2,}\b", low) and len(t) < 160:
        return True

    return False


def should_ask_clarification(intent: ClarificationIntent, meta: ClassifierMeta, text: str) -> bool:
    """
    Whether to show a conversational clarification step before drafting.

    True when confidence is below 0.9, the case is hybrid-flagged, or key facts look missing.
    Urgent / emergency cases are skipped (mirrors other clarification paths).
    """
    if _should_skip_clarification_from_intent(intent):
        return False
    conf = max(float(meta.get("confidence") or 0), float(meta.get("confidence_score") or 0))
    if conf < CLARIFICATION_ASK_CONFIDENCE_THRESHOLD:
        return True
    if bool(intent.get("is_hybrid")) or bool(meta.get("is_hybrid")):
        return True
    if key_facts_missing(text, meta, intent):
        return True
    return False


def should_skip_clarification_for_urgency(
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
) -> bool:
    if str(taxonomy.get("severity")) == "high":
        return True
    if issue_profile.get("urgency") == "high":
        return True
    if issue_profile.get("intent") == "emergency":
        return True
    return False


def _classifier_confidence(meta: ClassifierMeta) -> float:
    a = float(meta.get("confidence") or 0)
    b = float(meta.get("confidence_score") or 0)
    return max(a, b)


def is_clear_reported_theft_case(meta: ClassifierMeta, text: str) -> bool:
    """High-confidence theft / police narrative — skip LLM clarification agent."""
    fi = str(meta.get("fine_intent") or "")
    st = str(meta.get("sub_type") or "")
    if fi != "theft" and st != "theft":
        return False
    low = (text or "").strip().lower()
    return bool(
        re.search(
            r"\b(stolen|theft|fir|chori|robbed|snatched|burglary|pickpocket|police\s+station|complaint)\b",
            low,
        )
    )


def compute_missing_entity_flags(
    text: str,
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
) -> dict[str, bool]:
    """Signals for the LLM agent user payload (not authoritative routing)."""
    low = (text or "").strip().lower()
    flags: dict[str, bool] = {
        "date": not bool(_DATE_HINT.search(low)),
        "place": not bool(
            re.search(
                r"\b(in |at |near |district|village|taluka|tehsil|police\s+station|than[ae]|city of|state of)\b",
                low,
            )
        ),
        "actor": not bool(
            re.search(
                r"\b(neighbour|neighbor|landlord|tenant|employer|company|boss|he\s|she\s|they |relative|buyer|seller|driver)\b",
                low,
            )
        ),
        "document": False,
        "lost_vs_theft": False,
    }
    if re.search(r"\b(wallet|phone|laptop|keys|bag|purse|mobile)\b", low) and re.search(
        r"\b(missing|lost|gone|misplaced)\b",
        low,
    ):
        if not re.search(r"\b(stolen|theft|fir|robbed|snatched)\b", low):
            flags["lost_vs_theft"] = True
    prop = bool(re.search(r"\b(land|property|flat|plot|kabza|possession|boundary)\b", low))
    if prop:
        flags["document"] = not bool(
            re.search(r"\b(title|deed|sale deed|lease|agreement|registry|khasra|survey)\b", low)
        )
    return flags


def ambiguous_intent_for_llm_clarification(
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
) -> bool:
    if str(issue_profile.get("category") or "") == "unknown":
        return True
    if str(meta.get("fine_intent") or "") == "general_guidance":
        return True
    if str(taxonomy.get("sub_type") or "") == "general_guidance":
        return True
    if bool(meta.get("needs_llm_fallback")):
        return True
    if str(meta.get("domain") or "") == "unknown":
        return True
    return False


def should_use_llm_clarification(
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
    user_text: str,
    *,
    skip_clarification: bool,
) -> tuple[bool, bool]:
    """
    Whether to invoke the LLM clarification agent.

    Returns (invoke, soft_optional). soft_optional True => hybrid + confidence ≥ 0.85 (non-blocking UX).
    """
    if skip_clarification:
        return False, False
    pl = str(meta.get("priority_level") or "").strip().upper()
    if pl in ("P0", "P1") and not bool(meta.get("hybrid_police_primary")):
        return False, False
    if _looks_like_clarification_followup(user_text):
        return False, False
    if should_skip_clarification_for_urgency(taxonomy, issue_profile):
        return False, False
    if is_clear_reported_theft_case(meta, user_text):
        return False, False

    conf = max(float(meta.get("confidence") or 0), float(meta.get("confidence_score") or 0))
    hybrid = bool(meta.get("is_hybrid"))
    ambiguous = ambiguous_intent_for_llm_clarification(meta, taxonomy, issue_profile)
    flags = compute_missing_entity_flags(user_text, meta, taxonomy, issue_profile)
    it = str(taxonomy.get("issue_type") or "")
    ri = str(meta.get("router_intent") or "")
    time_sensitive = it in ("salary", "police", "fraud") or ri in (
        "salary_issue",
        "criminal_police",
        "civil_dispute",
    )
    missing_trigger = bool(
        flags.get("lost_vs_theft")
        or flags.get("document")
        or (time_sensitive and flags.get("date"))
        or ((ambiguous or conf < 0.85 or hybrid) and (flags.get("place") or flags.get("actor")))
    )

    if hybrid and conf >= 0.85:
        return True, True
    if conf < 0.85 or hybrid or ambiguous or missing_trigger:
        return True, False
    return False, False


def _looks_like_clarification_followup(user_text: str) -> bool:
    """User already picked an option or added a structured follow-up (chat UI appends this)."""
    t = (user_text or "").strip().lower()
    if re.search(r"\n\s*(clarification answers|additional detail|additional details)\s*:", t, re.I):
        return True
    if "additional details" in t or "additional detail" in t:
        if "structured" in t or "my choice" in t or re.search(r"documents?\s*:", t) or re.search(
            r"force|threat|violence", t
        ):
            return True
    if "additional detail" not in t and "my choice" not in t:
        return False
    if re.search(
        r"(?:lost\s*/\s*misplaced|stolen\s*/\s*snatched|not\s+sure|"
        r"missing\s+person|lost\s+or\s+stolen\s+property|"
        r"unauthorized\s*/\s*suspected\s+fraud|bank\s+dispute\s+or\s+service\s+issue|"
        r"consumer\s+commission\s+path|police\s*/\s*criminal\s+complaint|"
        r"safety\s+or\s+violence|unpaid\s+wages|both\b)",
        t,
    ):
        return True
    return False


def law_order_safety_gate_needed(meta: ClassifierMeta, user_text: str) -> bool:
    """Phase 6: short safety intake before drafting when law-and-order signals fire."""
    if str(meta.get("phase6_priority") or "") != "law_and_order":
        return False
    if not bool(meta.get("phase6_priority_override")):
        return False
    if _looks_like_clarification_followup(user_text):
        return False
    return True


def _ambiguous_lost_property(
    user_text: str,
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    t = (user_text or "").strip().lower()
    if _looks_like_clarification_followup(user_text or ""):
        return None
    if not re.search(
        r"\b(wallet|phone|mobile|iphone|android|laptop|keys|key\s*chain|bag|purse|watch|chain|earrings?)\b",
        t,
    ):
        return None
    if not re.search(r"\b(missing|lost|misplaced|can\s*'?t\s+find|cannot\s+find|gone)\b", t):
        return None
    if re.search(r"\b(stolen|theft|robbed|snatched|pickpocket|chori|chor\b|loot)\b", t):
        return None
    return (
        "Did you lose the item or do you suspect it was stolen?",
        [],
        [
            ClarificationPoint(
                label="What applies?",
                options=["Lost / misplaced", "Stolen / snatched", "Not sure"],
            )
        ],
    )


def _ambiguous_missing_person(
    user_text: str,
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    if _looks_like_clarification_followup(user_text or ""):
        return None
    t = (user_text or "").strip().lower()
    if re.search(r"\b(wallet|phone|mobile|laptop|keys|bag|purse)\b", t) and "missing" in t:
        return None
    if re.search(r"\b(stolen|theft|robbed|snatched|kidnap|abduct)\b", t):
        return None
    if "missing" not in t and "लापता" not in (user_text or ""):
        return None
    if not re.search(
        r"\b(person|people|daughter|son|child|wife|husband|mother|father|brother|sister|uncle|aunt|"
        r"relative|family\s+member|colleague|friend)\b",
        t,
    ):
        return None
    return (
        "Is someone missing (cannot be located), or is this about lost or stolen property?",
        [],
        [
            ClarificationPoint(
                label="What applies?",
                options=["Missing person", "Lost or stolen property", "Not sure"],
            )
        ],
    )


def _ambiguous_account_money(
    user_text: str,
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    if _looks_like_clarification_followup(user_text or ""):
        return None
    t = (user_text or "").strip().lower()
    if not re.search(
        r"\b(money|amount|funds)\b.*\b(account|bank)\b|\b(account|bank)\b.*\b(money|debited|withdrawn)\b|"
        r"\bgone\s+from\s+(my\s+)?(bank\s+)?account\b|debited\s+without\s+(my\s+)?(consent|permission)|"
        r"\bunauthorised\s+transaction\b|\bunauthorized\s+transaction\b",
        t,
    ):
        return None
    if re.search(r"\b(otp|upi|phish|cyber|online\s+fraud|net\s+banking|internet\s+banking|hacked)\b", t):
        return None
    return (
        "What fits best: an unauthorized debit or scam suspicion, or a dispute with the bank "
        "(charges, service, or error)?",
        [],
        [
            ClarificationPoint(
                label="What fits best?",
                options=[
                    "Unauthorized / suspected fraud",
                    "Bank dispute or service issue",
                    "Not sure",
                ],
            )
        ],
    )


def _ambiguous_labour_threat(
    user_text: str, meta: ClassifierMeta, taxonomy: LegalClassification
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    t = (user_text or "").strip().lower()
    if str(meta.get("router_intent") or "") != "salary_issue":
        return None
    if str(taxonomy.get("issue_type") or "") != "salary":
        return None
    if not re.search(r"\b(threat|threaten|beat|assault|attack|violence|hit|maar|pitai)\b", t):
        return None
    return (
        "You mentioned both employment/payment and threats or violence. What is the main urgent issue?",
        [],
        [
            ClarificationPoint(
                label="Main urgent issue",
                options=[
                    "Safety or violence (police / FIR first)",
                    "Unpaid wages or PF only",
                    "Both",
                ],
            )
        ],
    )


def _ambiguous_consumer_fraud(
    user_text: str,
    issue_profile: IssueProfile,
    meta: ClassifierMeta,
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    t = (user_text or "").strip().lower()
    if str(issue_profile.get("category") or "") != "consumer":
        return None
    if not re.search(r"\b(fraud|cheat|cheating|scam)\b", t):
        return None
    if str(meta.get("router_intent") or "") in ("fraud_general", "cyber_fraud", "criminal_police"):
        return None
    return (
        "Are you mainly seeking a consumer commission remedy (defective goods or deficient service), "
        "or reporting fraud / cheating for police investigation?",
        [],
        [
            ClarificationPoint(
                label="Preferred route",
                options=[
                    "Consumer commission path",
                    "Police / criminal complaint",
                    "Not sure",
                ],
            )
        ],
    )


def _ambiguous_civil_criminal(
    user_text: str, meta: ClassifierMeta
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    t = (user_text or "").strip().lower()
    if str(meta.get("router_intent") or "") != "civil_dispute":
        return None
    if not re.search(r"\b(fir|police|crime|criminal|assault|threat|cheat)\b", t):
        return None
    return (
        "Your text mentions both civil-style issues and police or criminal words. Which is primary?",
        [],
        [
            ClarificationPoint(
                label="Primary path",
                options=[
                    "Civil court / contract / property",
                    "Police or criminal matter",
                    "Not sure",
                ],
            )
        ],
    )


def _specific_clarification(
    user_text: str,
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
) -> tuple[str, list[str], list[ClarificationPoint] | None] | None:
    for fn in (
        lambda: _ambiguous_lost_property(user_text),
        lambda: _ambiguous_missing_person(user_text),
        lambda: _ambiguous_account_money(user_text),
        lambda: _ambiguous_labour_threat(user_text, meta, taxonomy),
        lambda: _ambiguous_consumer_fraud(user_text, issue_profile, meta),
        lambda: _ambiguous_civil_criminal(user_text, meta),
    ):
        out = fn()
        if out:
            return out
    return None


def _structured_default_clarification(
    user_text: str,
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
) -> tuple[bool, str, list[str], list[ClarificationPoint] | None]:
    llm = try_structured_clarification_from_llm(
        user_text,
        domain=str(meta.get("domain") or ""),
        router_intent=str(meta.get("router_intent") or ""),
        issue_type=str(taxonomy.get("issue_type") or ""),
    )
    if llm:
        return True, llm[0], [], llm[1]
    q, pts = rule_based_structured_fallback(user_text)
    return True, q, [], pts


def needs_clarification(
    meta: ClassifierMeta,
    taxonomy: LegalClassification,
    issue_profile: IssueProfile,
    user_text: str,
) -> tuple[bool, str, list[str], list[ClarificationPoint] | None]:
    """
    Returns (needed, question, flat_options, structured_points).

    Use either flat_options (legacy chips) OR structured_points (label + options per point), not both.
    When structured_points is set, flat_options is empty.
    """
    pl = str(meta.get("priority_level") or "").strip().upper()
    if pl in ("P0", "P1") and not bool(meta.get("hybrid_police_primary")):
        return False, "", [], None
    if should_skip_clarification_for_urgency(taxonomy, issue_profile):
        return False, "", [], None

    spec = _specific_clarification(user_text, meta, taxonomy, issue_profile)
    if spec:
        q, opts, pts = spec
        return True, q, opts, pts

    conf = _classifier_confidence(meta)
    if conf < CLARIFICATION_CONFIDENCE_THRESHOLD:
        return _structured_default_clarification(user_text, meta, taxonomy)

    if str(issue_profile.get("category") or "") == "unknown":
        return _structured_default_clarification(user_text, meta, taxonomy)

    if str(meta.get("fine_intent") or "") == "general_guidance":
        return _structured_default_clarification(user_text, meta, taxonomy)

    if str(taxonomy.get("sub_type") or "") == "general_guidance" or str(meta.get("sub_type") or "") == "general_guidance":
        return _structured_default_clarification(user_text, meta, taxonomy)

    return False, "", [], None
