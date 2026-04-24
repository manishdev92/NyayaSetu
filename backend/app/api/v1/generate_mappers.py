"""Map raw `ai_service` dicts into API Pydantic models for `/generate`."""

from __future__ import annotations

from app.api.v1.generate_schemas import (
    AuthorityCompactOut,
    AuthorityHierarchyStepOut,
    AuthorityInfo,
    AuthoritySummaryOut,
    ClarificationAgentQuestionOut,
    ClarificationPointOut,
    EmergencyContactOut,
    EmergencyReferenceLinkOut,
    IssueProfileOut,
    JurisdictionOut,
    LegalClassificationOut,
    LegalOverviewOut,
    LegalReference,
    RetrievedLawItem,
    RoutingSummaryOut,
    TrustReportOut,
    TrustSummaryOut,
    VerifierOut,
)


def to_emergency_contacts(raw: object) -> list[EmergencyContactOut]:
    if not isinstance(raw, list):
        return []
    out: list[EmergencyContactOut] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(EmergencyContactOut.model_validate(item))
            except Exception:
                continue
    return out


def to_emergency_reference_links(raw: object) -> list[EmergencyReferenceLinkOut]:
    if not isinstance(raw, list):
        return []
    out: list[EmergencyReferenceLinkOut] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(EmergencyReferenceLinkOut.model_validate(item))
            except Exception:
                continue
    return out


def to_clarification_agent_questions(raw: object) -> list[ClarificationAgentQuestionOut]:
    if not isinstance(raw, list):
        return []
    out: list[ClarificationAgentQuestionOut] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(ClarificationAgentQuestionOut.model_validate(item))
            except Exception:
                continue
    return out


def to_clarification_points(raw: object) -> list[ClarificationPointOut]:
    if not isinstance(raw, list):
        return []
    out: list[ClarificationPointOut] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(ClarificationPointOut.model_validate(item))
            except Exception:
                continue
    return out


def to_authority_hierarchy(raw: object) -> list[AuthorityHierarchyStepOut]:
    if not isinstance(raw, list):
        return []
    out: list[AuthorityHierarchyStepOut] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                out.append(AuthorityHierarchyStepOut.model_validate(item))
            except Exception:
                continue
    return out


def to_api_authority(raw: dict[str, object] | None) -> AuthorityInfo | None:
    if not raw:
        return None
    if not isinstance(raw.get("status"), str):
        return None
    return AuthorityInfo.model_validate(raw)


def to_legal_references(raw: object) -> list[LegalReference] | None:
    if not isinstance(raw, list):
        return None
    out: list[LegalReference] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(LegalReference.model_validate(item))
    return out or None


def to_authority_summary(raw: object) -> AuthoritySummaryOut | None:
    if not isinstance(raw, dict):
        return None
    return AuthoritySummaryOut.model_validate(raw)


def to_retrieved_laws(raw: object) -> list[RetrievedLawItem] | None:
    if not isinstance(raw, list):
        return None
    out: list[RetrievedLawItem] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(RetrievedLawItem.model_validate(item))
    return out or None


def to_issue_profile(raw: object) -> IssueProfileOut | None:
    if not isinstance(raw, dict):
        return None
    return IssueProfileOut.model_validate(raw)


def to_legal_overview(raw: object) -> LegalOverviewOut | None:
    if not isinstance(raw, dict):
        return None
    return LegalOverviewOut.model_validate(raw)


def to_routing_summary(raw: object) -> RoutingSummaryOut | None:
    if not isinstance(raw, dict):
        return None
    return RoutingSummaryOut.model_validate(raw)


def to_legal_classification(raw: object) -> LegalClassificationOut | None:
    if not isinstance(raw, dict):
        return None
    return LegalClassificationOut.model_validate(raw)


def to_jurisdiction(raw: object) -> JurisdictionOut | None:
    if not isinstance(raw, dict):
        return None
    return JurisdictionOut.model_validate(raw)


def to_trust_summary(raw: object) -> TrustSummaryOut | None:
    if not isinstance(raw, dict):
        return None
    return TrustSummaryOut.model_validate(raw)


def to_authority_compact(raw: object) -> AuthorityCompactOut | None:
    if not isinstance(raw, dict):
        return None
    return AuthorityCompactOut.model_validate(raw)


def to_trust_report(raw: object) -> TrustReportOut | None:
    if not isinstance(raw, dict):
        return None
    return TrustReportOut.model_validate(raw)


def to_verifier(raw: object) -> VerifierOut | None:
    if not isinstance(raw, dict):
        return None
    return VerifierOut.model_validate(raw)
