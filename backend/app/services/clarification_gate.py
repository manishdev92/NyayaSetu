"""Re-exports clarification_engine (legacy module name)."""

from __future__ import annotations

from app.services.clarification_engine import (
    CLARIFICATION_CONFIDENCE_THRESHOLD,
    needs_clarification,
    should_skip_clarification_for_urgency,
)

__all__ = [
    "CLARIFICATION_CONFIDENCE_THRESHOLD",
    "needs_clarification",
    "should_skip_clarification_for_urgency",
]
