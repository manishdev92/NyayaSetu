from __future__ import annotations

from typing import Any, TypedDict

from app.ai.rag_pipeline import RagPipelineOut
from app.i18n_response_strings import normalize_response_lang
from app.legal_ui_copy import (
    issue_type_display,
    jurisdiction_display,
    law_line_prefixes,
    legal_education_disclaimer,
    no_rag_match_message,
    procedure_steps_localized,
    rag_header_sub,
    severity_display,
)
from app.services.legal_taxonomy import LegalClassification

LEGAL_EDUCATION_DISCLAIMER = (
    "This summary is educational. Confirm statute text on India Code or official portals. "
    "This is not legal advice — consult a qualified advocate for your situation."
)

NO_RAG_MATCH_MESSAGE = (
    "No strong legal match was found in the curated legal database for this query and issue type. "
    "Use general government procedure guidance only, and verify any statute on "
    "https://www.indiacode.nic.in or your state portal. Do not treat uncited detail as authoritative."
)

CRISIS_MODE_LEGAL_MESSAGE = (
    "**Crisis / safety triage mode:** Long-form legal research, statute lists, and generic "
    "procedure checklists are hidden so the response stays short during an urgent situation. "
    "Use the helplines, alert, and immediate steps below. When it is safe, consult official "
    "portals or a qualified advocate for detailed legal options."
)


class AuthoritySummary(TypedDict, total=False):
    status: str
    name: str
    type: str
    source_url: str
    source: str


class LegalCompanionPayload(TypedDict, total=False):
    legal_explanation: str
    procedure_steps: list[str]
    step_by_step_procedure: list[str]
    legal_references: list[dict[str, str]]
    retrieved_laws: list[dict[str, Any]]
    confidence_score: float
    rag_grounding_label: str
    authority_summary: AuthoritySummary


_PROCEDURE_BY_ISSUE: dict[str, list[str]] = {
    "corporate": [
        "Collect company documents, shareholding pattern, and board/AGM records available to you.",
        "Identify whether relief lies before NCLT (e.g. oppression, winding-up) or civil court as per legal advice.",
        "File only through prescribed formats on official portals; appeals follow NCLAT/High Court routes as per law.",
    ],
    "salary": [
        "Collect employment records, pay slips, and any written communication about dues.",
        "Approach the labour inspectorate / assistant labour commissioner for your district (or the route your state prescribes).",
        "If conciliation does not resolve the matter, follow tribunal/court jurisdiction as advised for your category of workman/employee.",
    ],
    "traffic": [
        "Preserve the challan notice, vehicle documents, and any photographs or receipts.",
        "Use the official state transport / e-challan portal where applicable to verify and contest.",
        "For licence/RTO issues, follow the RTO process; for penalties, use appellate channels described on the official notice.",
    ],
    "cyber": [
        "Preserve bank/UPI logs, SMS, screenshots, and transaction IDs.",
        "File a complaint with the jurisdictional cyber cell / police station and use the national cybercrime reporting route as applicable.",
        "Follow up in writing and keep copies of all acknowledgements.",
    ],
    "land": [
        "Collect title documents, survey maps, and revenue extracts available to you.",
        "Approach the tehsil/revenue office for mutation and record corrections through prescribed forms.",
        "For encroachment or title disputes, seek guidance on civil remedies from official sources or qualified counsel.",
    ],
    "police": [
        "Write a clear factual complaint with date, place, and witnesses if any.",
        "Approach the police station with territorial jurisdiction; request a copy of the FIR when registered.",
        "Use hierarchical representations only as permitted by law and keep copies.",
    ],
    "family": [
        "Collect marriage documents, financial records, and communications relevant to the dispute.",
        "Identify the correct family court / forum jurisdiction with the help of official court websites or legal aid.",
        "Follow mediation requirements where mandatory before contested hearings.",
    ],
    "consumer": [
        "Preserve invoices, warranty cards, and written complaints to the seller/service provider.",
        "File before the correct consumer commission based on pecuniary limits using the prescribed format.",
        "Keep proof of filing and attend hearings as directed.",
    ],
    "fraud": [
        "Document timelines, bank records, and identities communicated to you.",
        "Lodge FIR / complaint with jurisdictional police and cooperate with investigation.",
        "Avoid transferring more funds; follow only official communication channels.",
    ],
    "general": [
        "Write down a clear timeline and collect any documents you already have.",
        "Identify whether the issue is civil, criminal, revenue, or regulatory using official state portals.",
        "Seek guidance from district administration or legal services authority for the correct department.",
    ],
}


def _slim_references(rag: RagPipelineOut) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in rag["retrieved_laws"]:
        out.append(
            {
                "law": str(r.get("law") or ""),
                "section": str(r.get("section") or ""),
                "source_url": str(r.get("source_url") or "").strip(),
            }
        )
    return out


