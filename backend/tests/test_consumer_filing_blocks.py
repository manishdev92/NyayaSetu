from __future__ import annotations

from app.services.ai_service import _build_consumer_filing_blocks


def test_consumer_filing_blocks_populated_for_consumer_category() -> None:
    out = _build_consumer_filing_blocks(
        user_input="I paid Rs. 9000 for service plan but no repair",
        category="consumer",
        task_type="draft_letter",
        authority_primary="District Consumer Disputes Redressal Commission (Consumer Commission — district)",
    )
    assert isinstance(out.get("forum_caption"), str)
    assert "District Consumer Disputes Redressal Commission" in str(out.get("forum_caption"))
    assert any("₹9000" in x for x in out.get("prayer_items") or [])
    assert len(out.get("annexure_checklist") or []) >= 3


def test_consumer_filing_blocks_empty_for_non_consumer_default() -> None:
    out = _build_consumer_filing_blocks(
        user_input="salary not paid",
        category="labour",
        task_type="draft_letter",
        authority_primary="Labour Commissioner",
    )
    assert out.get("forum_caption") is None
    assert out.get("prayer_items") == []
    assert out.get("annexure_checklist") == []


def test_consumer_filing_blocks_state_level_caption() -> None:
    out = _build_consumer_filing_blocks(
        user_input="defective appliance complaint",
        category="consumer",
        task_type="consumer_complaint_filing",
        authority_primary="State Commission; National Commission (limits)",
        city="Bengaluru",
    )
    assert out.get("forum_caption") == "Before the State Consumer Disputes Redressal Commission, [State]"


def test_consumer_filing_blocks_city_hint_for_district_caption() -> None:
    out = _build_consumer_filing_blocks(
        user_input="service deficiency complaint",
        category="consumer",
        task_type="consumer_complaint_filing",
        authority_primary="District Consumer Disputes Redressal Commission (Consumer Commission — district)",
        city="Varanasi",
    )
    assert "territorial jurisdiction over Varanasi" in str(out.get("forum_caption"))
