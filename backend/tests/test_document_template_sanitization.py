from __future__ import annotations

from app.services.ai_service import (
    _consumer_letter_signoff_looks_complete,
    _normalize_document_spacing,
    _postprocess_document,
    _strip_repeated_handfill_after_letter_closing,
)


def test_non_police_draft_strips_police_contact_placeholder() -> None:
    raw = (
        "Date: ____\n"
        "Official contact to be noted by you (from chowki/station notice board, state/district police website, or 112 for emergency only — never guess): ____\n"
        "To,\nThe Tehsildar,\nSubject: Property dispute\n"
    )
    out = _normalize_document_spacing(raw, issue_type="land")
    assert "Official contact to be noted by you" not in out
    assert "The Tehsildar" in out


def test_police_draft_keeps_police_contact_placeholder() -> None:
    raw = (
        "Date: ____\n"
        "Official contact to be noted by you (from chowki/station notice board, state/district police website, or 112 for emergency only — never guess): ____\n"
        "To,\nThe Station House Officer,\n"
    )
    out = _normalize_document_spacing(raw, issue_type="police")
    assert "Official contact to be noted by you" in out


def test_postprocess_moves_top_print_block_and_appends_bottom_details() -> None:
    raw = (
        "Print & fill\n"
        "Date: __________________\n"
        "Name (complainant / applicant): __________________\n"
        "Mobile number: __________________\n"
        "Full postal address: __________________\n"
        "\n"
        "To,\nThe District Consumer Disputes Redressal Commission,\nSubject: Complaint\n"
    )
    out = _postprocess_document(
        raw,
        issue_type="consumer",
        user_details={"full_name": "Asha", "phone": "9999999999", "address": "Bengaluru"},
        city="Bengaluru",
    )
    assert not out.startswith("Print & fill")
    assert "Name (complainant / applicant):" not in out.split("\n", 8)[0:8]
    assert "Complainant / Applicant Details" in out
    assert "Name: Asha" in out
    assert "Mobile: 9999999999" in out
    assert "City/District: Bengaluru" in out


def test_postprocess_strips_roman_hindi_top_fill_block_for_consumer() -> None:
    raw = (
        "Tithi:\n"
        "Naam (shikayatakarta):\n"
        "Mobile number:\n"
        "Poora postal pata:\n"
        "Aadhikarik sampark (board/website/112 se likhen — random number na guess karein):\n"
        "\n"
        "To,\nThe District Consumer Disputes Redressal Commission,\nVishay: Complaint\n"
    )
    out = _postprocess_document(
        raw,
        issue_type="consumer",
        user_details={"full_name": "Rajesh"},
        city="Varanasi",
    )
    assert not out.startswith("Tithi:")
    assert "Aadhikarik sampark" not in out
    assert "Complainant / Applicant Details" in out


def test_strip_handfill_after_closing_removes_loose_block() -> None:
    raw = (
        "Yours faithfully,\n"
        "Complainant\n"
        "Date:\n"
        "Name (complainant / applicant):\n"
        "Mobile number:\n"
    )
    out = _strip_repeated_handfill_after_letter_closing(raw)
    assert "Date:" not in out
    assert "Name (complainant" not in out
    assert "Yours faithfully" in out


def test_postprocess_merges_loose_closing_with_single_party_block() -> None:
    raw = (
        "Respected Sir/Madam,\n"
        "I submit the following.\n"
        "Yours faithfully,\n"
        "Complainant\n"
        "Date:\n"
        "Name (complainant / applicant):\n"
        "Mobile number:\n"
        "Full postal address:\n"
        "Official contact to be noted by you (from chowki/station notice board): ____\n"
    )
    out = _postprocess_document(
        raw,
        issue_type="consumer",
        user_details={},
        city="Pune",
        category="consumer",
    )
    assert "Official contact to be noted" not in out
    assert "Name (complainant / applicant)" not in out
    assert out.count("Complainant / Applicant Details") == 1
    assert "City/District: Pune" in out


def test_postprocess_skips_extra_footer_when_dcdrc_signoff_complete() -> None:
    raw = (
        "To,\nThe District Consumer Disputes Redressal Commission, [X]\n\n"
        "Subject: Complaint about phone\n\n"
        "Respected Sir/Madam,\nFacts.\n\n"
        "Thanking you.\n"
        "Yours sincerely,\n"
        "[Your Name]\n"
        "[Address]\n"
        "[Mobile Number]\n"
        "[Date]\n"
    )
    out = _postprocess_document(
        raw,
        issue_type="consumer",
        user_details={},
        city="Pune",
        category="consumer",
    )
    assert "Complainant / Applicant Details" not in out
    assert "[Your Name]" in out


def test_signoff_complete_detector() -> None:
    assert _consumer_letter_signoff_looks_complete("x\nThanking you.\nYours sincerely,\n[Your Name]\n[Address]\n")
    assert not _consumer_letter_signoff_looks_complete("Yours sincerely,\n[Name]\n")
