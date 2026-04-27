from __future__ import annotations

from app.research.case_law.tavily_source import (
    _is_likely_case_law_domain,
    _looks_case_law_content,
    _relevance_reason,
    _tokenize_query_terms,
)


def test_case_law_domain_accepts_court_and_government_hosts() -> None:
    assert _is_likely_case_law_domain("https://indiankanoon.org/doc/12345/")
    assert _is_likely_case_law_domain("https://main.sci.gov.in/judgments")
    assert _is_likely_case_law_domain("https://delhihighcourt.nic.in/")


def test_case_law_domain_rejects_known_noisy_hosts() -> None:
    assert not _is_likely_case_law_domain("https://chronicleclub.in/storage/a.pdf")
    assert not _is_likely_case_law_domain("https://bloggers.scripting.com/")
    assert not _is_likely_case_law_domain("https://nsearchives.nseindia.com/emerge/x.pdf")


def test_case_law_content_requires_legal_markers() -> None:
    assert _looks_case_law_content(
        "X vs Y",
        "The High Court dismissed the writ petition and discussed Section 106 of the Act.",
    )
    assert not _looks_case_law_content(
        "Quarterly earnings update",
        "Weighted average shares and listing details for issue period.",
    )


def test_relevance_reason_mentions_matches_and_domain() -> None:
    reason = _relevance_reason(
        query_terms=_tokenize_query_terms("landlord harassment deposit refund"),
        title="Ramesh vs State",
        snippet="High Court discussed landlord harassment and refund under Section 106.",
        url="https://indiankanoon.org/doc/123/",
        legalish_domain=True,
    )
    assert "matches issue terms" in reason
    assert "legal markers" in reason
    assert "source domain looks court/legal" in reason
