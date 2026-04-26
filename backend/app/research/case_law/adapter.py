from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.research.case_law.types import CaseLawSnippet


@runtime_checkable
class CaseLawSource(Protocol):
    """Pluggable case-law search (Sprint 6 P6-2). No web scraping in repo — use licensed APIs only."""

    def search(self, query: str, *, limit: int = 5) -> list[CaseLawSnippet]:
        """Return short snippets; empty when unavailable."""
