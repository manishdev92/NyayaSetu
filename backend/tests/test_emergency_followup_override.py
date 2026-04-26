from __future__ import annotations

from app.services.ai_service import _has_hard_emergency_signal


def test_hard_emergency_signal_true_for_ongoing_injury() -> None:
    assert _has_hard_emergency_signal("fight happening now, person is injured and bleeding") is True


def test_hard_emergency_signal_false_for_peaceful_land_dispute() -> None:
    assert _has_hard_emergency_signal("property mutation dispute, no force or violence involved") is False
