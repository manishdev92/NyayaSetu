from __future__ import annotations

from typing import TypedDict


class AuthorityCandidate(TypedDict, total=False):
    """Normalized row from any search source—never LLM-generated."""

    name: str
    address: str | None
    phone: str | None
    email: str | None
    source: str  # tavily | serpapi | bing | gov_in | local_json
    url: str
    snippet: str | None
