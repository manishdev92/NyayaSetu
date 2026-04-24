"""
Phase 6 logical agents — thin wrappers over existing classifier + formatter/evaluator.

Classifier output is derived from taxonomy + meta (no second LLM).
"""

from __future__ import annotations

from typing import Any

from app.services.output_formatter import evaluate_response_bundle


def normalize_phase6_issue_type(
    *,
    issue_type: str,
    domain: str,
    sub_type: str,
) -> str:
    """Coarse slug for clients: police / civil / land / traffic / consumer / unknown."""
    it = (issue_type or "").strip().lower()
    dom = (domain or "").strip().lower()
    st = (sub_type or "").strip().lower()

    if it in ("police", "police_oversight") or dom in ("criminal",):
        return "police"
    if it == "traffic" or dom == "traffic":
        return "traffic"
    if it == "consumer" or dom == "consumer":
        return "consumer"
    if it == "land" or dom in ("land_revenue",) or "land" in st:
        return "land"
    if it in ("civil_dispute", "salary") or dom in ("civil", "labour", "employment"):
        return "civil"
    if it in ("general", "education", "rti", "financial", "corporate", "civic"):
        return "unknown"
    if it == "cyber":
        return "police"
    return "unknown"


def classifier_agent_snapshot(
    taxonomy_ui: dict[str, Any],
    classifier_meta: dict[str, Any] | Any,
) -> dict[str, Any]:
    meta = dict(classifier_meta) if not isinstance(classifier_meta, dict) else classifier_meta
    sev = str(taxonomy_ui.get("severity") or meta.get("severity") or "medium").lower()
    if sev not in ("low", "medium", "high", "emergency"):
        sev = "high" if meta.get("is_emergency") else "medium"
    return {
        "issue_type": normalize_phase6_issue_type(
            issue_type=str(taxonomy_ui.get("issue_type") or ""),
            domain=str(meta.get("domain") or ""),
            sub_type=str(taxonomy_ui.get("sub_type") or meta.get("sub_type") or ""),
        ),
        "severity": sev,
        "is_hybrid": bool(meta.get("is_hybrid")),
    }


def map_phase6_intent_bucket(
    *,
    taxonomy_ui: dict[str, Any],
    classifier_meta: dict[str, Any],
    emergency_layer: dict[str, Any] | None = None,
) -> str:
    """
    High-level triage bucket for clients (criminal / civil / emergency / cybercrime / women_safety / …).
    """
    layer = emergency_layer or {}
    if bool(layer.get("bypass_recommended")):
        return "emergency"
    dom = str(classifier_meta.get("domain") or "").lower()
    it = str(taxonomy_ui.get("issue_type") or "").lower()
    cat = str(classifier_meta.get("category") or "").lower()
    if dom == "cyber" or it == "cyber":
        return "cybercrime"
    if dom == "women_child" or it == "women_child":
        return "women_safety"
    if it in ("police", "police_oversight") or dom == "criminal" or cat == "criminal":
        return "criminal"
    if dom == "traffic" or it == "traffic":
        return "traffic"
    if it == "consumer" or dom == "consumer":
        return "consumer"
    if dom in ("land_revenue",) or it == "land":
        return "civil"
    if it in ("civil_dispute", "salary", "corporate", "financial", "education", "rti") or dom in (
        "civil",
        "labour",
        "education",
        "corporate",
    ):
        return "civil"
    if it in ("general", "civic"):
        return "unknown"
    return "unknown"


def evaluator_agent_finalize(
    *,
    document: str,
    explanation: str,
    next_steps: list[str],
    meta: dict[str, Any],
    alert: str | None = None,
) -> tuple[str, str, list[str]]:
    """Public name for the evaluator step; delegates to `evaluate_response_bundle`."""
    return evaluate_response_bundle(
        document=document,
        explanation=explanation,
        next_steps=next_steps,
        meta=meta,
        alert=alert,
    )
