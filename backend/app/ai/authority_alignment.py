"""
Hard checks: deterministic routing vs draft text. LLM output must not override police/FIR path for criminal matters.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.legal_classifier import ClassifierMeta
from app.services.legal_taxonomy import LegalClassification

_FORBIDDEN_PRIMARY_FOR_CRIMINAL = re.compile(
    r"\bto\s*,?\s*(?:the\s+)?(?:dear\s+)?(?:"
    r"labour\s+commissioner|assistant\s+labour|consumer\s+commission|district\s+consumer|"
    r"tehsildar|district\s+collector|collector\s+office|district\s+magistrate|"
    r"revenue\s+officer|nclt\b"
    r")\b",
    re.I,
)

_POLICE_FORUM_MARKERS = re.compile(
    r"\b(?:"
    r"police\s+station|SHO|station\s+house\s+officer|"
    r"FIR|first\s+information|"
    r"superintendent\s+of\s+police|\bSP\b|DCP|ACP|"
    r"cybercrime\.gov|national\s+cyber\s+crime|"
    r"cognizable|written\s+complaint"
    r")\b",
    re.I,
)

_CYBER_MARKERS = re.compile(
    r"\b(cybercrime\.gov|cyber\s+crime|cyber\s+cell|national\s+cyber|police\s+station)\b",
    re.I,
)

_POLICE_ESCALATION_MARKERS = re.compile(
    r"\b(superintendent\s+of\s+police|\bSP\b|DCP|deputy\s+commissioner\s+of\s+police|"
    r"judicial\s+magistrate|magistrate\s+court|FIR\s+not\s+registered|refused\s+to\s+register|"
    r"complaint\s+to\s+magistrate)\b",
    re.I,
)

_CIVIL_COURT_MARKERS = re.compile(
    r"\b(civil\s+court|district\s+court|civil\s+suit|plaint|recovery\s+suit)\b",
    re.I,
)

_SHO_LETTER_OPENING = re.compile(
    r"\bto\s*,?\s*(?:the\s+)?(?:dear\s+)?(?:station\s+house\s+officer|\bSHO\b)\b",
    re.I,
)


def _requires_police_primary_forum(meta: ClassifierMeta, taxonomy: LegalClassification) -> bool:
    ri = str(meta.get("router_intent") or "")
    cat = str(meta.get("category") or "")
    it = str(taxonomy.get("issue_type") or "")
    if ri in ("criminal_police", "fraud_general"):
        return True
    if cat == "criminal" and it in ("police", "fraud"):
        return True
    return False


def _requires_cyber_plus_police(meta: ClassifierMeta) -> bool:
    return str(meta.get("router_intent") or "") == "cyber_fraud"


def _requires_police_oversight_escalation_forum(meta: ClassifierMeta) -> bool:
    return str(meta.get("router_intent") or "") == "police_oversight"


def _requires_civil_court_primary(meta: ClassifierMeta) -> bool:
    ri = str(meta.get("router_intent") or "")
    dom = str(meta.get("domain") or "")
    cat = str(meta.get("category") or "")
    fi = str(meta.get("fine_intent") or "")
    if ri == "civil_dispute":
        return True
    return dom == "civil" and cat == "civil" and fi in ("property_civil", "contract_dispute")


def document_violates_authority_alignment(
    document: str,
    *,
    classifier_meta: ClassifierMeta,
    taxonomy: LegalClassification,
) -> tuple[bool, str]:
    """
    Returns (violates, reason). If True, caller should REGENERATE — deterministic routing wins over LLM.
    """
    doc = (document or "").strip()
    if not doc or len(doc) < 30:
        return False, ""

    head = doc[:2200]

    if bool(classifier_meta.get("is_hybrid")) and bool(classifier_meta.get("hybrid_police_primary")):
        doc_window = doc[:8000]
        if not _POLICE_FORUM_MARKERS.search(doc_window) or not _CIVIL_COURT_MARKERS.search(doc_window):
            return True, "hybrid_police_primary_missing_police_or_civil_section"
        if re.search(
            r"\bto\s*,?\s*(?:the\s+)?(?:dear\s+)?(?:tehsildar|sub[-\s]?divisional\s+magistrate)\b",
            head,
            re.I,
        ) and not _POLICE_FORUM_MARKERS.search(head[:3200]):
            return True, "hybrid_police_tehsildar_primary_without_police"
        return False, ""

    # Civil / contract recovery: primary forum is civil court — not SHO-only police letter.
    if _requires_civil_court_primary(classifier_meta):
        if bool(classifier_meta.get("is_hybrid")):
            doc_window = doc[:8000]
            if not _CIVIL_COURT_MARKERS.search(doc_window) or not _POLICE_FORUM_MARKERS.search(doc_window):
                return True, "hybrid_case_missing_civil_or_police_section"
            return False, ""
        if _SHO_LETTER_OPENING.search(head) and not _CIVIL_COURT_MARKERS.search(head):
            return True, "civil_dispute_routed_as_police_fir_primary"
        return False, ""

    # FIR refusal / police misconduct: SP/DCP/Magistrate track — not Labour/Consumer/Collector as sole addressee.
    if _requires_police_oversight_escalation_forum(classifier_meta):
        if _FORBIDDEN_PRIMARY_FOR_CRIMINAL.search(head) and not _POLICE_ESCALATION_MARKERS.search(head[:1200]):
            return True, "police_oversight_wrong_primary_forum"
        if not _POLICE_ESCALATION_MARKERS.search(head):
            return True, "police_oversight_missing_sp_dcp_or_magistrate_language"
        return False, ""

    if _requires_cyber_plus_police(classifier_meta):
        if not _CYBER_MARKERS.search(head):
            return True, "cyber_route_missing_portal_or_police"
        return False, ""

    if not _requires_police_primary_forum(classifier_meta, taxonomy):
        return False, ""

    if _FORBIDDEN_PRIMARY_FOR_CRIMINAL.search(head) and not _POLICE_FORUM_MARKERS.search(head[:900]):
        return True, "criminal_wrong_primary_forum_without_police"

    if not _POLICE_FORUM_MARKERS.search(head):
        return True, "criminal_missing_police_sho_or_fir_language"

    return False, ""


def authority_block_suggested_mismatch(
    authority_block: dict[str, Any],
    *,
    classifier_meta: ClassifierMeta,
    taxonomy: LegalClassification,
) -> tuple[bool, str]:
    """Extra check on suggested primary string (graph-sourced; should rarely fail)."""
    if authority_block.get("status") == "verified":
        return False, ""
    primary = str(authority_block.get("primary") or "").lower()
    secondary = str(authority_block.get("secondary") or "").lower()
    if bool(classifier_meta.get("hybrid_police_primary")):
        if "police" not in primary and "station" not in primary and "fir" not in primary:
            return True, "hybrid_police_primary_suggested_without_police"
        if "civil" not in secondary and "court" not in secondary:
            return True, "hybrid_police_primary_suggested_without_civil_secondary"
        if "tehsildar" in primary and "police" not in primary:
            return True, "hybrid_police_tehsildar_suggested_primary"
        return False, ""
    if not _requires_police_primary_forum(classifier_meta, taxonomy):
        return False, ""
    dom = str(classifier_meta.get("domain") or "").lower()
    if dom == "criminal" and not (
        "police" in primary or "station" in primary or "fir" in primary or "cyber" in primary
    ):
        return True, "criminal_domain_suggested_without_police_primary"
    bad_substrings = (
        "labour commissioner",
        "consumer commission",
        "district collector",
        "district administration",
        "tehsildar",
    )
    if any(b in primary for b in bad_substrings) and "police" not in primary and "fir" not in primary:
        return True, "authority_primary_string_non_police_for_criminal"
    return False, ""


def verified_authority_breaks_domain_alignment(
    verified: dict[str, Any] | None,
    *,
    classifier_meta: ClassifierMeta,
    user_input: str = "",
) -> tuple[bool, str]:
    """
    True when a verified directory row's office_type is incompatible with classifier domain/router
    (e.g. criminal domain but Labour office). Callers should discard the verified row and fall back to graph.
    """
    from app.authority import strict_authority_passes_domain_gate

    if not verified:
        return False, ""
    if not strict_authority_passes_domain_gate(
        verified.get("office_type"),
        router_intent=classifier_meta.get("router_intent"),
        domain=classifier_meta.get("domain"),
        user_input=user_input,
    ):
        return True, "verified_office_type_incompatible_with_domain_router"
    return False, ""
