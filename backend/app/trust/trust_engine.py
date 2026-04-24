from __future__ import annotations

import re
from typing import Any, Literal, TypedDict
from urllib.parse import urlparse

from app.services.authority_validation import is_internal_directory_authority
from app.services.authority_validator import validate_authority
from app.services.search.models import AuthorityCandidate

VERIFIED_AUTHORITY_MIN_SCORE = 8.0

TrustTier = Literal["VERIFIED", "SUGGESTED", "BLOCKED"]


class TrustEvaluation(TypedDict, total=False):
    is_verified: bool
    score: float
    reason: str
    safe_data: dict[str, Any]
    source_label: str


_AMBIGUOUS = re.compile(
    r"\bnearby\b|\bclose to\b|\bone of the offices\b|\bvisit any\b",
    re.IGNORECASE,
)


def _netloc(url: str) -> str:
    try:
        return urlparse(url.strip()).netloc.lower()
    except Exception:
        return ""


def _build_validation_content(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ("snippet", "address", "phone", "email"):
        v = result.get(k)
        if v:
            parts.append(str(v).strip())
    return "\n".join(parts)


def _normalize_source_channel(src: str) -> str | None:
    if not src:
        return None
    if src == "local_json":
        return "local_json"
    return src


def _is_search_api_source(src: str) -> bool:
    s = (src or "").lower()
    return any(
        s.startswith(p) or f"_{p}" in s
        for p in ("tavily", "serpapi", "bing")
    )


def _hard_reject(result: dict[str, Any]) -> tuple[bool, str]:
    name = (result.get("name") or "").strip()
    snippet = result.get("snippet") or ""
    url = (result.get("url") or "").strip()
    src = result.get("source") or ""

    if len(name) < 4:
        return True, "no_clear_authority_identity"

    if _AMBIGUOUS.search(snippet) or _AMBIGUOUS.search(name):
        return True, "ambiguous_nearby_style_text"

    if src != "local_json" and not url:
        return True, "no_official_domain_or_url"

    return False, ""


def evaluate_authority_trust(result: dict[str, Any]) -> TrustEvaluation:
    """
    External candidates — BLOCK scraped / low-signal listings unless .gov.in/.nic.in passes gates.
    Never mix VERIFIED with unverified search blobs in downstream UI.
    """
    reject, why = _hard_reject(result)
    if reject:
        return TrustEvaluation(
            is_verified=False,
            score=0.0,
            reason=f"rejected:{why}",
            safe_data={},
            source_label="unverified_search_result",
        )

    src = result.get("source") or ""
    name = (result.get("name") or "").strip()
    content = _build_validation_content(result)
    url = (result.get("url") or "").strip()
    ud = (result.get("user_district_normalized") or "").strip()
    addr = (result.get("address") or "").strip() or None

    val = validate_authority(
        url,
        content,
        office_name=name,
        source_channel=_normalize_source_channel(src),
        user_district_normalized=ud if ud else None,
        address=addr,
    )

    score = float(val.get("trust_score") or 0.0)
    reason = str(val.get("reason") or "")
    v_ok = bool(val.get("is_verified"))

    if _is_search_api_source(src) and not (
        _netloc(url).endswith(".gov.in") or _netloc(url).endswith(".nic.in")
    ):
        score = min(score, 3.0)
        v_ok = False
        reason += "; search_api_non_gov_capped"

    ul = url.lower()
    if "google.com/maps" in ul or "maps.app.goo.gl" in ul or "/maps/place" in ul:
        score = min(score, 5.0)
        v_ok = False
        reason += "; maps_not_verified_authority"

    is_verified = v_ok and score >= VERIFIED_AUTHORITY_MIN_SCORE
    label = "verified_authority" if is_verified else "unverified_search_result"

    safe: dict[str, Any] = {}
    if is_verified:
        safe = {
            "name": name,
            "address": addr,
            "phone": (result.get("phone") or "").strip() or None,
            "email": (result.get("email") or "").strip() or None,
            "source": src,
            "url": url or None,
        }

    reason_clean = "; ".join(s.strip() for s in reason.split(";") if s.strip())

    return TrustEvaluation(
        is_verified=is_verified,
        score=round(min(10.0, max(0.0, score)), 2),
        reason=reason_clean,
        safe_data=safe,
        source_label=label,
    )


def candidate_to_normalized(c: AuthorityCandidate) -> dict[str, Any]:
    return {
        "name": c.get("name") or "",
        "address": c.get("address") or "",
        "phone": c.get("phone") or "",
        "email": c.get("email") or "",
        "source": c.get("source") or "",
        "url": c.get("url") or "",
        "snippet": c.get("snippet") or "",
    }


def trust_sort_key(c: AuthorityCandidate, te: TrustEvaluation) -> tuple[int, int, float]:
    internal = 0 if is_internal_directory_authority(c) else 1
    gov = 0 if _netloc(c.get("url") or "").endswith((".gov.in", ".nic.in")) else 1
    return (internal, gov, -float(te.get("score") or 0.0))


def authority_tier_from_block(authority_api: dict[str, Any] | None) -> TrustTier:
    if not authority_api:
        return "BLOCKED"
    st = authority_api.get("status")
    if st == "verified":
        return "VERIFIED"
    if st == "suggested":
        return "SUGGESTED"
    return "BLOCKED"


def build_trust_report(
    *,
    authority_block: dict[str, Any],
    verifier: dict[str, Any],
    law_refs_verified_only: bool,
) -> dict[str, Any]:
    """Explainable score 0–10 + reason — LLM does not set this."""
    tier = authority_tier_from_block(authority_block)
    base = float(verifier.get("accuracy_score") or 0.0)
    score = max(0.0, min(10.0, base))
    parts = [f"authority_tier={tier}", f"verifier_accuracy={verifier.get('accuracy_score')}"]
    if tier == "VERIFIED":
        parts.append("internal_or_gov_domain_validated")
    elif tier == "SUGGESTED":
        parts.append("graph_routing_only_no_contacts")
    else:
        parts.append("no_verified_office_match")
    if law_refs_verified_only:
        parts.append("legal_refs_filtered_verified_chunks_only")
    else:
        parts.append("legal_refs_empty_or_unverified_omitted")
    return {
        "score": round(score, 1),
        "reason": "; ".join(parts),
        "hallucination_risk": verifier.get("hallucination_risk"),
        "fix_required": verifier.get("fix_required"),
    }
