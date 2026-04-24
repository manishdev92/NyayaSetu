from __future__ import annotations

from typing import Literal, TypedDict

LawType = Literal["Act", "Rule", "Procedure", "Judgment"]


class LegalKnowledgeEntry(TypedDict, total=False):
    """Single curated knowledge row — ingest only from verified Indian official sources."""

    id: str
    domain: str
    content: str
    source_name: str
    source_url: str
    law_type: LawType
    section: str
    verified: bool
    tags: list[str]
