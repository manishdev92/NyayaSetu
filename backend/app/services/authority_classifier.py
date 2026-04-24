from __future__ import annotations

import re
from enum import Enum
from urllib.parse import urlparse


class SourceClassification(str, Enum):
    """High-level URL/source bucket for authority handling."""

    VERIFIED = "VERIFIED"  # Official Indian government hostname — eligible for gov validation path
    UNVERIFIED = "UNVERIFIED"  # Not an official gov host (search, maps, blogs, etc.)
    REJECTED = "REJECTED"  # Blocklisted or unusable for authority display


class AuthorityPageIntent(str, Enum):
    """
    Whether a government URL represents an actionable office/contact path
    vs informational / directory content (must not be treated as verified authority office).
    """

    ACTIONABLE = "actionable"
    INFORMATIONAL = "informational"
    REJECTED = "rejected"


# Hosts that must never be treated as government authority sources
_REJECT_NETLOC_PATTERNS = re.compile(
    r"(justdial|sulekha|indiamart|tradeindia|yellowpages|asklaila|\.blog\.|blogspot|wordpress\.com|"
    r"medium\.com|quora\.com|reddit\.|facebook\.|instagram\.|twitter\.|x\.com|"
    r"timesofindia|indiatoday|ndtv|hindustantimes|news18|thehindu|scroll\.in)",
    re.IGNORECASE,
)

# URL path patterns typical of "who's who", directories, pure info — not an office desk
_INFO_PATH_PATTERNS = re.compile(
    r"(/whos-?who|/whoswho|telephone[-_]?directory|officer[-_]?directory|/ias[-_]?officers|"
    r"/directory/|/phonebook|/contact-list|/static/|/history|/about[-_]?us|/rti-act-text|"
    r"/gazette-notification|/notification-archive)",
    re.IGNORECASE,
)


def _netloc(url: str) -> str:
    try:
        return urlparse(url.strip()).netloc.lower()
    except Exception:
        return ""


def classify_source(source_url: str) -> SourceClassification:
    """
    Classify a URL for authority handling. Does not fetch pages.
    Internal directory rows use source_url "" — caller treats those separately.
    """
    if not (source_url or "").strip():
        return SourceClassification.UNVERIFIED

    nl = _netloc(source_url)
    if not nl:
        return SourceClassification.UNVERIFIED

    if _REJECT_NETLOC_PATTERNS.search(nl):
        return SourceClassification.REJECTED

    if nl.endswith(".nic.in") or nl.endswith(".gov.in"):
        return SourceClassification.VERIFIED

    return SourceClassification.UNVERIFIED


def classify_authority_page_intent(source_url: str, text_sample: str) -> AuthorityPageIntent:
    """
    Distinguish actionable office/counter pages from informational / directory / gazette-only pages.
    Uses URL path + short title/snippet heuristics only (no HTML scraping).
    """
    url = (source_url or "").strip()
    if not url:
        return AuthorityPageIntent.REJECTED

    ul = url.lower()
    if _INFO_PATH_PATTERNS.search(ul):
        return AuthorityPageIntent.INFORMATIONAL

    ts = (text_sample or "").lower()
    if re.search(
        r"\b(who'?s who|whos who|list of ias|list of officers|telephone directory|"
        r"officers of the district|organizational chart only)\b",
        ts,
    ):
        return AuthorityPageIntent.INFORMATIONAL

    return AuthorityPageIntent.ACTIONABLE
