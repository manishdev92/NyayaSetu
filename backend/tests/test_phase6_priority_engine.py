"""Phase 6 priority_engine (law-and-order detection)."""

from __future__ import annotations

from app.services.priority_engine import detect_law_and_order_priority


def test_detect_fight_hindi_threat() -> None:
    out = detect_law_and_order_priority("मारपीट हो गई और धमकी मिल रही है")
    assert out["priority"] == "law_and_order"
    assert out["override"] is True
    assert out["primary_forum"] == "police"


def test_detect_normal_mutation() -> None:
    out = detect_law_and_order_priority("mutation pending for khasra 12")
    assert out["priority"] == "normal"
    assert out["override"] is False
