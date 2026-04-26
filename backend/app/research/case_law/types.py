from __future__ import annotations

from typing import TypedDict


class CaseLawSnippet(TypedDict, total=False):
    """Normalized case-law row from any licensed `CaseLawSource` (Sprint 6)."""

    title: str
    citation: str
    court: str
    year: int
    source: str
    url: str
    snippet: str
