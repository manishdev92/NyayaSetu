"""Phase 6 safety hints (violence / emergency). Classifier remains source of truth for routing."""

from __future__ import annotations

import re
from typing import Any


_VIOLENCE = re.compile(
    r"\b(kill|killed|murder|stab|stabbed|shoot|shot|weapon|knife|gun|"
    r"beaten|beating|assault|attack|blood|bleeding|injured|injury|hurt badly|"
    r"rape|molest|kidnap|threat to kill|life danger|dying)\b",
    re.I,
)


def assess_violence_guardrails(user_input: str) -> dict[str, Any]:
    """
    Lightweight text signals for UX copy — does not override `classifier_meta.is_emergency`.
    """
    raw = (user_input or "").strip()
    if not raw:
        return {"violence_signal": False, "suggested_alert": None}
    hit = bool(_VIOLENCE.search(raw))
    alert = None
    if hit:
        alert = "If you are in immediate danger, call 112 (or 100) now and move to a safe place."
    return {"violence_signal": hit, "suggested_alert": alert}
