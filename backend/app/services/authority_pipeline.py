from __future__ import annotations

from typing import Any

from app.ai.authority_evaluator import evaluate_strict_authority_gate
from app.ai.evaluator import RESPONSE_DISCLAIMER
from app.authority import (
    StrictAuthority,
    department_for_router_intent,
    department_key_to_office_type,
    district_label_from_city_key,
    get_default_authority_provider,
    infer_state_hint,
    state_for_city_key,
    strict_authority_passes_domain_gate,
)
from app.services.district_entity import normalize_place_token
from app.services.search.models import AuthorityCandidate
from app.services.search.parallel_search import gather_remote_candidates
from app.services.trust_engine import (
    VERIFIED_AUTHORITY_MIN_SCORE,
    candidate_to_normalized,
    evaluate_authority_trust,
    trust_sort_key,
)

AUTHORITY_DISCLAIMER = RESPONSE_DISCLAIMER

FALLBACK_MESSAGE = (
    "⚠️ No verified authority found for your location. Please check official government website."
)


def _strict_from_internal(
    *,
    rec: dict[str, Any],
    city_key: str,
    department: str,
) -> StrictAuthority:
    st = state_for_city_key(city_key)
    dist = district_label_from_city_key(city_key)
    return {
        "state": st,
        "district": dist,
        "office_type": department_key_to_office_type(department),
        "office_name": str(rec.get("name") or ""),
        "address": rec.get("address"),
        "phone": rec.get("phone"),
        "email": rec.get("email"),
        "source": "NyayaSetu internal verified directory",
        "verification_status": "VERIFIED",
        "trust_score": 10.0,
        "url": None,
    }


def _strict_from_external(
    *,
    chosen: AuthorityCandidate,
    te: dict[str, Any],
    safe: dict[str, Any],
    city_display: str,
    department: str,
) -> StrictAuthority:
    snippet = chosen.get("snippet") or ""
    addr = safe.get("address") or chosen.get("address")
    phone = safe.get("phone") or chosen.get("phone")
    email = safe.get("email") or chosen.get("email")
    url = (safe.get("url") or chosen.get("url") or "").strip()
    blob = f"{snippet}\n{safe.get('name') or chosen.get('name')}\n{addr or ''}"
    st = infer_state_hint(blob) or ""
    return {
        "state": st,
        "district": city_display.strip(),
        "office_type": department_key_to_office_type(department),
        "office_name": str(safe.get("name") or chosen.get("name") or ""),
        "address": addr if isinstance(addr, str) else None,
        "phone": phone if isinstance(phone, str) else None,
        "email": email if isinstance(email, str) else None,
        "source": "Validated official government page (.gov.in / .nic.in)",
        "verification_status": "VERIFIED",
        "trust_score": float(te.get("score") or 0.0),
        "url": url if url else None,
    }


