from __future__ import annotations

import re
from typing import Literal, TypedDict

VerificationStatus = Literal["VERIFIED", "UNVERIFIED", "REJECTED"]


class StrictAuthority(TypedDict, total=False):
    """Fixed authority payload — never LLM-invented."""

    state: str
    district: str
    office_type: str
    office_name: str
    address: str | None
    phone: str | None
    email: str | None
    source: str
    verification_status: VerificationStatus
    # Optional metadata for API / auditing (not user-guessable facts)
    trust_score: float
    url: str | None


OFFICE_TYPES = (
    "Labour",
    "Police",
    "Cyber Crime",
    "SDM",
    "Collector",
    "Court",
    "Land",
    "Rental",
    "General",
)


def department_key_to_office_type(department: str) -> str:
    """Map internal JSON department key to display office_type."""
    d = (department or "").lower().strip()
    mapping = {
        "labour": "Labour",
        "police": "Police",
        "land": "Collector",
        "rental": "Court",
        "cyber": "Cyber Crime",
        "other": "General",
    }
    return mapping.get(d, "General" if not d else d.title())


# Known city keys → state (deterministic; extend as JSON grows)
STATE_BY_CITY_KEY: dict[str, str] = {
    "varanasi": "Uttar Pradesh",
    "delhi": "Delhi",
}


def state_for_city_key(city_key: str | None) -> str:
    if not city_key:
        return ""
    return STATE_BY_CITY_KEY.get(city_key.strip().lower(), "")


def district_label_from_city_key(city_key: str | None) -> str:
    if not city_key:
        return ""
    return city_key.strip().replace("_", " ").title()


_STATE_HINT = re.compile(
    r"\b(Uttar Pradesh|Delhi|Maharashtra|Karnataka|Bihar|West Bengal|Telangana|Tamil Nadu)\b",
    re.IGNORECASE,
)


def infer_state_hint(text: str | None) -> str:
    """Best-effort state from page text — never guessed beyond pattern match."""
    if not text:
        return ""
    m = _STATE_HINT.search(text)
    return m.group(1).strip() if m else ""
