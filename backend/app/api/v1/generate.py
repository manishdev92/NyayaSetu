import asyncio
import json
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.i18n_response_strings import (
    authority_disclaimer,
    stream_phase_analyzing,
    stream_phase_clarification_banner,
    stream_phase_domain_check,
    stream_phase_preparing_for_task,
    stream_phase_urgent_violence,
)
from app.api.v1.generate_mappers import (
    to_api_authority,
    to_authority_compact,
    to_authority_hierarchy,
    to_authority_summary,
    to_case_law_references,
    to_clarification_agent_questions,
    to_clarification_points,
    to_emergency_contacts,
    to_emergency_reference_links,
    to_issue_profile,
    to_jurisdiction,
    to_legal_classification,
    to_legal_overview,
    to_legal_references,
    to_retrieved_laws,
    to_routing_summary,
    to_trust_report,
    to_trust_summary,
    to_verifier,
)
from app.api.v1.generate_schemas import GenerateRequest, GenerateResponse, UsageInfoOut
from app.config import settings
from app.services.ai_service import (
    generate_legal_response,
    maybe_clarification_only_response,
    prefetch_intent,
)
from app.services.pro_entitlements_store import clerk_has_pro_entitlement
from app.services.usage_limit import UsageSnapshot, consume_request, http_rate_limit_headers

router = APIRouter()


def _error_code_for_value_error(msg: str) -> str:
    if "OPENAI_API_KEY is not configured" in msg:
        return "generate_openai_unconfigured"
    if "OpenAI rejected your API key" in msg:
        return "generate_openai_auth_failed"
    return "generate_service_unavailable"


def _coalesce_response_language(
    from_body: str | None,
    accept_language: str | None,
) -> str:
    if from_body in ("en", "hi", "hi_latn"):
        return from_body
    if accept_language and str(accept_language).strip():
        part = str(accept_language).split(",")[0].strip().split(";")[0].strip().lower()
        if part.startswith("hi"):
            return "hi"
    return "en"


def _resolve_client_mode(
    body_mode: Literal["citizen", "lawyer"] | None,
    header_value: str | None,
) -> Literal["citizen", "lawyer"]:
    """Body wins; then X-Client-Mode; default citizen. See docs/CLIENT_MODE_DESIGN.md."""
    if body_mode in ("citizen", "lawyer"):
        return body_mode
    if isinstance(header_value, str) and header_value.strip():
        h = header_value.strip().lower()
        if h in ("lawyer", "legal_professional", "pro"):
            return "lawyer"
        if h in ("citizen", "public", "general"):
            return "citizen"
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid X-Client-Mode; use citizen, lawyer, or omit.",
                "error_code": "invalid_client_mode",
            },
        )
    return "citizen"


def _ensure_lawyer_mode_allowed(client_mode: str, uid: str | None) -> None:
    """P1-1: optional gate — lawyer tier requires signed-in user id when configured."""
    if client_mode != "lawyer":
        return
    if not settings.lawyer_client_mode_requires_user_id:
        return
    if uid and str(uid).strip():
        return
    raise HTTPException(
        status_code=403,
        detail={
            "message": "Lawyer mode requires a signed-in user. Sign in and retry, or use general user mode.",
            "error_code": "lawyer_mode_requires_sign_in",
        },
    )


def _ensure_lawyer_pro_if_required(client_mode: str, uid: str | None) -> None:
    """P1-1: optional gate — Pro subscription (Stripe entitlements) for lawyer mode."""
    if client_mode != "lawyer" or not settings.lawyer_pro_gate_active():
        return
    if not uid or not str(uid).strip():
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Lawyer mode in this deployment requires a signed-in account and NyayaSetu Pro.",
                "error_code": "lawyer_mode_requires_sign_in",
            },
        )
    if not clerk_has_pro_entitlement(str(uid).strip()):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Lawyer mode requires an active NyayaSetu Pro subscription. Use general user mode, or upgrade in billing.",
                "error_code": "lawyer_mode_requires_pro",
            },
        )


def _usage_model(snap: UsageSnapshot) -> UsageInfoOut:
    return UsageInfoOut(
        used=snap.used,
        limit=snap.limit,
        remaining=snap.remaining,
        reset_at_utc=snap.reset_at_utc,
    )


