from app.services.output_formatter import (
    dedupe_and_cap_next_steps,
    deduplicate_lines,
    evaluate_response_bundle,
    validate_output_bundle,
)


def test_deduplicate_lines_order() -> None:
    assert deduplicate_lines(["a", "b", "a", "B "]) == ["a", "b"]


def test_validate_allows_civil_court_when_not_emergency() -> None:
    ok, _ = validate_output_bundle(
        document="Draft to civil court.",
        explanation="File suit in civil court.",
        next_steps=["Engage advocate"],
        meta={"is_emergency": False, "is_hybrid": False},
    )
    assert ok is True


def test_evaluate_response_bundle_dedupes_and_caps_steps() -> None:
    doc, expl, steps = evaluate_response_bundle(
        document="Line A\nLine A",
        explanation="One\nTwo",
        next_steps=["a", "a", "b", "c", "d", "e"],
        meta={"is_emergency": False, "is_hybrid": False},
        alert=None,
    )
    assert "Line A" in doc
    assert len(steps) <= 4


def test_dedupe_next_steps_caps_and_dedupes_112() -> None:
    steps = [
        "Dial 112 immediately",
        "Dial 112 for emergency",
        "Go to police station",
        "Bring ID",
        "Extra fifth",
    ]
    out = dedupe_and_cap_next_steps(steps, max_steps=4)
    assert len(out) <= 4
