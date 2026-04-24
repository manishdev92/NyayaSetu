from __future__ import annotations

import re
from typing import Any, TypedDict
from urllib.parse import urlparse

from app.services.authority_classifier import (
    AuthorityPageIntent,
    SourceClassification,
    classify_authority_page_intent,
    classify_source,
)
from app.services.district_entity import (
    district_entity_check,
    looks_like_scraped_html_table,
    normalize_place_token,
)


class AuthorityValidationResult(TypedDict, total=False):
    is_verified: bool
    trust_score: float
    reason: str
    cleaned_data: dict[str, Any]


_DEPT_OR_OFFICE = re.compile(
    r"\b(department|dept|commissioner|collector|ministry|government|govt|secretariat|"
    r"directorate|office|authority|tribunal|court|police|municipal|panchayat|"
    r"भारत|सचिवालय|विभाग|कार्यालय)\b",
    re.IGNORECASE,
)

PHONE_IN = re.compile(r"(?:\+91|0)?[\s\-]?[6-9]\d{9}\b")
_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PIN = re.compile(r"\b\d{3}\s?\d{3}\b")


def _netloc(url: str) -> str:
    try:
        return urlparse(url.strip()).netloc.lower()
    except Exception:
        return ""


def _is_gov_host(url: str) -> bool:
    nl = _netloc(url)
    return nl.endswith(".gov.in") or nl.endswith(".nic.in")


def has_complete_contact_bundle(content: str, office_name: str) -> bool:
    """Office/role signal + phone or email or PIN — required for external gov 'validated' tier."""
    blob = f"{office_name}\n{content}".strip()
    if len(blob) < 30:
        return False
    has_office = bool(
        re.search(
            r"\b(office|department|commissioner|collector|directorate|authority|officer|deputy)\b",
            blob,
            re.IGNORECASE,
        )
    )
    has_contact = bool(PHONE_IN.search(blob) or _EMAIL.search(blob) or _PIN.search(blob))
    return has_office and has_contact


def _content_has_authority_signals(content: str, office_name: str) -> bool:
    text = f"{office_name}\n{content}".strip()
    if len(text) < 24:
        return False

    has_dept = bool(_DEPT_OR_OFFICE.search(text))
    has_contact = bool(PHONE_IN.search(text) or _EMAIL.search(text) or _PIN.search(text))
    has_address_hint = bool(
        re.search(
            r"\b(road|street|lane|nagar|district|state|pin|near|opp|building|floor|block)\b",
            text,
            re.IGNORECASE,
        )
    )

    if has_dept:
        return has_contact or has_address_hint or len(office_name.strip()) >= 8
    return has_contact and len(office_name.strip()) >= 6


def validate_authority(
    source_url: str,
    content: str,
    *,
    office_name: str = "",
    source_channel: str | None = None,
    user_district_normalized: str | None = None,
    address: str | None = None,
) -> AuthorityValidationResult:
    """
    Fixed scoring (Phase 3 truth engine):
    - Internal DB match: 10
    - Verified govt structured API: 9 (reserved channel)
    - Validated .gov.in / .nic.in page (entity + contact): 8
    - Unvalidated gov page: 5
    - Search / third-party: 0–4
    - Scraped HTML tables: rejected (score ~0)
    """
    name = (office_name or "").strip()
    combined = f"{name}\n{content}".strip()
    ch = (source_channel or "").lower()

    cleaned: dict[str, Any] = {
        "name": name or None,
        "address": None,
        "phone": None,
        "email": None,
        "url": (source_url or "").strip() or None,
    }

    if looks_like_scraped_html_table(combined):
        return AuthorityValidationResult(
            is_verified=False,
            trust_score=0.0,
            reason="rejected:scraped_html_or_tabular_layout",
            cleaned_data={},
        )

    # --- Internal NyayaSetu directory ---
    if ch == "local_json":
        if len(name) < 4:
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=2.0,
                reason="internal_db:weak_identity",
                cleaned_data={},
            )
        has_contact_lines = bool(PHONE_IN.search(combined) or _EMAIL.search(combined))
        has_addr = bool(
            re.search(
                r"\b(road|street|lane|nagar|district|state|pin|building)\b",
                combined,
                re.IGNORECASE,
            )
        )
        if _content_has_authority_signals(content, name) or (
            len(name) >= 6 and (has_contact_lines or has_addr)
        ):
            return AuthorityValidationResult(
                is_verified=True,
                trust_score=10.0,
                reason="internal_db:verified",
                cleaned_data=cleaned,
            )
        return AuthorityValidationResult(
            is_verified=False,
            trust_score=5.0,
            reason="internal_db:incomplete_record",
            cleaned_data={},
        )

    clf = classify_source(source_url)
    if clf == SourceClassification.REJECTED:
        return AuthorityValidationResult(
            is_verified=False,
            trust_score=1.0,
            reason="blacklisted_or_untrusted_domain",
            cleaned_data={},
        )

    url = (source_url or "").strip()
    if not url:
        return AuthorityValidationResult(
            is_verified=False,
            trust_score=1.5,
            reason="missing_url_for_web_source",
            cleaned_data={},
        )

    ul = url.lower()
    if "google.com/maps" in ul or "maps.app.goo.gl" in ul or "/maps/" in ul:
        return AuthorityValidationResult(
            is_verified=False,
            trust_score=5.0,
            reason="google_maps:unverified_channel",
            cleaned_data={},
        )

    # Reserved: deterministic government API feed (not search snippets)
    if ch in ("gov_structured_api", "government_api"):
        if _is_gov_host(url) and has_complete_contact_bundle(content, name):
            return AuthorityValidationResult(
                is_verified=True,
                trust_score=9.0,
                reason="gov_structured_api:verified",
                cleaned_data=cleaned,
            )

    if _is_gov_host(url) and clf == SourceClassification.VERIFIED:
        if len(name) < 4:
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=4.0,
                reason="gov_domain:weak_title",
                cleaned_data={},
            )
        page_intent = classify_authority_page_intent(url, combined)
        if page_intent == AuthorityPageIntent.INFORMATIONAL:
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=3.5,
                reason="gov_domain:informational_page_not_action_office",
                cleaned_data={},
            )
        if page_intent == AuthorityPageIntent.REJECTED:
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=2.0,
                reason="gov_domain:page_intent_rejected",
                cleaned_data={},
            )
        ud = normalize_place_token(user_district_normalized or "")
        if not ud:
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=5.0,
                reason="gov_domain:missing_user_district_for_entity_check",
                cleaned_data={},
            )

        ok_ent, ent_why = district_entity_check(
            user_district_normalized=ud,
            combined_text=content,
            office_name=name,
            address=address or "",
        )
        if not ok_ent:
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=4.0,
                reason=f"gov_domain:entity_check_failed:{ent_why}",
                cleaned_data={},
            )

        if has_complete_contact_bundle(content, name):
            return AuthorityValidationResult(
                is_verified=True,
                trust_score=8.0,
                reason="gov_domain:validated_page_score_8",
                cleaned_data=cleaned,
            )
        if _content_has_authority_signals(content, name):
            return AuthorityValidationResult(
                is_verified=False,
                trust_score=5.0,
                reason="gov_domain:unvalidated_partial_contact",
                cleaned_data={},
            )
        return AuthorityValidationResult(
            is_verified=False,
            trust_score=5.0,
            reason="gov_domain:unvalidated_weak_content",
            cleaned_data={},
        )

    return AuthorityValidationResult(
        is_verified=False,
        trust_score=3.0,
        reason="unverified_search_or_third_party",
        cleaned_data={},
    )
