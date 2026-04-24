"""Detect civil/land issues with criminal-style facts — dual routing (no LLM)."""

from __future__ import annotations

import re

from app.core.legal_classifier import ClassifierMeta
from app.services.clarification_followup import parse_followup_signals
from app.services.legal_taxonomy import LegalClassification
from app.services.priority_engine import enrich_classifier_meta_with_priority

# Strict land/property context — hybrid civil–criminal routing must NOT leak without these.
LAND_KEYWORDS_STRICT = (
    "land",
    "property",
    "plot",
    "khasra",
    "kabza",
    "kabja",
    "qabza",
    "encroachment",
    "possession",
    "registry",
)


def detect_land_context(text: str) -> bool:
    """True only when user text clearly concerns land/property (anti hybrid hallucination)."""
    raw = (text or "").strip()
    if not raw:
        return False
    low = raw.lower()
    if any(w in low for w in LAND_KEYWORDS_STRICT):
        return True
    if "कब्ज़ा" in raw or "कब्जा" in raw:
        return True
    return bool(_LANDISH.search(raw))


def _strip_hybrid_if_no_land_context(user_text: str, meta: ClassifierMeta) -> ClassifierMeta:
    """No land context → never advertise civil/land hybrid paths."""
    if not bool(meta.get("is_hybrid")):
        return meta
    if detect_land_context(user_text):
        return meta
    m: dict = {**meta, "is_hybrid": False}
    m.pop("secondary_domain", None)
    m.pop("hybrid_police_primary", None)
    m.pop("hybrid_routing_type", None)
    return m  # type: ignore[return-value]


# Force / occupation / threat cues → parallel police track alongside civil or revenue.
_HYBRID_CRIMINAL_CUES = re.compile(
    r"\b(forcefully|forcible|forcibly|threat|threatened|violence|violent|occupied|occupying|occupation|"
    r"encroachment|trespass|kabza|kabja|illegal\s+occupation)\b|"
    r"(कब्ज़ा|कब्जा|जबरदस्ती|धमकी|हिंसा|जबरन|कब्ज़)",
    re.I,
)

_LANDISH = re.compile(
    r"\b(land|plot|farm|field|acre|zameen|jameen|boundary|mutation|khasra|patta|khatauni|jamabandi|"
    r"property|possession|title|agrah|encroach)\b|"
    r"(जमीन|ज़मीन|भूमि)",
    re.I,
)


def hybrid_criminal_cues_match(user_text: str) -> bool:
    if not (user_text or "").strip():
        return False
    s = user_text.strip()
    return bool(_HYBRID_CRIMINAL_CUES.search(s) or _HYBRID_CRIMINAL_CUES.search(s.lower()))


def _eligible_for_hybrid(meta: ClassifierMeta, lc: LegalClassification) -> bool:
    ri = str(meta.get("router_intent") or "").lower()
    it = str(lc.get("issue_type") or "").lower()
    dom = str(meta.get("domain") or "").lower()
    if ri in ("civil_dispute", "land_dispute"):
        return True
    if it in ("civil_dispute", "land"):
        return True
    if dom in ("civil", "government"):
        return True
    return False


def _upgrade_general_land_with_cues(
    user_text: str, lc: LegalClassification, meta: ClassifierMeta
) -> tuple[LegalClassification, ClassifierMeta]:
    """Escape weak `general` bucket when land + force/kabza cues are present."""
    if str(meta.get("router_intent") or "") != "general_issue":
        return lc, meta
    if not hybrid_criminal_cues_match(user_text):
        return lc, meta
    if not _LANDISH.search(user_text):
        return lc, meta
    t = user_text.lower()
    c = max(0.86, float(meta.get("confidence") or 0), float(meta.get("confidence_score") or 0))
    meta2: ClassifierMeta = {
        **meta,
        "domain": "civil",
        "sub_type": "forceful_land_occupation",
        "category": "civil",
        "fine_intent": "property_civil",
        "router_intent": "civil_dispute",
        "confidence": c,
        "confidence_score": c,
    }
    lc2: LegalClassification = {
        **lc,
        "issue_type": "civil_dispute",
        "severity": "high" if re.search(r"threat|violence|धमकी|हिंसा", t) else "medium",
        "jurisdiction_type": "district",
        "sub_type": "forceful_land_occupation",
    }
    return lc2, meta2