def build_authority_summary(authority_block: dict[str, Any]) -> AuthoritySummary:
    st = authority_block.get("status") or "unknown"
    if st == "verified":
        return AuthoritySummary(
            status="verified",
            name=str(authority_block.get("office_name") or authority_block.get("primary") or ""),
            type=str(authority_block.get("office_type") or "office"),
            source_url=str(authority_block.get("url") or "").strip(),
            source=str(authority_block.get("source") or "").strip(),
        )
    if st == "suggested":
        return AuthoritySummary(
            status="suggested",
            name=str(authority_block.get("primary") or ""),
            type="routing_suggestion",
            source_url="",
            source="deterministic_routing",
        )
    return AuthoritySummary(status="unknown", name="", type="", source_url="", source="")


def build_legal_companion_payload(
    *,
    user_input: str,
    city: str | None,
    taxonomy: LegalClassification,
    authority_block: dict[str, Any],
    rag_result: RagPipelineOut,
    response_language: str = "en",
) -> LegalCompanionPayload:
    """Deterministic companion layer — law text must come only from strict RAG output."""
    _ = user_input
    it = taxonomy["issue_type"]
    rl = normalize_response_lang(response_language)
    use_hi = rl in ("hi", "hi_latn")
    loc_steps = procedure_steps_localized(str(it), response_language)
    steps = list(loc_steps) if loc_steps else list(_PROCEDURE_BY_ISSUE.get(it, _PROCEDURE_BY_ISSUE["general"]))
    label = rag_result["grounding_label"]
    laws = rag_result["retrieved_laws"]
    conf = float(rag_result["confidence_score"])
    loc_raw = (city or "").strip()
    it_show = issue_type_display(str(it), response_language)
    sev_show = severity_display(str(taxonomy["severity"]), response_language)
    jur_show = jurisdiction_display(str(taxonomy["jurisdiction_type"]), response_language)

    if use_hi:
        loc_bold = loc_raw or ("आपका ज़िला" if rl == "hi" else "aapka zila")
        if rl == "hi":
            cls_line = f"मुद्दा वर्गीकरण: **{it_show}** (गंभीरता: {sev_show}, क्षेत्राधिकार केंद्र: {jur_show})।"
            loc_line = f"फ़ॉर्म से स्थान: **{loc_bold}** (आधिकारिक पोर्टलों पर क्षेत्राधिकार पुष्टि करें)।"
        else:
            cls_line = f"Mudda vargikaran: **{it_show}** (gambhirata: {sev_show}, kshetradhikar kendr: {jur_show})."
            loc_line = f"Form se sthan: **{loc_bold}** (adhikarik portalon par kshetradhikar pushti karein)."
    else:
        loc_en = loc_raw or "your district"
        cls_line = (
            f"Issue classification: **{it}** (severity: {taxonomy['severity']}, "
            f"jurisdiction focus: {taxonomy['jurisdiction_type']})."
        )
        loc_line = f"Location context from your form: **{loc_en}** (confirm jurisdiction on official portals)."

    expl_parts = [cls_line, loc_line]

    if label == "no_match" or not laws:
        expl_parts.append(no_rag_match_message(response_language) if use_hi else NO_RAG_MATCH_MESSAGE)
    else:
        header, sub = rag_header_sub(response_language, str(label))
        expl_parts.append(f"**{header}**\n{sub}")
        rs_key, ver_key = law_line_prefixes(response_language)
        chunk_lbl = "अंश" if rl == "hi" else "Ansh" if rl == "hi_latn" else "Chunk"
        url_lbl = "URL" if use_hi else "URL"
        for r in laws[:8]:
            chunk = str(r.get("chunk") or "").strip()
            excerpt = chunk if len(chunk) <= 400 else chunk[:397] + "…"
            expl_parts.append(
                f"• **{r.get('law', '')}** — {r.get('section', '')} — {rs_key}={r.get('retrieval_score')} — {ver_key}={r.get('verified')}\n"
                f"  _{chunk_lbl}:_ {excerpt}\n"
                f"  _{url_lbl}:_ {r.get('source_url', '')}"
            )

    expl_parts.append(legal_education_disclaimer(response_language) if use_hi else LEGAL_EDUCATION_DISCLAIMER)
    legal_explanation = "\n\n".join(expl_parts)

    rl_serial = [dict(x) for x in laws]

    return LegalCompanionPayload(
        legal_explanation=legal_explanation,
        procedure_steps=steps,
        step_by_step_procedure=steps,
        legal_references=_slim_references(rag_result) if laws else [],
        retrieved_laws=rl_serial,
        confidence_score=conf,
        rag_grounding_label=label,
        authority_summary=build_authority_summary(authority_block),
    )


def build_crisis_triage_companion_payload(*, authority_block: dict[str, Any]) -> LegalCompanionPayload:
    """
    No RAG chunks / no generic procedure list — used when violence, emergency, or high-priority
    women/safety routing requires a short, action-first response.
    """
    return LegalCompanionPayload(
        legal_explanation=CRISIS_MODE_LEGAL_MESSAGE,
        procedure_steps=[],
        step_by_step_procedure=[],
        legal_references=[],
        retrieved_laws=[],
        confidence_score=0.0,
        rag_grounding_label="no_match",
        authority_summary=build_authority_summary(authority_block),
    )
