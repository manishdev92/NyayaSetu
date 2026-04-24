from __future__ import annotations

from app.services.authority_provider import AuthorityRecord
from app.authority import get_default_authority_provider
from app.services.json_authority_provider import JsonFileAuthorityProvider


def resolve_city_key(city: str | None) -> str | None:
    return JsonFileAuthorityProvider().resolve_city_key(city)


def infer_department(user_input: str) -> str:
    """
    Map free-text issue to a department key present under each city in authorities.json.
    Defaults to "other" when cues are ambiguous (routing should use router_intent from the classifier).
    """
    t = user_input.lower()
    if any(
        w in t
        for w in (
            "nclt",
            "company law tribunal",
            "shareholder",
            "share dispute",
            "mca ",
            "ministry of corporate",
            "roc ",
            "registrar of companies",
            "oppression",
            "minority shareholder",
            "winding up",
            "insolvency",
        )
    ):
        return "corporate"
    if any(
        w in t
        for w in (
            "salary",
            "wage",
            "wages",
            "payment due",
            "not received salary",
            "unpaid",
            "pf ",
            "provident",
            "gratuity",
            "labour",
            "labor",
            "factory",
            "industrial",
            "employer",
            "termination",
            "wrongful",
            "layoff",
            "bonus",
            "overtime",
        )
    ):
        return "labour"
    if any(w in t for w in ("land", "boundary", "survey", "title deed", "property dispute")):
        return "land"
    if any(w in t for w in ("rent", "tenant", "landlord", "lease", "eviction")):
        return "rental"
    if any(
        w in t
        for w in (
            "fir",
            "police",
            "theft",
            "assault",
            "beating",
            "attack",
            "violence",
            "threat",
            "robbery",
            "cheating",
            "ipc",
        )
    ):
        return "police"
    return "other"


def get_local_authority(city: str, issue_type: str) -> AuthorityRecord | None:
    """Public entry used by tools and deterministic fallback; backed by the configured provider."""
    return get_default_authority_provider().get_local_authority(city, issue_type)