def _usage_payload(snap: UsageSnapshot) -> dict[str, Any]:
    return {
        "used": snap.used,
        "limit": snap.limit,
        "remaining": snap.remaining,
        "reset_at_utc": snap.reset_at_utc,
    }


@router.post("/generate", response_model=GenerateResponse)
def generate(
    request: Request,
    response: Response,
    payload: GenerateRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    x_client_mode: str | None = Header(default=None, alias="X-Client-Mode"),
) -> GenerateResponse:
    client_ip = request.client.host if request.client else None
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    ok, usage_snap = consume_request(user_id=uid, client_ip=client_ip)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily request limit reached. Sign in for a higher limit, or try again tomorrow.",
                "error_code": "generate_rate_limited",
            },
            headers=http_rate_limit_headers(usage_snap),
        )
    for hk, hv in http_rate_limit_headers(usage_snap).items():
        response.headers[hk] = hv

    client_mode = _resolve_client_mode(payload.client_mode, x_client_mode)
    _ensure_lawyer_mode_allowed(client_mode, uid)
    _ensure_lawyer_pro_if_required(client_mode, uid)

    try:
        details = {
            "full_name": payload.full_name,
            "address": payload.address,
            "city": payload.city,
            "phone": payload.phone,
            "email": payload.email,
        }
        rl = _coalesce_response_language(payload.response_language, accept_language)
        result = generate_legal_response(
            payload.user_input,
            user_details=details,
            skip_clarification=payload.skip_clarification,
            response_language=rl,
            client_mode=client_mode,
            task_type=payload.task_type,
        )
        disclaimer = str(result.get("authority_disclaimer") or "").strip()
        if not disclaimer:
            disclaimer = authority_disclaimer(rl)
        proc = result.get("procedure_steps")
        if not isinstance(proc, list):
            proc = result.get("step_by_step_procedure")
        draft = result.get("draft")
        if not isinstance(draft, str) or not draft.strip():
            draft = str(result.get("document") or "")
        _tt = result.get("task_type", payload.task_type)
        task_type_out = (
            _tt
            if _tt in ("draft_letter", "qa_only", "draft_with_qa", "consumer_complaint_filing")
            else payload.task_type
        )
        return GenerateResponse(
            client_mode=client_mode,
            task_type=task_type_out,
            document=result["document"],
            draft=draft,
            explanation=result["explanation"],
            next_steps=result["next_steps"],
            clarification_needed=bool(result.get("clarification_needed")),
            clarification_question=result.get("clarification_question")
            if isinstance(result.get("clarification_question"), str)
            else None,
            clarification_options=list(co)
            if isinstance((co := result.get("clarification_options")), list)
            else [],
            clarification_points=to_clarification_points(result.get("clarification_points")),
            clarifying_questions=list(cq)
            if isinstance((cq := result.get("clarifying_questions")), list)
            else [],
            clarification_agent_questions=to_clarification_agent_questions(
                result.get("clarification_agent_questions")
            ),
            clarification_optional=bool(result.get("clarification_optional")),
            clarification_agent_reason=str(result.get("clarification_agent_reason") or ""),
            clarification_agent_confidence_hint=float(cah)
            if isinstance((cah := result.get("clarification_agent_confidence_hint")), (int, float))
            else None,
            urgency_banner=result.get("urgency_banner") if isinstance(result.get("urgency_banner"), str) else None,
            urgency_level=str(result.get("urgency_level") or "medium"),
            issue_profile=to_issue_profile(ip) if isinstance((ip := result.get("issue_profile")), dict) else None,
            official_links=list(ol) if isinstance((ol := result.get("official_links")), list) else [],
            legal_overview=to_legal_overview(result.get("legal_overview")),
            multi_intent=result.get("multi_intent") if isinstance(result.get("multi_intent"), dict) else None,
            generation_score=float(gs)
            if isinstance((gs := result.get("generation_score")), (int, float))
            else None,
            routing_summary=to_routing_summary(result.get("routing_summary")),
            is_verified=bool(result.get("is_verified")),
            authority=to_api_authority(result.get("authority")),
            authority_compact=to_authority_compact(result.get("authority_compact")),
            authority_disclaimer=disclaimer,
            authority_search_note=result.get("authority_search_note"),
            legal_explanation=result.get("legal_explanation") if isinstance(result.get("legal_explanation"), str) else None,
            procedure_steps=proc if isinstance(proc, list) else None,
            step_by_step_procedure=result.get("step_by_step_procedure")
            if isinstance(result.get("step_by_step_procedure"), list)
            else None,
            legal_references=to_legal_references(result.get("legal_references")),
            retrieved_laws=to_retrieved_laws(result.get("retrieved_laws")),
            confidence_score=float(cs)
            if isinstance((cs := result.get("confidence_score")), (int, float))
            else None,
            rag_grounding_label=result.get("rag_grounding_label")
            if isinstance(result.get("rag_grounding_label"), str)
            else None,
            authority_summary=to_authority_summary(result.get("authority_summary")),
            legal_classification=to_legal_classification(result.get("legal_classification")),
            jurisdiction=to_jurisdiction(result.get("jurisdiction")),
            trust_summary=to_trust_summary(result.get("trust_summary")),
            trust_report=to_trust_report(result.get("trust_report")),
            verifier=to_verifier(result.get("verifier")),
            authority_hierarchy=to_authority_hierarchy(result.get("authority_hierarchy")),
            alert=result.get("alert") if isinstance(result.get("alert"), str) else None,
            note=result.get("note") if isinstance(result.get("note"), str) else None,
            generation_mode=str(result.get("generation_mode") or "NORMAL"),
            skip_full_generation=bool(result.get("skip_full_generation")),
            safety_tip=result.get("safety_tip") if isinstance(result.get("safety_tip"), str) else None,
            emergency_contacts=to_emergency_contacts(result.get("emergency_contacts")),
            emergency_reference_links=to_emergency_reference_links(result.get("emergency_reference_links")),
            emergency_registry_disclaimer=str(result.get("emergency_registry_disclaimer") or ""),
            crisis_triage_mode=bool(result.get("crisis_triage_mode")),
            usage=_usage_model(usage_snap),
            case_law_references=to_case_law_references(result.get("case_law_references")),
            forum_caption=result.get("forum_caption")
            if isinstance(result.get("forum_caption"), str)
            else None,
            prayer_items=list(pi) if isinstance((pi := result.get("prayer_items")), list) else [],
            annexure_checklist=list(ac) if isinstance((ac := result.get("annexure_checklist")), list) else [],
            document_evaluator=result.get("document_evaluator")
            if isinstance(result.get("document_evaluator"), dict)
            else None,
            document_revised=str(result.get("document_revised") or ""),
        )
    except ValueError as e:
        msg = str(e)
        code = _error_code_for_value_error(msg)
        raise HTTPException(status_code=503, detail={"message": msg, "error_code": code}) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"message": f"AI generation failed: {e!s}", "error_code": "generate_upstream_error"},
        ) from e


