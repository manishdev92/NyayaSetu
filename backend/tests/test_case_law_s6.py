from __future__ import annotations

import pytest

from app.config import settings
from app.research.case_law import NoopCaseLawSource, search_case_law_references


def test_search_case_law_citizen_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "case_law_mode", "noop", raising=False)
    assert search_case_law_references("any query", client_mode="citizen") == []


def test_search_case_law_off_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "case_law_mode", "off", raising=False)
    assert search_case_law_references("x", client_mode="lawyer") == []


def test_search_case_law_noop_lawyer_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "case_law_mode", "noop", raising=False)
    assert search_case_law_references("x", client_mode="lawyer") == []


def test_noop_source_empty() -> None:
    assert NoopCaseLawSource().search("q", limit=3) == []


def test_case_law_mode_invalid_resets_to_off() -> None:
    from app.config import Settings

    s = Settings.model_validate({"case_law_mode": "unlicensed_vendor"})
    assert s.case_law_mode == "off"


def test_case_law_mode_tavily_preview_allowed() -> None:
    from app.config import Settings

    s = Settings.model_validate({"case_law_mode": "tavily_preview"})
    assert s.case_law_mode == "tavily_preview"


def test_search_case_law_respects_case_law_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "case_law_mode", "tavily_preview", raising=False)
    monkeypatch.setattr(settings, "case_law_max_results", 2, raising=False)

    class FakeSource:
        def search(self, query: str, *, limit: int = 5):
            assert query == "rent control precedent"
            assert limit == 2
            return [
                {
                    "title": "A v B",
                    "citation": "A v B",
                    "source": "test",
                    "url": "https://example.com/a-v-b",
                    "snippet": "ratio",
                }
            ]

    monkeypatch.setattr("app.research.case_law.factory.get_case_law_source", lambda: FakeSource())
    rows = search_case_law_references("rent control precedent", client_mode="lawyer", limit=10)
    assert len(rows) == 1
    assert rows[0]["title"] == "A v B"
