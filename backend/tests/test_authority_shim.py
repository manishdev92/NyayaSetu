"""RISK-01: `app.authority` re-exports match canonical `authority_schema` (no duplicate types)."""

from app import authority
from app.services import authority_intent_resolver, authority_schema, json_authority_provider


def test_authority_shim_same_objects() -> None:
    assert authority.StrictAuthority is authority_schema.StrictAuthority
    assert authority.state_for_city_key is authority_schema.state_for_city_key
    assert authority.department_key_to_office_type is authority_schema.department_key_to_office_type
    assert authority.department_for_router_intent is authority_intent_resolver.department_for_router_intent
    assert (
        authority.strict_authority_passes_domain_gate
        is authority_intent_resolver.strict_authority_passes_domain_gate
    )
    assert (
        authority.get_default_authority_provider
        is json_authority_provider.get_default_authority_provider
    )