def _maybe_reclass_land_to_civil_for_force(user_text: str, lc: LegalClassification, meta: ClassifierMeta) -> tuple[LegalClassification, ClassifierMeta]:
    """
    Land-revenue router is correct for pure records; force/kabza/encroachment should not read as tehsildar-only.
    """
    if str(meta.get("router_intent") or "") != "land_dispute":
        return lc, meta
    if not hybrid_criminal_cues_match(user_text):
        return lc, meta
    t = user_text.lower()
    c = max(0.86, float(meta.get("confidence") or 0), float(meta.get("confidence_score") or 0))
    meta2: ClassifierMeta = {
        **meta,
        "domain": "civil",
        "category": "civil",
        "router_intent": "civil_dispute",
        "fine_intent": "property_civil",
        "sub_type": "forceful_land_occupation",
        "confidence": c,
        "confidence_score": c,
    }
    lc2: LegalClassification = {
        **lc,
        "issue_type": "civil_dispute",
        "sub_type": "forceful_land_occupation",
        "severity": "high" if re.search(r"threat|violence|धमकी|हिंसा", t) else "medium",
        "jurisdiction_type": "district",
    }
    return lc2, meta2


def _is_land_or_civil_dispute_ctx(meta: ClassifierMeta, lc: LegalClassification, user_text: str) -> bool:
    ri = str(meta.get("router_intent") or "").lower()
    it = str(lc.get("issue_type") or "").lower()
    st = str(lc.get("sub_type") or "").lower()
    if ri in ("land_dispute", "civil_dispute"):
        return True
    if it in ("civil_dispute", "land"):
        return True
    if "land" in st or "property" in st or "dispute" in st:
        return True
    return bool(_LANDISH.search(user_text))


def apply_hybrid_civil_criminal_overlay(
    user_text: str,
    lc: LegalClassification,
    meta: ClassifierMeta,
) -> tuple[LegalClassification, ClassifierMeta]:
    meta = enrich_classifier_meta_with_priority(user_text, meta)
    lc0, meta0 = _upgrade_general_land_with_cues(user_text, lc, meta)
    lc1, meta1 = _maybe_reclass_land_to_civil_for_force(user_text, lc0, meta0)
    sig = parse_followup_signals(user_text)
    if sig.no_force_peaceful:
        if sig.documents_yes:
            c0 = max(0.88, float(meta1.get("confidence") or 0), float(meta1.get("confidence_score") or 0))
            return lc1, {**meta1, "confidence": c0, "confidence_score": c0}
        return lc1, meta1
    if not hybrid_criminal_cues_match(user_text):
        if sig.documents_yes:
            c0 = max(0.88, float(meta1.get("confidence") or 0), float(meta1.get("confidence_score") or 0))
            return lc1, {**meta1, "confidence": c0, "confidence_score": c0}
        return lc1, meta1
    if not _eligible_for_hybrid(meta1, lc1):
        if sig.documents_yes:
            c0 = max(0.88, float(meta1.get("confidence") or 0), float(meta1.get("confidence_score") or 0))
            return lc1, {**meta1, "confidence": c0, "confidence_score": c0}
        return lc1, meta1
    c = max(0.86, float(meta1.get("confidence") or 0), float(meta1.get("confidence_score") or 0))
    if sig.documents_yes:
        c = max(c, 0.88)
    meta_out: ClassifierMeta = {
        **meta1,
        "confidence": c,
        "confidence_score": c,
        "secondary_domain": "criminal",
        "is_hybrid": True,
    }
    lc_out: LegalClassification = {**lc1}
    meta_out = _strip_hybrid_if_no_land_context(user_text, meta_out)
    return lc_out, meta_out


def apply_law_and_order_land_hybrid_merge(
    user_text: str,
    lc: LegalClassification,
    meta: ClassifierMeta,
) -> tuple[LegalClassification, ClassifierMeta]:
    """
    Law-and-order + land/civil: police-first hybrid; Tehsildar never sole primary; civil court always in path.
    """
    if str(meta.get("phase6_priority") or "") != "law_and_order":
        return lc, meta
    if not bool(meta.get("phase6_priority_override")):
        return lc, meta
    if not detect_land_context(user_text):
        return lc, meta
    if not _is_land_or_civil_dispute_ctx(meta, lc, user_text):
        return lc, meta
    c = max(
        0.9,
        float(meta.get("confidence") or 0),
        float(meta.get("confidence_score") or 0),
    )
    meta_out: ClassifierMeta = {
        **meta,
        "is_hybrid": True,
        "hybrid_police_primary": True,
        "hybrid_routing_type": "hybrid_civil_criminal",
        "secondary_domain": "civil",
        "confidence": c,
        "confidence_score": c,
    }
    return {**lc}, meta_out
