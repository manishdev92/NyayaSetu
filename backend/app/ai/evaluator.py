from __future__ import annotations

from typing import Any

from app.services.trust_engine import VERIFIED_AUTHORITY_MIN_SCORE

RESPONSE_DISCLAIMER = (
    "Please verify all details on official government websites before visiting or taking action. "
    "NyayaSetu does not guarantee external data accuracy."
)


def approve_final_response(
    *,
    authority_api: dict[str, Any] | None,
    trust_is_verified: bool,
    trust_score: float,
) -> tuple[bool, str]:
    """
    Consistency check for unified authority block (verified | suggested | unknown).
    """
    if authority_api is None:
        return True, "ok"

    mode = authority_api.get("status")
    if mode == "verified":
        if not trust_is_verified:
            return False, "inconsistent: verified mode without trust pipeline match"
        ts = authority_api.get("trust_score")
        if ts is not None and float(ts) < VERIFIED_AUTHORITY_MIN_SCORE:
            return False, "trust_score below threshold in payload"
        if authority_api.get("verification_status") not in (None, "VERIFIED"):
            return False, "verification_status must be VERIFIED in verified mode"
        return True, "ok"

    if mode in ("suggested", "unknown"):
        if trust_is_verified:
            return False, "inconsistent: non-verified mode with trust flag"
        return True, "ok"

    return False, "invalid authority status"
