"""P4-4: version fields round-trip via metadata helpers (no network)."""

from __future__ import annotations

import pytest
from app.rag.pinecone_legal_index import entry_to_metadata, metadata_to_entry

pytestmark = pytest.mark.rag


def test_entry_to_metadata_ingest_fields() -> None:
    e = {
        "id": "a__h__p0",
        "content": "text",
        "source_name": "N",
        "source_url": "https://www.indiacode.nic.in/x",
        "domain": "civil",
        "section": "1",
        "act_id": "bns-2023",
        "source_version": "2.0",
        "ingested_at": "2026-01-15T00:00:00Z",
        "content_sha256": "a" * 64,
    }
    m = entry_to_metadata(e)
    assert m.get("act_id") == "bns-2023"
    assert m.get("ingested_at") and "2026" in str(m.get("ingested_at"))
    back = metadata_to_entry(m, "a__h__p0")
    assert back
    assert back.get("act_id") == "bns-2023"
    assert back.get("source_version") == "2.0"
    assert back.get("ingested_at") and "2026" in str(back.get("ingested_at"))
    assert back.get("content_sha256") == "a" * 64
