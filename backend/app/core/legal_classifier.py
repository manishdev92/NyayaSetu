"""
Deterministic legal classification — NO LLM. Every user issue goes through a single **ordered** rule
chain: higher-severity / clearer buckets first, then more general paths. The output is *issue_type* +
*router_intent* for the whole app (not tuned to one kind of case only).

Priority (see rules below in source order): e.g. emergency violence → missing person →
assault (non-battery) → **CPA retail/remote-purchase v. cyber** (one disambiguation block) →
cyber proper → theft → … → **consumer** (general keyword block) → land, labour, traffic, family, etc. →
general. Additional regexes only **de-conflict** routes that are easy to mix up (e.g. “online
order” is often consumer law, not cybercrime) — they do not replace the rest of the chain.
"""

from __future__ import annotations

import re
from typing import Any, NotRequired, TypedDict

from app.services.legal_taxonomy import (
    IssueType,
    JurisdictionType,
    LegalClassification,
    Severity,
)


class ClassifierMeta(TypedDict):
    """Trace for routing / API — domain + sub_type are the hierarchical taxonomy (deterministic)."""

    domain: str
    sub_type: str
    category: str
    fine_intent: str
    confidence: float
    confidence_score: float  # 0–1, same scale as confidence; explicit for API consumers
    router_intent: str
    needs_llm_fallback: NotRequired[bool]
    is_llm_fallback: NotRequired[bool]
    llm_fallback_confidence: NotRequired[float]
    llm_fallback_raw: NotRequired[dict[str, Any]]
    secondary_domain: NotRequired[str]
    is_hybrid: NotRequired[bool]
    is_priority_override: NotRequired[bool]
    priority_level: NotRequired[str]  # P0–P5 when legal_priority_engine applied
    phase6_priority: NotRequired[str]
    phase6_urgency: NotRequired[str]
    phase6_priority_override: NotRequired[bool]
    phase6_primary_forum: NotRequired[str]
    hybrid_police_primary: NotRequired[bool]
    hybrid_routing_type: NotRequired[str]
    phase6_pipeline_questions: NotRequired[list[str]]
    phase6_pipeline_round: NotRequired[int]
    phase6_suggest_reclassification: NotRequired[bool]
    phase6_pipeline_clarification_done: NotRequired[bool]
    is_emergency: NotRequired[bool]
    emergency_layer: NotRequired[dict[str, Any]]


_THEFT_HARD = re.compile(
    r"\b(stolen|theft|chori|चोरी|robbed|robbery|burglary|snatched|snatching|"
    r"lost\s+forcibly|forcibly\s+taken|bike\s+stolen|bicycle\s+stolen|cycle\s+stolen|"
    r"chori\s+ho|चोरी\s+हो)\b",
    re.IGNORECASE,
)

# Wallet/phone/etc. + missing/lost (not theft keywords) → police / lost article path (before sectoral buckets).
_LOST_ARTICLE_OBJECT = re.compile(
    r"\b(wallet|wallets|batuaa?|batuva|batua\b|बटुआ|phone|phones|mobile|iphone|android|laptop|laptops|keys|keychain|bag|bags|purse|watches?)\b",
    re.I,
)
_LOST_OR_MISSING_SIGNAL = re.compile(
    r"\b(missing|lost|misplaced|cannot\s+find|can't\s+find|cant\s+find|do\s+not\s+find|did\s+not\s+find|"
    r"gone\s+missing|nowhere\s+to\s+be\s+found|not\s+found|kayab|gayab|gayaab|lapata|lapataa|"
    r"ho\s+gya|ho\s+gaya|kho\s+gya|kho\s+gaya|gum\s+ho|gum\s+hogaya|"
    r"खो\s*गया|खो\s+गया|गायब|गुम|लापता|नहीं\s+मिल)\b",
    re.I,
)

_MISSING = re.compile(
    r"(?:^|[\s,;])(लापता|गायब|गुम|gumshuda|gayab)(?:[\s,;]|$)|"
    r"\b(missing\s+person|person\s+missing|missing\s+child|lost\s+child|child\s+missing|"
    r"(?:daughter|son|child|uncle|aunt|niece|nephew|cousin|wife|husband|mother|father|brother|sister)\s+missing|"
    r"(?:daughter|son|child|wife|husband|mother|father|brother|sister)\s+has\s+been\s+missing|"
    r"missing\s+(?:daughter|son|child|person)|"
    r"been\s+missing\s+since|"
    r"kidnapp|kidnapping|abduct|abduction)\b",
    re.IGNORECASE,
)

# Sexual violence / serious bodily harm → police / FIR only (never labour/consumer as primary).
# NOTE: "attempt to murder" is handled separately — do not include here (was mis-routing FIR phrasing).
_SEXUAL_OR_SERIOUS_VIOLENCE = re.compile(
    r"\b(sexual(ly)?\s+abus(e|ed)|sexual\s+abuse|molest(ed|ation)?|rape|pocso|"
    r"balatkar|ched\s*chad|chedchad|"
    r"grope|groping|indecent\s+assault|acid\s+attack)\b",
    re.I,
)

