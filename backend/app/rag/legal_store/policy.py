"""
Curated legal store — allowed source patterns only (India official law).
RAG chunks must satisfy these for highest trust tier.
"""

from __future__ import annotations

ALLOWED_LEGAL_HOST_SUFFIXES: tuple[str, ...] = (
    "indiacode.nic.in",
    "gov.in",
    "nic.in",
    "sci.gov.in",
    "ecourts.gov.in",
    "india.gov.in",
    "districts.ecourts.gov.in",
)

FORBIDDEN_HOST_HINTS: tuple[str, ...] = (
    "wikipedia.org",
    "medium.com",
    "blogspot.",
    "wordpress.com",
)


def is_allowed_legal_source_url(url: str) -> bool:
    u = (url or "").lower()
    if not u.startswith("http"):
        return False
    if any(bad in u for bad in FORBIDDEN_HOST_HINTS):
        return False
    return any(s in u for s in ALLOWED_LEGAL_HOST_SUFFIXES)