def resolve_verified_authority(
    user_input: str,
    city: str | None,
    *,
    router_intent: str | None = None,
    domain: str | None = None,
) -> tuple[StrictAuthority | None, dict[str, Any]]:
    """
    STRICT ORDER:
    1) Internal NyayaSetu DB (keyed by resolved district) — if match, return VERIFIED and STOP.
    2) Else if city missing — cannot align external rows to a district; return no authority.
    3) Else remote search — validate each candidate; never show without score ≥ 8 and gate approval.
    """
    department = department_for_router_intent(router_intent, domain, user_input)
    provider = get_default_authority_provider()
    meta: dict[str, Any] = {
        "disclaimer": AUTHORITY_DISCLAIMER,
        "fallback_message": None,
        "authority_gate": None,
        "resolution_path": None,
        "authority_department": department,
        "authority_router_intent": router_intent,
        "authority_domain": domain,
    }

    city_stripped = (city or "").strip()
    ck = provider.resolve_city_key(city_stripped) if city_stripped else None

    # --- STEP 1: internal directory only (no mixing with web results) ---
    if ck and city_stripped:
        rec = provider.get_local_authority(city_stripped, department)
        if rec and rec.get("found"):
            strict = _strict_from_internal(rec=rec, city_key=ck, department=department)
            gate = evaluate_strict_authority_gate(
                authority=strict,
                trust_score=float(strict.get("trust_score") or 0.0),
                source_label="verified_authority",
                internal_resolution=True,
                user_district_normalized=None,
            )
            meta["authority_gate"] = gate
            meta["resolution_path"] = "internal_db"
            if gate.get("approved"):
                if not strict_authority_passes_domain_gate(
                    strict.get("office_type"),
                    router_intent=router_intent,
                    domain=domain,
                    user_input=user_input,
                ):
                    meta["fallback_message"] = FALLBACK_MESSAGE
                    meta["resolution_path"] = "internal_rejected_domain_gate"
                    return None, meta
                meta["trust_snapshot"] = {
                    "is_verified": True,
                    "score": strict["trust_score"],
                    "reason": "internal_db:verified",
                    "tier": "verified_authority",
                }
                return strict, meta
            meta["fallback_message"] = FALLBACK_MESSAGE
            return None, meta

    # --- External path requires an explicit user district/city for entity alignment ---
    if not city_stripped:
        meta["fallback_message"] = FALLBACK_MESSAGE
        meta["resolution_path"] = "no_city_for_external_alignment"
        return None, meta

    ud_token = normalize_place_token(city_stripped)

    try:
        remote = gather_remote_candidates(user_input, city_stripped, department)
    except Exception:
        remote = []

    if not remote:
        meta["fallback_message"] = FALLBACK_MESSAGE
        meta["resolution_path"] = "no_remote_candidates"
        return None, meta

    ranked: list[tuple[AuthorityCandidate, dict[str, Any], dict[str, Any], StrictAuthority]] = []
    for c in remote:
        norm = candidate_to_normalized(c)
        norm["user_district_normalized"] = ud_token
        te = evaluate_authority_trust(norm)
        if not te.get("is_verified"):
            continue
        if float(te.get("score") or 0) < VERIFIED_AUTHORITY_MIN_SCORE:
            continue
        safe = te.get("safe_data") or {}
        strict = _strict_from_external(
            chosen=c,
            te=te,
            safe=safe,
            city_display=city_stripped,
            department=department,
        )
        gate = evaluate_strict_authority_gate(
            authority=strict,
            trust_score=float(te.get("score") or 0.0),
            source_label=te.get("source_label"),
            internal_resolution=False,
            user_district_normalized=ud_token,
        )
        if not gate.get("approved"):
            continue
        if not strict_authority_passes_domain_gate(
            strict.get("office_type"),
            router_intent=router_intent,
            domain=domain,
            user_input=user_input,
        ):
            continue
        ranked.append((c, te, gate, strict))

    if not ranked:
        meta["fallback_message"] = FALLBACK_MESSAGE
        meta["resolution_path"] = "no_candidate_passed_validation"
        return None, meta

    ranked.sort(key=lambda it: trust_sort_key(it[0], it[1]))
    _chosen, te, gate, out = ranked[0]
    meta["authority_gate"] = gate
    meta["resolution_path"] = "external_gov_validated"
    meta["trust_snapshot"] = {
        "is_verified": True,
        "score": out["trust_score"],
        "reason": str(te.get("reason") or ""),
        "tier": "verified_authority",
    }
    return out, meta


def _verification_kind_for_api(v: StrictAuthority) -> str | None:
    src = (v.get("source") or "").lower()
    if "internal" in src:
        return "internal_directory"
    if (v.get("url") or "").strip():
        return "government_domain"
    return None


def verified_to_api_dict(v: StrictAuthority | None) -> dict[str, str | float | None] | None:
    if not v:
        return None
    u = (v.get("url") or "").strip()
    office = v.get("office_name") or ""
    return {
        "state": v.get("state") or "",
        "district": v.get("district") or "",
        "office_type": v.get("office_type") or "",
        "office_name": office,
        "name": office,
        "address": v.get("address"),
        "phone": v.get("phone"),
        "email": v.get("email"),
        "source": v.get("source") or "",
        "verification_status": v.get("verification_status"),
        "verification_kind": _verification_kind_for_api(v),
        "url": u if u else None,
        "trust_score": v.get("trust_score"),
        "status": "verified",
        "authority_tier": "verified_authority",
    }