_FEES_CONSUMER = re.compile(
    r"\b(?:fees?\s+(?:is\s+)?(?:too\s+)?high|overcharg(?:ed|ing)?|exorbitant\s+fees|"
    r"(?:school|college|institute)\s+fees)\b",
    re.I,
)

_VIOLENT_SIMPLE = re.compile(
    r"\b(assault|assaulted|battery|attack|beaten|beating|beat\b|beat\s+me|hurt\s+me|grievous)\b",
    re.I,
)

_DEVICE_OR_PRODUCT_BATTERY = re.compile(
    r"(?i)(?:(?:the|a|an|my|our)\s+)?(?:"
    r"phone|phones|iphone|android|mobile|laptop|tablet|car|ev|lithium|watch|tw[s']|earbuds?)\S*\s+battery\b|"
    r"battery\s+is\s+(defective|weak|drained|low|not\s+charging|faulty|swollen)|"
    r"battery's\s+life|battery\s+life|battery\s+problem",
)


def _device_or_product_battery_context(t: str) -> bool:
    """True if 'battery' likely means electronics — not 'assault and battery'."""
    return bool(_DEVICE_OR_PRODUCT_BATTERY.search(t))

_HINDI_ASSAULT = re.compile(r"\b(maar\s*peet|pitai|मारपीट)\b", re.I)

_ATTEMPT_MURDER = re.compile(
    r"\b(attempt\s+to\s+murder|attempted\s+murder|jaan\s+se\s+maarne\s+ki\s+koshish)\b",
    re.I,
)

_CHILD_ABUSE_MINOR = re.compile(r"\b(child\s+abuse|minor\s+abuse)\b", re.I)

_GOV_CERT_ANY = re.compile(
    r"\b(birth|death|income|caste|domicile|residence)\s+certificate\b",
    re.I,
)

_CRIMINAL = [
    (re.compile(r"\b(fraud|cheated|cheating|scam|duped|forgery|dhokha|thagi)\b", re.I), "fraud"),
    (re.compile(r"\b(fir\b|police\s+station|ipc\b|investigation|complaint\s+at\s+station)\b", re.I), "police_report"),
    (re.compile(r"\b(theft|stolen|robbery|burglary|chori)\b", re.I), "theft"),
    # "murder" alone — not "attempt to murder" (handled earlier). Rape/kidnap stay here.
    (re.compile(r"\b(rape|kidnap)\b", re.I), "serious_crime"),
    (re.compile(r"(?<!to )\bmurder\b", re.I), "serious_crime"),
]

_POLICE_OVERSIGHT = re.compile(
    r"\b(fir\s+not\s+registered|police\s+refus|refused\s+to\s+register|no\s+fir|"
    r"police\s+not\s+taking|police\s+misconduct|no\s+action\s+by\s+police|"
    r"police\s+not\s+registering)\b",
    re.I,
)

_RTI = re.compile(
    r"\b(rti\b|right\s+to\s+information|information\s+commission|first\s+appeal\s+rti|pio\b|"
    r"public\s+information\s+officer|information\s+denied)\b",
    re.I,
)

_CIVIC = re.compile(
    r"\b(garbage|sanitation|illegal\s+construction|municipal\s+corporation|"
    r"street\s+lights?|stray\s+dogs?|civic\s+issue)\b",
    re.I,
)

_FINANCIAL = re.compile(
    r"\b(banking\s+ombudsman|rbi\s+ombuds|\brbi\b|ombudsman|bank\s+complaint|banking\s+issue|"
    r"loan\s+harassment|recovery\s+agents?|"
    r"bank\s+not\s+responding|insurance\s+claim\s+reject|cheque\s+bounce|"
    r"nbfc\s+harassment)\b",
    re.I,
)

_SENIOR = re.compile(
    r"\b(senior\s+citizen|maintenance\s+tribunal|1090|elder\s+abuse)\b",
    re.I,
)

_WOMEN_CHILD = re.compile(
    r"(\b1091\b|\b1098\b|child\s+welfare|women\s+helpline|\bCWC\b|childline|posco\s+committee)",
    re.I,
)

_EDUCATION = re.compile(
    r"\b(admission\s+fraud|certificate\s+withheld|school\s+not\s+giving|college\s+withheld|"
    r"marksheet\s+withheld|board\s+withheld\s+certificate)\b",
    re.I,
)

_PROPERTY_RENT = re.compile(
    r"\b(property\s+dispute|rent\s+dispute|tenant|landlord|eviction|lease\s+dispute)\b",
    re.I,
)