def _sse_line(obj: dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/generate-stream")
async def generate_stream(
    request: Request,
    payload: GenerateRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    x_client_mode: str | None = Header(default=None, alias="X-Client-Mode"),
) -> StreamingResponse:
    """SSE stream: phase updates, optional clarification, then full JSON result (or clarification-only payload)."""
    client_ip = request.client.host if request.client else None
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    stream_ok, usage_snap = consume_request(user_id=uid, client_ip=client_ip)
    if not stream_ok:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily request limit reached. Sign in for a higher limit, or try again tomorrow.",
                "error_code": "generate_rate_limited",
            },
            headers=http_rate_limit_headers(usage_snap),
        )
    udict = _usage_payload(usage_snap)

    client_mode = _resolve_client_mode(payload.client_mode, x_client_mode)
    _ensure_lawyer_mode_allowed(client_mode, uid)
    _ensure_lawyer_pro_if_required(client_mode, uid)

    user_trim = payload.user_input.strip()
    stream_rl = _coalesce_response_language(payload.response_language, accept_language)
    details = {
        "full_name": payload.full_name,
        "address": payload.address,
        "city": payload.city,
        "phone": payload.phone,
        "email": payload.email,
    }

    async def event_gen():
        try:
            yield _sse_line({"type": "phase", "message": stream_phase_analyzing(stream_rl)})
            if not settings.openai_api_key:
                yield _sse_line(
                    {
                        "type": "error",
                        "message": "OPENAI_API_KEY is not configured",
                        "error_code": "generate_openai_unconfigured",
                    }
                )
                yield _sse_line({"type": "done"})
                return

            prefetch = await asyncio.to_thread(
                prefetch_intent,
                user_trim,
                payload.city,
                str(getattr(payload, "task_type", None) or "draft_letter"),
            )
            if str(prefetch.classifier_meta.get("priority_level") or "").strip().upper() == "P0":
                yield _sse_line(
                    {
                        "type": "phase",
                        "message": stream_phase_urgent_violence(stream_rl),
                    }
                )
            domain = str(prefetch.classifier_meta.get("domain") or "general")
            yield _sse_line(
                {
                    "type": "phase",
                    "message": stream_phase_domain_check(stream_rl, domain.replace("_", " ")),
                }
            )

            if not payload.skip_clarification:
                early = await asyncio.to_thread(
                    maybe_clarification_only_response,
                    user_trim,
                    prefetch,
                    city=payload.city,
                    response_language=stream_rl,
                )
                if early and early.get("clarification_needed"):
                    cqq_raw = early.get("clarifying_questions")
                    cqq = [str(x).strip() for x in cqq_raw if str(x).strip()] if isinstance(cqq_raw, list) else []
                    opt_flag = bool(early.get("clarification_optional"))
                    agent_q_raw = early.get("clarification_agent_questions")
                    agent_q = agent_q_raw if isinstance(agent_q_raw, list) else []
                    phase_msg = stream_phase_clarification_banner(
                        stream_rl,
                        optional=opt_flag,
                        has_agent_q=bool(agent_q),
                        multi_q=len(cqq) >= 2,
                    )
                    yield _sse_line(
                        {"type": "phase", "phase": "clarification_questions", "message": phase_msg}
                    )
                    q = early.get("clarification_question") if isinstance(early.get("clarification_question"), str) else ""
                    opts = early.get("clarification_options") if isinstance(early.get("clarification_options"), list) else []
                    pts = early.get("clarification_points") if isinstance(early.get("clarification_points"), list) else []
                    yield _sse_line(
                        {
                            "type": "clarification",
                            "question": q,
                            "options": opts,
                            "points": pts,
                            "clarifying_questions": cqq,
                            "clarification_agent_questions": agent_q,
                            "clarification_optional": opt_flag,
                            "clarification_agent_reason": early.get("clarification_agent_reason")
                            if isinstance(early.get("clarification_agent_reason"), str)
                            else "",
                            "clarification_agent_confidence_hint": early.get("clarification_agent_confidence_hint"),
                            "clarification_needed": True,
                        }
                    )
                    early_out = dict(early) if isinstance(early, dict) else {}
                    early_out["usage"] = udict
                    early_out["client_mode"] = client_mode
                    yield _sse_line({"type": "result", "payload": early_out})
                    yield _sse_line({"type": "done"})
                    return

            yield _sse_line(
                {
                    "type": "phase",
                    "message": stream_phase_preparing_for_task(stream_rl, str(payload.task_type or "draft_letter")),
                }
            )
            result = await asyncio.to_thread(
                generate_legal_response,
                user_trim,
                details,
                _intent_prefetch=prefetch,
                skip_clarification=True,
                response_language=stream_rl,
                client_mode=client_mode,
                task_type=payload.task_type,
            )
            assert isinstance(result, dict)
            result = {**result, "usage": udict, "client_mode": client_mode}
            yield _sse_line({"type": "result", "payload": result})
            yield _sse_line({"type": "done"})
        except ValueError as e:
            msg = str(e)
            code = _error_code_for_value_error(msg)
            yield _sse_line({"type": "error", "message": msg, "error_code": code})
            yield _sse_line({"type": "done"})
        except Exception as e:
            yield _sse_line(
                {
                    "type": "error",
                    "message": str(e),
                    "error_code": "generate_upstream_error",
                }
            )
            yield _sse_line({"type": "done"})

    stream_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    stream_headers.update(http_rate_limit_headers(usage_snap))
    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers=stream_headers,
    )
