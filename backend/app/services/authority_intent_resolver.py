"""Map jurisdiction router_intent → authority JSON department keys + domain compatibility gates."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CRIMINAL_FORBIDDEN_OFFICE = re.compile(
    r"\b(labour|assistant\s+labour|municipal|district\s+consumer|consumer\s+commission|"
    r"banking\s+ombuds|tehsildar|sub[-\s]?divisional\s+magistrate|\bSDM\b|collector\s+office|"
    r"national\s+company\s+law\s+tribunal|\bNCLT\b)\b",
    re.I,
)

_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "authority_mismatch.json"

# JSON department keys used by authorities.json + search query builder (see search/queries.py)
_ROUTER_TO_DEPARTMENT: dict[str, str] = {
    "criminal_police": "police",
    "fraud_general": "police",
    "police_oversight": "police",
    "cyber_fraud": "cyber",
    "salary_issue": "labour",
    "consumer_issue": "other",
    "civil_dispute": "rental",
    "family_matters": "rental",
    "land_dispute": "land",
    "traffic_violation": "police",
    "rti_grievance": "other",
    "civic_local": "other",
    "banking_ombudsman": "other",
    "education_dispute": "other",
    "women_child_route": "police",
    "senior_maintenance": "rental",
    "share_dispute": "other",
    "general_issue": "",
}


def _log_mismatch(
    *,
    user_input: str,
    expected_domain: str,
    router_intent: str,
    returned_office_type: str | None,
    status: str,
) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "input": (user_input or "")[:2000],
            "expected_domain": expected_domain,
            "router_intent": router_intent,
            "returned_authority": returned_office_type,
            "status": status,
        }
        arr: list[Any] = []
        if _LOG_PATH.exists():
            try:
                arr = json.loads(_LOG_PATH.read_text(encoding="utf-8"))
                if not isinstance(arr, list):
                    arr = []
            except (json.JSONDecodeError, OSError):
                arr = []
        arr.append(row)
        _LOG_PATH.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("authority mismatch log failed: %s", e)


def log_authority_mismatch_event(
    *,
    user_input: str,
    expected_domain: str,
    returned_authority: str | None,
    router_intent: str | None,
    status: str = "mismatch",
) -> None:
    _log_mismatch(
        user_input=user_input,
        expected_domain=expected_domain,
        router_intent=str(router_intent or ""),
        returned_office_type=returned_authority,
        status=status,
    )


def department_for_router_intent(
    router_intent: str | None,
    domain: str | None,
    user_input: str,
) -> str:
    """
    Strict routing: department key follows classifier router_intent, not keyword guesswork.
    Falls back to infer_department only for general_issue / unknown router.
    """
    from app.services.authority_service import infer_department

    ri = (router_intent or "").strip().lower()
    if ri in _ROUTER_TO_DEPARTMENT:
        mapped = _ROUTER_TO_DEPARTMENT[ri]
        if mapped:
            return mapped
        return infer_department(user_input)
    return infer_department(user_input)


def strict_authority_passes_domain_gate(
    office_type: str | None,
    *,
    router_intent: str | None,
    domain: str | None,
    user_input: str = "",
) -> bool:
    """
    Hard reject cross-domain verified rows (e.g. criminal route must not surface Labour office).
    """
    ot = (office_type or "").strip().lower()
    ri = (router_intent or "").strip().lower()
    dom = (domain or "").strip().lower()

    if dom == "criminal":
        if ri == "cyber_fraud":
            if "police" in ot or "cyber" in ot:
                return True
            log_authority_mismatch_event(
                user_input=user_input,
                expected_domain=dom,
                returned_authority=office_type,
                router_intent=ri,
                status="criminal_cyber_reject_non_police_cyber",
            )
            return False
        if _CRIMINAL_FORBIDDEN_OFFICE.search(ot):
            log_authority_mismatch_event(
                user_input=user_input,
                expected_domain=dom,
                returned_authority=office_type,
                router_intent=ri,
                status="criminal_reject_forbidden_office_type",
            )
            return False
        if "police" not in ot and "cyber" not in ot:
            log_authority_mismatch_event(
                user_input=user_input,
                expected_domain=dom,
                returned_authority=office_type,
                router_intent=ri,
                status="criminal_requires_police_office_type",
            )
            return False
        return True

    if ri == "salary_issue" and dom == "labour":
        if "labour" not in ot:
            log_authority_mismatch_event(
                user_input=user_input,
                expected_domain=dom,
                returned_authority=office_type,
                router_intent=ri,
                status="labour_route_non_labour_office",
            )
            return False
        return True

    return True