_WRONGFUL_TERM = re.compile(r"\b(wrongful\s+termination|illegal\s+termination|fired\s+without)\b", re.I)
_PF_ONLY = re.compile(r"\b(pf\s+not\s+credited|provident\s+fund|epfo|pf\s+withdrawal\s+issue)\b", re.I)
_WORKPLACE_HARASS = re.compile(r"\b(workplace\s+harassment|sexual\s+harassment\s+at\s+work|posh\s+committee)\b", re.I)
_DEFECTIVE = re.compile(r"\b(defective\s+product|defective\s+goods|warranty\s+claim)\b", re.I)
_SERVICE_DEF = re.compile(r"\b(service\s+deficiency|poor\s+service|service\s+not\s+provided)\b", re.I)
_CHALLAN = re.compile(r"\b(challan|e-?challan|traffic\s+ticket)\b", re.I)
_LICENCE = re.compile(r"\b(licen[cs]e\s+renew|dl\s+suspended|driving\s+licen[cs]e\s+issue)\b", re.I)
_ACCIDENT = re.compile(r"\b(motor\s+accident|road\s+accident|hit\s+and\s+run|mact)\b", re.I)
_DIVORCE = re.compile(r"\b(divorce|judicial\s+separation)\b", re.I)
_MAINT = re.compile(r"\b(maintenance\s+under|spousal\s+maintenance|125\s+crpc)\b", re.I)
_CUSTODY = re.compile(r"\b(child\s+custody|custody\s+battle|visitation\s+rights)\b", re.I)
_SERIOUS_FRAUD_MONEY = re.compile(r"\b(large\s+scale\s+fraud|ponzi|multi\s+crore\s+scam)\b", re.I)

_CYBER = [
    re.compile(
        r"\b(cyber|online\s+fraud|phishing|upi\s+fraud|otp\s+(?:scam|fraud)|hacking|data\s+breach)\b",
        re.I,
    ),
    re.compile(r"\b(internet\s+crime|morphing|deepfake|fake\s+profile|identity\s+theft)\b", re.I),
]

_LABOUR = re.compile(
    r"\b(salary|wage|wages|unpaid|not\s+paying|pf\b|provident|gratuity|employer|"
    r"termination|bonus|overtime|factory|industrial|labour|labor|company\s+not\s+paying)\b",
    re.I,
)

_CONSUMER = re.compile(
    r"\b(consumer|defective|warranty|refund|overcharg|fees|service\s+deficiency|cpa\b|complaint\s+against\s+company)\b",
    re.I,
)

# Revenue / records (Tehsildar–SDM path). Generic "property dispute" → civil branch, not land office alone.
_LAND = re.compile(
    r"\b(boundary|mutation|encroachment|survey|title\s+deed|khasra|land\s+records|"
    r"patta|khatauni|jamabandi|revenue\s+department|tehsildar|circle\s+office|"
    r"forcibly|forceful|illegal\s+occupation|occupied\s+by|kabza|kabja)\b|"
    r"(कब्ज़ा|कब्जा|जबरदस्ती|जबरन)",
    re.I,
)

_TRAFFIC = re.compile(
    r"\b(challan|traffic\s+fine|license|licence|dl\b|rto\b|signal|parking\s+violation|rash\s+driving|"
    r"motor\s+accident|road\s+accident|hit\s+and\s+run|\bmact\b)\b",
    re.I,
)

_FAMILY = re.compile(
    r"\b(divorce|custody|maintenance|498a|domestic\s+violence|marriage|alimony)\b",
    re.I,
)

_CORP = re.compile(
    r"\b(nclt|shareholder|share\s+dispute|mca\b|roc\b|oppression|winding\s+up|insolvency|"
    r"private\s+limited|pvt\.?\s*ltd|llp\b|company\s+law|board\s+of\s+directors)\b",
    re.I,
)

_CIVIL_CONTRACT = re.compile(
    r"\b(contract|breach\s+of\s+contract|money\s+recovery|recovery\s+suit|"
    r"civil\s+suit|partition|specific\s+performance)\b",
    re.I,
)

# Threats / violence alongside employment → criminal path (FIR), not labour-only.
_THREAT_CRIMINAL = re.compile(
    r"\b(threat|threatened|intimidat|assault|beat|attack|hurt|harm|kill|weapon|"
    r"fir\b|police|ipc\b|section\s+\d+)\b",
    re.I,
)


# E-commerce / retail: "online" alone must not outrank CPA consumer forums (defect, delay, refund, seller).
_ECOMMERCE_CONSUMER_SHOPPING = re.compile(
    r"\b("
    r"consumer\s+complaint|file\s+a\s+consumer|district\s+consumer|dcdrc|ncdrc|commission\s+complaint|"
    r"defect(ive|)?|refund|warranty|return|replacement|delivery|courier|order\s*numbers?|e-?commerce|e[\s-]?com|"
    r"bought|purchas(ed|e|ing|es)?|flipkart|amazon|meesho|myntra|website|order(?!\s+of\s+court)|\borders?\b|"
    r"seller|unfair\s+trade|deficiency\s+of\s+service|"
    r"overcharg|over\s+pric|invoice"
    r")\b",
    re.I,
)


