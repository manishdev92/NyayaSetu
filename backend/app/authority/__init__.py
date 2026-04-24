"""
Public authority types and helpers (RISK-01, staged).

Re-exports the canonical implementation in `app.services.authority_schema` so
callers can use `app.authority` as a stable import root. Do not duplicate logic here.
"""

from app.services.authority_intent_resolver import (
    department_for_router_intent,
    strict_authority_passes_domain_gate,
)
from app.services.authority_schema import (
    OFFICE_TYPES,
    StrictAuthority,
    VerificationStatus,
    department_key_to_office_type,
    district_label_from_city_key,
    infer_state_hint,
    state_for_city_key,
)
from app.services.json_authority_provider import get_default_authority_provider

__all__ = [
    "OFFICE_TYPES",
    "StrictAuthority",
    "VerificationStatus",
    "department_for_router_intent",
    "department_key_to_office_type",
    "district_label_from_city_key",
    "get_default_authority_provider",
    "infer_state_hint",
    "state_for_city_key",
    "strict_authority_passes_domain_gate",
]
