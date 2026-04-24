from __future__ import annotations

from typing import Any

_DEFAULT_NEXT_STEPS: list[str] = [
    "Confirm facts and dates in writing.",
    "Use only official government websites (.gov.in / .nic.in) or India Code for legal text.",
    "If you need representation, contact a qualified advocate or district legal services authority.",
]


def ensure_non_empty_next_steps(next_steps: list[str] | None) -> list[str]:
    if next_steps and len([s for s in next_steps if str(s).strip()]) > 0:
        return [str(s).strip() for s in next_steps if str(s).strip()]
    return list(_DEFAULT_NEXT_STEPS)


def finalize_legal_response(result: dict[str, Any]) -> dict[str, Any]:
    """Contract: never return empty next_steps."""
    ns = ensure_non_empty_next_steps(result.get("next_steps") if isinstance(result.get("next_steps"), list) else None)
    out = dict(result)
    out["next_steps"] = ns
    return out