def _consumer_cpa_retail_purchase_dispute(t: str) -> bool:
    """
    **Goods / services** bought as a consumer (remote order, app, store counter, website, etc.) with a
    grievance (defect, refund, delivery, warranty…). If true, route to **consumer (CPA)** before the
    generic *cyber* path, so “I ordered / I bought + problem” is not the same as *cybercrime*.
    Not limited to e-commerce sites — same idea for any retail purchase + dispute wording.
    """
    low = (t or "").lower()
    if re.search(
        r"\b(hack|hacking|phish|upi\s+fraud|data\s+breach|ransom|kidnap|stolen|theft|rob\w*|rape|molest|assault\w*)\b",
        low,
    ) and "defect" not in low and "warranty" not in low and "refund" not in low:
        return False
    shop = re.search(
        r"(?i)\b(online|web\s*site|e-?com|bought|purchas\w*|order|delivery|seller|flipkart|amazon|meesho|"
        r"myntra|marketplace|e-?commerce|invoice|mobile\s+phone|phone|product|app\s*\.|"
        r"shipment|courier|unfair\s+trade|consumer\s*protection|dcdrc|consumer\s+commission|complaint\s+against|"
        r"₹|rupees?|inr)\b",
        t,
    )
    harm = re.search(
        r"(?i)\bdefect(ive|)?|warranty|refund|return|replace|deficien|"
        r"not\s+working|faulty|late\s+deliver|delay|broken|battery|denied|refus|lemon\b",
        t,
    )
    return bool(shop and harm)


def _cyber_route(t: str) -> bool:
    """Digital / online / identity signals — prefer cyber over physical theft (TASK 6)."""
    low = t.strip()
    if re.search(
        r"\b(online|internet|e-?commerce|e[\s-]?com|digital\s+purchase|app)\b", low, re.I
    ) and _ECOMMERCE_CONSUMER_SHOPPING.search(low):
        # E.g. "bought a phone online … defective" → consumer, not generic cyber/online
        return False
    if any(p.search(t) for p in _CYBER):
        return True
    if re.search(r"\b(online|internet|digital|otp|upi|phishing|hacking|data\s+breach|cyber)\b", t, re.I):
        return True
    if re.search(r"\b(identity\s+theft|fake\s+profile|morphing|deepfake)\b", t, re.I):
        return True
    return False


def _cyber_sub_type(t: str) -> str:
    if re.search(r"\botp\b", t):
        return "otp_fraud"
    if re.search(r"\bupi\b|phishing", t):
        return "upi_fraud"
    if re.search(r"\bhack|data\s+breach|breach\b", t):
        return "hacking"
    if re.search(r"\bidentity|morphing|deepfake|fake\s+profile", t):
        return "identity_theft"
    return "cybercrime_general"


def _assert_domain_issue_alignment(lc: LegalClassification, meta: ClassifierMeta) -> None:
    """Strict guard: non-general domain must not pair with issue_type general (TASK 4)."""
    d = str(meta.get("domain") or "")
    it = str(lc.get("issue_type") or "")
    if d != "general" and it == "general":
        raise ValueError(f"Invalid mapping: domain={d!r} issue_type={it!r}")


def _finish(lc: LegalClassification, meta: ClassifierMeta) -> tuple[LegalClassification, ClassifierMeta]:
    _assert_domain_issue_alignment(lc, meta)
    return lc, meta


def _sev_for(issue: IssueType, strong: bool) -> Severity:
    if issue in ("cyber", "fraud", "police", "police_oversight", "women_child") and strong:
        return "high"
    if issue == "financial" and strong:
        return "high"
    if issue in ("traffic", "consumer") and not strong:
        return "low"
    return "medium"


def _jur(issue: IssueType) -> JurisdictionType:
    if issue == "cyber":
        return "national"
    if issue in ("consumer", "fraud", "corporate", "general", "civil_dispute", "education", "rti", "financial"):
        return "state"
    if issue in ("traffic", "civic"):
        return "local"
    return "district"


