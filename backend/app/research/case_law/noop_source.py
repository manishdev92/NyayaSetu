from __future__ import annotations

from app.research.case_law.types import CaseLawSnippet


class NoopCaseLawSource:
    """Default adapter: no external calls; always empty."""

    def search(self, query: str, *, limit: int = 5) -> list[CaseLawSnippet]:
        return []
