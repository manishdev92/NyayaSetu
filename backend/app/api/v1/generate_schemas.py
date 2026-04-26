"""Pydantic request/response models for `/generate` and `/generate-stream` (no route logic)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthorityInfo(BaseModel):
    """Unified authority / routing block (verified, suggested, or unknown)."""

    model_config = ConfigDict(extra="ignore")

    status: str  # verified | suggested | unknown
    primary: str = ""
    secondary: str = ""
    guidance: str = ""
    office_name: str | None = None
    name: str | None = None
    district: str | None = None
    state: str | None = None
    office_type: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    url: str | None = None
    trust_score: float | None = None
    verification_status: str | None = None
    verification_kind: str | None = None
    authority_tier: str | None = None
    fallback_authorities: list[str] | None = None
    suggestion_label: str | None = None
    issue_type: str | None = None
    severity: str | None = None
    jurisdiction_type: str | None = None
    reasoning: str | None = None
    jurisdiction_path: list[str] | None = None
    routing_context: str | None = None


class IssueProfileOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: str = ""
    severity: str = ""
    intent: str = ""
    keywords: list[str] = Field(default_factory=list)
    urgency: str = ""
    primary_category: str | None = None
    secondary_categories: list[str] = Field(default_factory=list)
    multi_intent_split: bool | None = None


class LegalClassificationOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    domain: str = ""
    sub_type: str = ""
    category: str = ""
    fine_intent: str = ""
    classifier_confidence: float = 0.0
    router_intent: str = ""
    entities: list[str] = Field(default_factory=list)
    intent_hint: str = ""
    context: str = ""
    issue_type: str = ""
    severity: str = ""
    jurisdiction_type: str = ""
    authority_primary: str = ""
    authority_secondary: str = ""
    issue_profile: IssueProfileOut | None = None
    secondary_domain: str | None = None
    is_hybrid: bool | None = None
    phase6_agents: dict[str, Any] | None = None
    intent_bucket: str = ""
    emergency_layer: dict[str, Any] | None = None


class EmergencyContactOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: str = ""
    label: str = ""
    numbers: list[str] = Field(default_factory=list)
    notes: str = ""
    provenance: str = ""
    source_url: str | None = None


class EmergencyReferenceLinkOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    url: str = ""
    source: str = ""


class JurisdictionOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    primary: str = ""
    secondary: str = ""
    path: list[str] = Field(default_factory=list)
    fallback_path: list[str] = Field(default_factory=list)
    jurisdiction_reason: str = ""
    is_hybrid: bool | None = None


class TrustSummaryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    authority_routing: str = ""
    law_knowledge: str = ""


class AuthorityCompactOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str = ""
    name: str = ""
    source: str = ""
    warning: str = ""


class TrustReportOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    score: float = 0.0
    reason: str = ""
    hallucination_risk: str | None = None
    fix_required: bool | None = None


class VerifierOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    accuracy_score: float = 0.0
    hallucination_risk: str = ""
    authority_validity: bool = False
    fix_required: bool = False


class GenerateRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="User's description of the legal issue")
    city: str | None = Field(default=None, description="City / district for authority lookup")
    full_name: str | None = Field(default=None, description="Complainant name for the letter")
    address: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    email: str | None = Field(default=None)
    skip_clarification: bool = Field(
        default=False,
        description="If true, skip all clarification gates (use after the user answered a prior clarification round).",
    )
    response_language: str | None = Field(
        default=None,
        description="Output language: 'en', 'hi' (Devanagari), or 'hi_latn' (Hindi in Roman/Latin script). Omit to infer from Accept-Language.",
    )
    client_mode: Literal["citizen", "lawyer"] | None = Field(
        default=None,
        description="Caller tier: citizen (default) or lawyer. Body wins over X-Client-Mode header; both omitted => citizen. Not authentication.",
    )
    task_type: Literal["draft_letter", "qa_only", "draft_with_qa", "consumer_complaint_filing"] = Field(
        default="draft_letter",
        description="draft_letter = full formal letter; qa_only = answer-first, short annex; draft_with_qa = short direct answer then full letter; consumer_complaint_filing = DCDRC-style filing template.",
    )

    @field_validator("response_language", mode="before")
    @classmethod
    def _normalize_response_language(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise TypeError("response_language must be a string or null")
        s = v.strip().lower().replace("-", "_")
        if s in ("hi", "hindi"):
            return "hi"
        if s in ("hi_latn", "hi_lat", "hindi_latn", "hindi_latin", "hinglish"):
            return "hi_latn"
        if s in ("en", "english"):
            return "en"
        raise ValueError("response_language must be 'en', 'hi', or 'hi_latn'")

    @field_validator("full_name", "address", "city", "phone", "email", mode="before")
    @classmethod
    def strip_optional(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v.strip() or None
        return v


class LegalReference(BaseModel):
    model_config = ConfigDict(extra="ignore")
    law: str = ""
    section: str = ""
    source_url: str = ""


class LegalOverviewOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: str | None = None
    grounding_label: str | None = None
    confidence_score: float | None = None
    references: list[LegalReference] = Field(default_factory=list)


class RetrievedLawItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    law: str = ""
    section: str = ""
    chunk: str = ""
    source_url: str = ""
    retrieval_score: float = 0.0
    verified: bool = False


class AuthoritySummaryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str = ""
    name: str = ""
    type: str = ""
    source_url: str = ""
    source: str = ""


class AuthorityHierarchyStepOut(BaseModel):
    """Static template + optional directory-backed office name (never LLM-generated)."""

    model_config = ConfigDict(extra="ignore")

    order: int = 0
    label: str = ""
    description: str = ""
    verified: bool = False
    office_name: str | None = None
    department_key: str | None = None
    source: str = "template"
    district_label: str | None = None


class RoutingSummaryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    issue_type: str = ""
    sub_type: str = ""
    domain: str = ""
    severity: str = ""
    authority_primary: str = ""
    authority_secondary: str = ""
    is_verified: bool = False
    urgency: str = ""
    router_intent: str = ""
    is_llm_fallback: bool = False
    llm_fallback_confidence: float | None = None
    is_hybrid: bool | None = None
    secondary_domain: str | None = None
    routing_primary_forum: str | None = None
    routing_secondary_forum: str | None = None


class ClarificationPointOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str = ""
    options: list[str] = Field(default_factory=list)


class ClarificationAgentQuestionOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = ""
    question: str = ""
    type: str = "single_choice"
    options: list[str] = Field(default_factory=list)
    required: bool = True


class UsageInfoOut(BaseModel):
    """Daily generation budget (UTC day; same counter as rate limit)."""

    model_config = ConfigDict(extra="ignore")
    used: int
    limit: int
    remaining: int
    reset_at_utc: str


class CaseLawReferenceOut(BaseModel):
    """Sprint 6: optional licensed case-law snippets (not statute RAG)."""

    model_config = ConfigDict(extra="ignore")
    title: str = ""
    citation: str = ""
    court: str = ""
    year: int | None = None
    source: str = ""
    url: str = ""
    snippet: str = ""


class GenerateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document: str
    draft: str = ""
    explanation: str
    next_steps: list[str]
    clarification_needed: bool = False
    clarification_question: str | None = None
    clarification_options: list[str] = Field(default_factory=list)
    clarification_points: list[ClarificationPointOut] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(
        default_factory=list,
        description="Conversational follow-up questions (2–4) before drafting; empty when using structured points only.",
    )
    clarification_agent_questions: list[ClarificationAgentQuestionOut] = Field(default_factory=list)
    clarification_optional: bool = False
    clarification_agent_reason: str = ""
    clarification_agent_confidence_hint: float | None = None
    urgency_banner: str | None = None
    urgency_level: str = "medium"
    issue_profile: IssueProfileOut | None = None
    official_links: list[str] = Field(default_factory=list)
    legal_overview: LegalOverviewOut | None = None
    multi_intent: dict[str, Any] | None = None
    generation_score: float | None = None
    routing_summary: RoutingSummaryOut | None = None
    is_verified: bool = False
    authority: AuthorityInfo | None = None
    authority_compact: AuthorityCompactOut | None = None
    authority_disclaimer: str
    authority_search_note: str | None = None
    legal_explanation: str | None = None
    procedure_steps: list[str] | None = None
    step_by_step_procedure: list[str] | None = None
    legal_references: list[LegalReference] | None = None
    retrieved_laws: list[RetrievedLawItem] | None = None
    confidence_score: float | None = None
    rag_grounding_label: str | None = None
    authority_summary: AuthoritySummaryOut | None = None
    legal_classification: LegalClassificationOut | None = None
    jurisdiction: JurisdictionOut | None = None
    trust_summary: TrustSummaryOut | None = None
    trust_report: TrustReportOut | None = None
    verifier: VerifierOut | None = None
    authority_hierarchy: list[AuthorityHierarchyStepOut] = Field(default_factory=list)
    alert: str | None = None
    note: str | None = None
    generation_mode: str = "NORMAL"
    skip_full_generation: bool = False
    safety_tip: str | None = None
    emergency_contacts: list[EmergencyContactOut] = Field(default_factory=list)
    emergency_reference_links: list[EmergencyReferenceLinkOut] = Field(default_factory=list)
    emergency_registry_disclaimer: str = ""
    crisis_triage_mode: bool = False
    usage: UsageInfoOut | None = None
    client_mode: Literal["citizen", "lawyer"] = Field(
        default="citizen",
        description="Effective tier applied for this response (echo of body/header resolution).",
    )
    task_type: Literal["draft_letter", "qa_only", "draft_with_qa", "consumer_complaint_filing"] = Field(
        default="draft_letter",
        description="Effective task type applied for this response (echo of request body).",
    )
    forum_caption: str | None = None
    prayer_items: list[str] = Field(default_factory=list)
    annexure_checklist: list[str] = Field(default_factory=list)
    case_law_references: list[CaseLawReferenceOut] = Field(
        default_factory=list,
        description="Sprint 6: optional case-law research rows (lawyer tier; empty when off or not configured).",
    )
    # Optional second pass: LLM evaluator + refiner (when `EVALUATOR_DUAL_DRAFT` is enabled on API).
    document_evaluator: dict[str, Any] | None = None
    document_revised: str = ""
