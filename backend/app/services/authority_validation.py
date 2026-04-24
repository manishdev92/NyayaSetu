from __future__ import annotations

from urllib.parse import urlparse

from app.services.search.models import AuthorityCandidate


def _netloc(url: str) -> str:
    try:
        return urlparse(url.strip()).netloc.lower()
    except Exception:
        return ""


def is_trusted_government_domain(url: str) -> bool:
    """
    True only for hostnames under official Indian government patterns.
    Generic web search results on other domains are never treated as verified authority.
    """
    if not url or not str(url).strip():
        return False
    nl = _netloc(url)
    if not nl:
        return False
    return nl.endswith(".gov.in") or nl.endswith(".nic.in")


def is_internal_directory_authority(c: AuthorityCandidate) -> bool:
    """NyayaSetu curated JSON directory — explicitly trusted."""
    return (c.get("source") or "") == "local_json"


def validate_authority_for_display(c: AuthorityCandidate) -> bool:
    """
    Explicit gate used before any contact details or "official" labelling:
    - Internal verified directory entry, OR
    - URL on .gov.in / .nic.in
    """
    if is_internal_directory_authority(c):
        return True
    return is_trusted_government_domain(c.get("url") or "")


def verification_kind(c: AuthorityCandidate) -> str | None:
    if not validate_authority_for_display(c):
        return None
    if is_internal_directory_authority(c):
        return "internal_directory"
    if is_trusted_government_domain(c.get("url") or ""):
        return "government_domain"
    return None


def pick_best_verified_candidate(
    eligible: list[AuthorityCandidate],
    scores: dict[int, float],
    *,
    min_score_government: float = 8.0,
) -> AuthorityCandidate | None:
    """
    Prefer internal directory rows; among government URLs only, require evaluator score threshold.
    """
    if not eligible:
        return None

    internal_idxs = [i for i, c in enumerate(eligible) if is_internal_directory_authority(c)]
    if internal_idxs:
        best_i = max(internal_idxs, key=lambda i: scores.get(i, 0.0))
        return eligible[best_i]

    passing = [
        i
        for i, c in enumerate(eligible)
        if scores.get(i, 0.0) >= min_score_government and is_trusted_government_domain(c.get("url") or "")
    ]
    if not passing:
        return None
    best_i = max(passing, key=lambda i: scores.get(i, 0.0))
    return eligible[best_i]
