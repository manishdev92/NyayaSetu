"""
Sprint P4-1: pluggable legal document sources for statute ingest (no network in core types).
"""

from __future__ import annotations

from typing import Any, NotRequired, Protocol, TypedDict, runtime_checkable


class IngestChunk(TypedDict):
    """One chunk ready to become a knowledge row + vector."""

    text: str
    section: str
    part_index: int


class SourceMetadata(TypedDict, total=False):
    act_id: str
    source_name: str
    source_url: str
    source_version: str
    domain: str
    law_type: str
    verified: bool
    tags: list[str]
    # provenance
    local_path: str


class NormalizedDocument(TypedDict):
    """Single logical document from a source (e.g. one Act file) before chunking."""

    text: str
    meta: SourceMetadata


@runtime_checkable
class LegalDocumentSource(Protocol):
    """Yields normalized {text, metadata} records for the chunker (P4-1)."""

    def iter_documents(self) -> Any:
        """Iterator of NormalizedDocument."""
        ...


class KnowledgeIngestEntry(TypedDict, total=False):
    """Row compatible with `entry_to_metadata` + Pinecone upsert (P4-4)."""

    id: str
    act_id: str
    content: str
    source_name: str
    source_url: str
    source_version: str
    ingested_at: str
    content_sha256: str
    domain: str
    section: str
    law_type: str
    verified: bool
    tags: list[str]
    # backwards compat with knowledge_seed
    law_type_name: NotRequired[str]
