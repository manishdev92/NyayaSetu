from __future__ import annotations

from typing import TypedDict

from app.authority import StrictAuthority
from app.services.district_entity import normalize_place_token
from app.services.trust_engine import VERIFIED_AUTHORITY_MIN_SCORE


class AuthorityGateResult(TypedDict):
    approved: bool
    final_score: float
    issues: list[str]


def evaluate_strict_authority_gate(
    *,
    authority: StrictAuthority | None,
    trust_score: float,
    source_label: str | None,
    internal_resolution: bool,
    user_district_normalized: str | None,
) -> AuthorityGateResult:
    """
    Final gate: verification status, score floor, source class, district integrity (external only).
    """
    if authority is None:
        return AuthorityGateResult(approved=False, final_score=0.0, issues=["missing_authority_block"])

    issues: list[str] = []

    if authority.get("verification_status") != "VERIFIED":
        issues.append("verification_status_not_verified")

    if trust_score < VERIFIED_AUTHORITY_MIN_SCORE:
        issues.append("score_below_verified_minimum")

    if source_label is not None and source_label != "verified_authority":
        issues.append("source_not_verified_authority_class")

    district_ok = True
    if not internal_resolution and user_district_normalized:
        ud = normalize_place_token(user_district_normalized)
        ad = normalize_place_token(authority.get("district") or "")
        if ud and ad and ud != ad:
            district_ok = False
            issues.append("district_mismatch_vs_user_input")

    approved = (
        authority.get("verification_status") == "VERIFIED"
        and trust_score >= VERIFIED_AUTHORITY_MIN_SCORE
        and (source_label is None or source_label == "verified_authority")
        and district_ok
    )

    if approved:
        issues = []

    return AuthorityGateResult(
        approved=approved,
        final_score=float(trust_score),
        issues=issues,
    )


def evaluate_authority_gate(
    *,
    trust_score: float,
    is_verified: bool,
    source_label: str | None,
) -> AuthorityGateResult:
    """Legacy shim — prefer evaluate_strict_authority_gate."""
    issues: list[str] = []
    if not is_verified:
        issues.append("trust_engine_not_verified")
    if trust_score < VERIFIED_AUTHORITY_MIN_SCORE:
        issues.append("score_below_verified_minimum")
    if source_label != "verified_authority":
        issues.append("source_not_verified_authority_class")
    approved = (
        is_verified
        and trust_score >= VERIFIED_AUTHORITY_MIN_SCORE
        and source_label == "verified_authority"
    )
    if approved:
        issues = []
    return AuthorityGateResult(approved=approved, final_score=float(trust_score), issues=issues)