def classify_legal_issue(
    text: str,
    entities: list[str] | None = None,
    location: str | None = None,
) -> tuple[LegalClassification, ClassifierMeta]:
    """
    Rule-based classification. Never returns issue_type 'unknown' — uses 'general' as safe fallback.
    entities/location reserved for future boosting; included in trace.
    """
    _ = entities
    _ = location
    raw = (text or "").strip()
    t = raw.lower()

    if not raw:
        meta = ClassifierMeta(
            domain="general",
            sub_type="unspecified",
            category="general",
            fine_intent="empty_input",
            confidence=0.4,
            confidence_score=0.4,
            router_intent="general_issue",
        )
        lc0 = LegalClassification(
            issue_type="general", severity="low", jurisdiction_type="district", sub_type="unspecified"
        )
        return _finish(lc0, meta)

    # --- 1. Attempt to murder (before sexual / missing / theft) ---
    if _ATTEMPT_MURDER.search(t) or _ATTEMPT_MURDER.search(raw):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="attempt_to_murder",
            category="criminal",
            fine_intent="attempt_to_murder",
            confidence=0.98,
            confidence_score=0.98,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="high",
            jurisdiction_type="district",
            sub_type="attempt_to_murder",
        )
        return _finish(lc, meta)

    # --- 2. Sexual offences ---
    if _SEXUAL_OR_SERIOUS_VIOLENCE.search(t) or _SEXUAL_OR_SERIOUS_VIOLENCE.search(raw):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="sexual_offence",
            category="criminal",
            fine_intent="sexual_offence",
            confidence=0.96,
            confidence_score=0.96,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="high",
            jurisdiction_type="district",
            sub_type="sexual_offence",
        )
        return _finish(lc, meta)

    # --- 3. Missing person / abduction ---
    if _MISSING.search(t) or _MISSING.search(raw):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="missing_person",
            category="criminal",
            fine_intent="missing_person",
            confidence=0.97,
            confidence_score=0.97,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="high",
            jurisdiction_type="district",
            sub_type="missing_person",
        )
        return _finish(lc, meta)

    # --- 4. Non-sexual assault (English + Hinglish) ---
    if (
        (_VIOLENT_SIMPLE.search(t) or _HINDI_ASSAULT.search(t))
        and not _device_or_product_battery_context(t)
        and not _SEXUAL_OR_SERIOUS_VIOLENCE.search(t)
    ):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="assault",
            category="criminal",
            fine_intent="assault",
            confidence=0.93,
            confidence_score=0.93,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="high",
            jurisdiction_type="district",
            sub_type="assault",
        )
        return _finish(lc, meta)

    # --- 4.5 Consumer: retail / remote / app purchase + grievance (before generic cyber) ---
    if _consumer_cpa_retail_purchase_dispute(t) or _consumer_cpa_retail_purchase_dispute(raw):
        if _DEFECTIVE.search(t) or re.search(
            r"\b(defect(ive|)?|warranty\s+claim|warranty\s+rejected|faulty|lemon|battery|"
            r"broken|not\s+working|dead\s*on\s*arrival)\b",
            t,
            re.I,
        ):
            csub = "defective_product"
        elif _SERVICE_DEF.search(t) or re.search(
            r"\b(refund|return|replace|delivery|late|delay|shipment|courier|"
            r"deficien|cancel\w*ed?\s*order|order\s+cancel)\b",
            t,
            re.I,
        ):
            csub = "service_deficiency"
        else:
            csub = "consumer_general"
        meta = ClassifierMeta(
            domain="consumer",
            sub_type=csub,
            category="consumer",
            fine_intent="consumer_issue",
            confidence=0.91,
            confidence_score=0.91,
            router_intent="consumer_issue",
        )
        return _finish(
            LegalClassification(
                issue_type="consumer",
                severity="medium",
                jurisdiction_type="state",
                sub_type=csub,
            ),
            meta,
        )

    # --- 5. Cyber / digital / identity (before physical theft; TASK 6) ---
    if _cyber_route(t):
        csub = _cyber_sub_type(t)
        meta = ClassifierMeta(
            domain="cyber",
            sub_type=csub,
            category="criminal",
            fine_intent="cybercrime",
            confidence=0.94,
            confidence_score=0.94,
            router_intent="cyber_fraud",
        )
        lc = LegalClassification(
            issue_type="cyber", severity="high", jurisdiction_type="national", sub_type=csub
        )
        return _finish(lc, meta)

    # --- 6. Physical theft / stolen property (not superseded by cyber route) ---
    if (_THEFT_HARD.search(t) or _THEFT_HARD.search(raw)) and not _cyber_route(t):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="theft",
            category="criminal",
            fine_intent="theft",
            confidence=0.99,
            confidence_score=0.99,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="high",
            jurisdiction_type="district",
            sub_type="theft",
        )
        return _finish(lc, meta)

    # --- 6b. Lost or missing personal article (e.g. wallet/phone) — police / diary path, not `general` ---
    if (
        _LOST_ARTICLE_OBJECT.search(t)
        and _LOST_OR_MISSING_SIGNAL.search(t)
        and not re.search(
            r"\b(stolen|theft|robbed|robbery|burglary|snatched|pickpocket|chori|chor\b|loot|forcibly)\b",
            t,
            re.I,
        )
        and not _cyber_route(t)
    ):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="lost_property",
            category="criminal",
            fine_intent="lost_property",
            confidence=0.86,
            confidence_score=0.86,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="medium",
            jurisdiction_type="district",
            sub_type="lost_property",
        )
        return _finish(lc, meta)

    # --- 7. Police: FIR refusal / misconduct ---
    if _POLICE_OVERSIGHT.search(t):
        sub = "police_misconduct" if re.search(r"misconduct", t) else "police_not_registering_fir"
        meta = ClassifierMeta(
            domain="police_complaint",
            sub_type=sub,
            category="criminal",
            fine_intent=sub,
            confidence=0.9,
            confidence_score=0.9,
            router_intent="police_oversight",
        )
        lc = LegalClassification(
            issue_type="police_oversight",
            severity="high",
            jurisdiction_type="district",
            sub_type=sub,
        )
        return _finish(lc, meta)

    # --- Labour + criminal threat (salary + assault/threat) → police / FIR primary ---
    if _LABOUR.search(t) and _THREAT_CRIMINAL.search(t):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="labour_with_threat",
            category="criminal",
            fine_intent="labour_with_criminal_threat",
            confidence=0.9,
            confidence_score=0.9,
            router_intent="criminal_police",
        )
        return (
            LegalClassification(
                issue_type="police",
                severity="high",
                jurisdiction_type="district",
                sub_type="labour_with_threat",
            ),
            meta,
        )

    # --- Corporate / shares (before labour — "company" can appear in both) ---
    if _CORP.search(t):
        meta = ClassifierMeta(
            domain="civil",
            sub_type="contract_dispute",
            category="civil_commercial",
            fine_intent="share_dispute",
            confidence=0.9,
            confidence_score=0.9,
            router_intent="share_dispute",
        )
        return (
            LegalClassification(
                issue_type="corporate", severity="medium", jurisdiction_type="state", sub_type="share_dispute"
            ),
            meta,
        )

    # --- Consumer: high fees / overcharging (before plain labour) ---
    if _FEES_CONSUMER.search(t) and not _THREAT_CRIMINAL.search(t):
        meta = ClassifierMeta(
            domain="consumer",
            sub_type="education_fees",
            category="consumer",
            fine_intent="fees_dispute",
            confidence=0.82,
            confidence_score=0.82,
            router_intent="consumer_issue",
        )
        return (
            LegalClassification(
                issue_type="consumer", severity="medium", jurisdiction_type="state", sub_type="education_fees"
            ),
            meta,
        )

    # --- Education grievance ---
    if _EDUCATION.search(t):
        edu_sub = "admission_fraud" if re.search(r"admission|fraud", t) else "certificate_withheld"
        meta = ClassifierMeta(
            domain="education",
            sub_type=edu_sub,
            category="consumer",
            fine_intent="education",
            confidence=0.84,
            confidence_score=0.84,
            router_intent="education_dispute",
        )
        lc = LegalClassification(
            issue_type="education", severity="medium", jurisdiction_type="state", sub_type=edu_sub
        )
        return _finish(lc, meta)

    # --- Women / child helpline + child abuse intake (after education; before senior) ---
    if (_WOMEN_CHILD.search(t) or _CHILD_ABUSE_MINOR.search(t)) and not _SEXUAL_OR_SERIOUS_VIOLENCE.search(t):
        wc_sub = (
            "abuse"
            if (_CHILD_ABUSE_MINOR.search(t) or re.search(r"\babuse\b|child\s+abuse", t))
            else "harassment"
        )
        wc_conf = 0.86 if _CHILD_ABUSE_MINOR.search(t) else 0.84
        meta = ClassifierMeta(
            domain="women_child",
            sub_type=wc_sub,
            category="family",
            fine_intent="women_child",
            confidence=wc_conf,
            confidence_score=wc_conf,
            router_intent="women_child_route",
        )
        lc = LegalClassification(
            issue_type="women_child",
            severity="medium",
            jurisdiction_type="district",
            sub_type=wc_sub,
        )
        return _finish(lc, meta)

    # --- Senior citizen maintenance ---
    if _SENIOR.search(t):
        meta = ClassifierMeta(
            domain="senior_citizen",
            sub_type="maintenance_claim",
            category="family",
            fine_intent="senior_maintenance",
            confidence=0.85,
            confidence_score=0.85,
            router_intent="senior_maintenance",
        )
        lc = LegalClassification(
            issue_type="senior_citizen",
            severity="medium",
            jurisdiction_type="district",
            sub_type="maintenance_claim",
        )
        return _finish(lc, meta)

    # --- Workplace harassment / POSH (labour forum even if salary words absent) ---
    if _WORKPLACE_HARASS.search(t) and not _THREAT_CRIMINAL.search(t):
        meta = ClassifierMeta(
            domain="labour",
            sub_type="workplace_harassment",
            category="labour",
            fine_intent="workplace_harassment",
            confidence=0.87,
            confidence_score=0.87,
            router_intent="salary_issue",
        )
        return (
            LegalClassification(
                issue_type="salary", severity="medium", jurisdiction_type="district", sub_type="workplace_harassment"
            ),
            meta,
        )

    # --- Labour ---
    if _LABOUR.search(t) and not re.search(r"\b(rent|tenant|landlord|lease|eviction)\b", t):
        if _WORKPLACE_HARASS.search(t):
            lsub = "workplace_harassment"
        elif _WRONGFUL_TERM.search(t):
            lsub = "wrongful_termination"
        elif _PF_ONLY.search(t) or (re.search(r"\bpf\b", t) and not re.search(r"salary|wage", t)):
            lsub = "pf_issue"
        else:
            lsub = "salary_not_paid"
        meta = ClassifierMeta(
            domain="labour",
            sub_type=lsub,
            category="labour",
            fine_intent="salary_issue",
            confidence=0.9,
            confidence_score=0.9,
            router_intent="salary_issue",
        )
        return (
            LegalClassification(issue_type="salary", severity="medium", jurisdiction_type="district", sub_type=lsub),
            meta,
        )

    # --- Consumer ---
    if _CONSUMER.search(t):
        if _DEFECTIVE.search(t):
            csub = "defective_product"
        elif _SERVICE_DEF.search(t):
            csub = "service_deficiency"
        elif re.search(r"overcharg|fees", t):
            csub = "overcharging"
        else:
            csub = "consumer_general"
        meta = ClassifierMeta(
            domain="consumer",
            sub_type=csub,
            category="consumer",
            fine_intent="consumer_issue",
            confidence=0.88,
            confidence_score=0.88,
            router_intent="consumer_issue",
        )
        return (
            LegalClassification(
                issue_type="consumer", severity="medium", jurisdiction_type="state", sub_type=csub
            ),
            meta,
        )

    # --- Land / government records (skip when civic/municipal cues win — e.g. illegal construction + encroachment + civic) ---
    if (
        _LAND.search(t)
        or (
            _GOV_CERT_ANY.search(t)
            and re.search(r"\b(delay|pending|not\s+issued|held|withheld|ward|office|online|portal)\b", t, re.I)
        )
    ) and not _CIVIC.search(t):
        if re.search(r"mutation|khasra|jamabandi", t):
            gsub = "mutation_issue"
        elif re.search(
            r"\b(birth|death|income|caste|domicile|residence)\s+certificate\b",
            t,
        ) and (
            re.search(r"\b(tehsil|sdm|collector|revenue\s+department)\b", t)
            or re.search(r"\b(delay|pending|not\s+issued|held|withheld|ward|office|online|portal)\b", t, re.I)
        ):
            gsub = "certificate_issue"
        else:
            gsub = "land_records"
        meta = ClassifierMeta(
            domain="government",
            sub_type=gsub,
            category="land_revenue",
            fine_intent="land_dispute",
            confidence=0.88,
            confidence_score=0.88,
            router_intent="land_dispute",
        )
        return (
            LegalClassification(issue_type="land", severity="medium", jurisdiction_type="district", sub_type=gsub),
            meta,
        )

    # --- Traffic ---
    if _TRAFFIC.search(t):
        if _ACCIDENT.search(t):
            tsub = "accident"
        elif _LICENCE.search(t):
            tsub = "licence_issue"
        elif _CHALLAN.search(t):
            tsub = "challan_dispute"
        else:
            tsub = "traffic_general"
        meta = ClassifierMeta(
            domain="traffic",
            sub_type=tsub,
            category="traffic",
            fine_intent="traffic_violation",
            confidence=0.88,
            confidence_score=0.88,
            router_intent="traffic_violation",
        )
        return (
            LegalClassification(issue_type="traffic", severity="low", jurisdiction_type="local", sub_type=tsub),
            meta,
        )

    # --- Family ---
    if _FAMILY.search(t):
        if _DIVORCE.search(t):
            fsub = "divorce"
        elif re.search(r"498a|domestic\s+violence|dv\b", t):
            fsub = "domestic_violence"
        elif _CUSTODY.search(t):
            fsub = "child_custody"
        elif _MAINT.search(t):
            fsub = "maintenance"
        else:
            fsub = "family_general"
        meta = ClassifierMeta(
            domain="family",
            sub_type=fsub,
            category="family",
            fine_intent="family_matters",
            confidence=0.88,
            confidence_score=0.88,
            router_intent="family_matters",
        )
        return (
            LegalClassification(issue_type="family", severity="medium", jurisdiction_type="district", sub_type=fsub),
            meta,
        )

    # --- Civil: property / rent ---
    if _PROPERTY_RENT.search(t) and not (_LAND.search(t) or _GOV_CERT_ANY.search(t)):
        psub = "rent_issue" if re.search(r"rent|tenant|landlord|lease|eviction", t) else "property_dispute"
        meta = ClassifierMeta(
            domain="civil",
            sub_type=psub,
            category="civil",
            fine_intent="property_civil",
            confidence=0.74,
            confidence_score=0.74,
            router_intent="civil_dispute",
        )
        lc = LegalClassification(
            issue_type="civil_dispute", severity="medium", jurisdiction_type="state", sub_type=psub
        )
        return _finish(lc, meta)

    # --- Civil contract / civil suit (not corporate-specific; not police unless criminal keywords exist elsewhere) ---
    if _CIVIL_CONTRACT.search(t):
        csub = "money_recovery" if re.search(r"money\s+recovery|recovery", t) else "contract_dispute"
        meta = ClassifierMeta(
            domain="civil",
            sub_type=csub,
            category="civil",
            fine_intent="contract_dispute",
            confidence=0.72,
            confidence_score=0.72,
            router_intent="civil_dispute",
        )
        lc = LegalClassification(
            issue_type="civil_dispute",
            severity="medium",
            jurisdiction_type="state",
            sub_type=csub,
        )
        return _finish(lc, meta)

    # --- Financial: banking / loan / insurance (after civil per routing ladder) ---
    if _FINANCIAL.search(t):
        meta = ClassifierMeta(
            domain="financial",
            sub_type="banking_dispute",
            category="financial",
            fine_intent="banking_dispute",
            confidence=0.86,
            confidence_score=0.86,
            router_intent="banking_ombudsman",
        )
        sev: Severity = "high" if _SERIOUS_FRAUD_MONEY.search(t) else "medium"
        lc = LegalClassification(
            issue_type="financial",
            severity=sev,
            jurisdiction_type="state",
            sub_type="loan_harassment" if re.search(r"loan|recovery|nbfc", t) else "banking_dispute",
        )
        return _finish(lc, meta)

    # --- RTI ---
    if _RTI.search(t):
        rti_sub = "information_denied" if re.search(r"denied|reject", t) else "rti_application"
        meta = ClassifierMeta(
            domain="rti",
            sub_type=rti_sub,
            category="administrative",
            fine_intent="rti",
            confidence=0.88,
            confidence_score=0.88,
            router_intent="rti_grievance",
        )
        lc = LegalClassification(issue_type="rti", severity="medium", jurisdiction_type="state", sub_type=rti_sub)
        return _finish(lc, meta)

    # --- Civic / municipal ---
    if _CIVIC.search(t):
        if re.search(r"street\s+lights?", t):
            civic_sub = "streetlight_issue"
        elif re.search(r"garbage|sanitation|dog", t):
            civic_sub = "garbage_issue"
        else:
            civic_sub = "illegal_construction"
        meta = ClassifierMeta(
            domain="civic",
            sub_type=civic_sub,
            category="administrative",
            fine_intent="civic",
            confidence=0.82,
            confidence_score=0.82,
            router_intent="civic_local",
        )
        lc = LegalClassification(
            issue_type="civic", severity="medium", jurisdiction_type="local", sub_type=civic_sub
        )
        return _finish(lc, meta)

    # --- Criminal (after sectoral buckets so e.g. "consumer fraud" → consumer) ---
    for pat, label in _CRIMINAL:
        if pat.search(t):
            if label == "fraud":
                fi = "fraud"
                sub = "fraud_general"
                it: IssueType = "fraud"
                router = "fraud_general"
            elif label == "theft":
                fi = "theft"
                sub = "theft"
                it = "police"
                router = "criminal_police"
            elif label == "serious_crime":
                fi = "serious_crime"
                sub = "serious_crime"
                it = "police"
                router = "criminal_police"
            else:
                fi = "police_report"
                sub = "police_report"
                it = "police"
                router = "criminal_police"
            meta = ClassifierMeta(
                domain="criminal",
                sub_type=sub,
                category="criminal",
                fine_intent=fi,
                confidence=0.95,
                confidence_score=0.95,
                router_intent=router,
            )
            strong = True
            if label == "fraud" and _SERIOUS_FRAUD_MONEY.search(t):
                sev2: Severity = "high"
            else:
                sev2 = _sev_for(it, strong)
            return (
                LegalClassification(
                    issue_type=it,
                    severity=sev2,
                    jurisdiction_type=_jur(it),
                    sub_type=sub,
                ),
                meta,
            )

    # --- Lost article after user clarified "lost / misplaced" (NCR / diary path — not theft FIR) ---
    _lost_item_word = re.search(
        r"\b(wallet|phone|mobile|iphone|android|laptop|keys|keychain|bag|purse|watch)\b",
        t,
    )
    _lost_only_followup = re.search(
        r"(?:additional\s+detail|my\s+choice).{0,280}?"
        r"(?:lost\s*/\s*misplaced|lost/misplaced|only\s+lost|not\s+stolen|misplaced\s+only|"
        r"lost\s+article|general\s+diary|\bncr\b)",
        t,
        re.DOTALL | re.I,
    )
    if (
        _lost_item_word
        and _lost_only_followup
        and not re.search(r"\b(stolen|theft|robbed|snatched|pickpocket|chori|chor\b|loot)\b", t)
    ):
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="lost_property",
            category="criminal",
            fine_intent="lost_property",
            confidence=0.78,
            confidence_score=0.78,
            router_intent="criminal_police",
        )
        lc = LegalClassification(
            issue_type="police",
            severity="medium",
            jurisdiction_type="district",
            sub_type="lost_property",
        )
        return _finish(lc, meta)

    # --- Keyword catch-all: weak signals ---
    weak_criminal = re.search(r"\b(crime|illegal|stolen|thief|police)\b", t)
    if weak_criminal:
        meta = ClassifierMeta(
            domain="criminal",
            sub_type="general_criminal",
            category="criminal",
            fine_intent="general_criminal",
            confidence=0.62,
            confidence_score=0.62,
            router_intent="criminal_police",
        )
        return (
            LegalClassification(
                issue_type="police",
                severity="medium",
                jurisdiction_type="district",
                sub_type="general_criminal",
            ),
            meta,
        )

    # --- DEFAULT: never unknown ---
    meta = ClassifierMeta(
        domain="general",
        sub_type="general_guidance",
        category="general",
        fine_intent="general_guidance",
        confidence=0.55,
        confidence_score=0.55,
        router_intent="general_issue",
    )
    return (
        LegalClassification(
            issue_type="general", severity="low", jurisdiction_type="district", sub_type="general_guidance"
        ),
        meta,
    )
