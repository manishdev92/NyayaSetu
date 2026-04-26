import pytest

from app.services.ai_service import _build_rag_metadata_hints

pytestmark = pytest.mark.rag


def test_build_rag_metadata_hints_extracts_act_and_year() -> None:
    hints = _build_rag_metadata_hints(
        "Need draft under BNSS 2023 for police complaint",
        entities=["bnss", "police"],
        city="Varanasi",
        taxonomy_ui={
            "issue_type": "police",
            "severity": "high",
            "jurisdiction_type": "district",
            "sub_type": "general",
        },
    )
    assert hints.get("act_id") == "bnss-2023"
    assert hints.get("source_year") == 2023
    assert hints.get("city_hint") == "Varanasi"
    assert hints.get("jurisdiction_type") == "district"


def test_build_rag_metadata_hints_empty_when_no_signal() -> None:
    hints = _build_rag_metadata_hints(
        "Need legal help",
        entities=[],
        city=None,
        taxonomy_ui={
            "issue_type": "general",
            "severity": "medium",
            "jurisdiction_type": "state",
            "sub_type": "unspecified",
        },
    )
    assert "act_id" not in hints
    assert "source_year" not in hints
