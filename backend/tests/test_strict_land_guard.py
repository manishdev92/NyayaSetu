"""Strict land hybrid guard and output validation."""

from __future__ import annotations

import pytest

from app.ai.llm_intent_engine import classify_intent_pipeline
from app.services.hybrid_case_routing import detect_land_context
from app.services.output_formatter import validate_output_bundle


def test_detect_land_context_kabza_hindi() -> None:
    assert detect_land_context("fight over land कब्ज़ा") is True


def test_detect_land_context_brutal_fight_only() -> None:
    assert detect_land_context("brutal fight between two people") is False


def test_brutal_fight_no_hybrid_leak() -> None:
    _interp, _tax, meta = classify_intent_pipeline(
        "brutal fight between two people in the market",
        city="Delhi",
    )
    assert meta.get("is_hybrid") is not True


def test_fight_land_kabza_hybrid_preserved() -> None:
    text = "fight over land कब्ज़ा between groups"
    assert detect_land_context(text) is True
    _interp, _tax, meta = classify_intent_pipeline(text, city="Lucknow")
    assert bool(meta.get("is_hybrid")) or bool(meta.get("hybrid_police_primary"))


def test_validate_non_hybrid_rejects_civil_court() -> None:
    ok, reason = validate_output_bundle(
        document="To the Station House Officer...",
        explanation="Go to police.",
        next_steps=["Call police"],
        meta={"is_emergency": True, "is_hybrid": False},
    )
    assert ok is True
    ok2, reason2 = validate_output_bundle(
        document="To the Station House Officer...",
        explanation="Also file in civil court tomorrow.",
        next_steps=["x"],
        meta={"is_emergency": True, "is_hybrid": False},
    )
    assert ok2 is False
    assert "civil" in reason2
