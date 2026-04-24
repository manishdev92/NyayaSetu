"""Phase 6.5: emergency triple-confirmation and short FIR template."""

from __future__ import annotations

from app.services.emergency_fir_draft import (
    build_incident_line,
    parse_emergency_narrative_context,
    render_emergency_fir_contextual,
    render_emergency_fir_short,
)
from app.services.priority_engine import detect_law_and_order_priority, infer_emergency_triple_confirmed


def test_infer_emergency_triple_all_yes() -> None:
    text = """fight between two groups for land
ongoing: yes
injury: yes
police help: yes
"""
    assert infer_emergency_triple_confirmed(text) is True
    out = detect_law_and_order_priority(text)
    assert out["priority"] == "law_and_order"
    assert out["is_emergency"] is True


def test_infer_emergency_incomplete() -> None:
    text = "fight between two groups for land\nongoing: yes\ninjury: no"
    assert infer_emergency_triple_confirmed(text) is False


def test_contextual_incident_line() -> None:
    ctx = parse_emergency_narrative_context(
        "brutal fight at Sector 21\ninjury: yes\nongoing: yes",
        location_hint="Sector 21",
    )
    line = build_incident_line(ctx)
    assert "fight" in line.lower() or "violent" in line.lower() or "physical" in line.lower()
    assert "Sector 21" in line
    assert "injured" in line.lower() or "1 person" in line


def test_incident_line_hindi_devanagari() -> None:
    ctx = parse_emergency_narrative_context(
        "brutal fight at Sector 21\ninjury: yes",
        location_hint="Sector 21",
    )
    line = build_incident_line(ctx, language="hi")
    assert "Sector 21" in line
    assert any(c in line for c in "घटना")


def test_incident_line_roman_hindi() -> None:
    ctx = parse_emergency_narrative_context(
        "brutal fight at Sector 21\ninjury: yes",
        location_hint="Sector 21",
    )
    line = build_incident_line(ctx, language="hi_latn")
    assert "Sector 21" in line
    assert "par" in line.lower()
    assert "ghatna" in line.lower()


def test_emergency_fir_template_renders() -> None:
    doc = render_emergency_fir_short(
        police_station="[PS]",
        district="Test District",
        location="Village X",
        name="Test User",
    )
    assert "Station House Officer" in doc
    assert "FIR" in doc
    assert "Village X" in doc
    assert "Test User" in doc


def test_communal_clash_omits_bad_location_phrase() -> None:
    ctx = parse_emergency_narrative_context(
        "fight broke out between two religions many injured",
    )
    line = build_incident_line(ctx)
    assert "communal" in line.lower()
    assert "two religions" not in line.lower()


def test_emergency_fir_contextual_template() -> None:
    doc = render_emergency_fir_contextual(
        police_station="[PS]",
        district="X District",
        incident_line="A physical fight occurred at Village Y. 2 person(s) were injured.",
        name="A User",
    )
    assert "Station House Officer" in doc
    assert "Village Y" in doc
    assert "2 person" in doc


def test_emergency_fir_contextual_template_hindi() -> None:
    doc = render_emergency_fir_contextual(
        police_station="[PS]",
        district="X District",
        incident_line="Sector 21 पर शारीरिक झगड़ा हुआ।",
        name="A User",
        language="hi",
    )
    assert "थाना प्रभारी" in doc
    assert "FIR" in doc
    assert "Sector 21" in doc


def test_emergency_fir_contextual_template_roman_hindi() -> None:
    doc = render_emergency_fir_contextual(
        police_station="[PS]",
        district="X District",
        incident_line="Sector 21 par jhagda hua.",
        name="A User",
        language="hi_latn",
    )
    assert "Thanadhikari" in doc
    assert "FIR" in doc
    assert "Sector 21" in doc
