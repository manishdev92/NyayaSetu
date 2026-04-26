"""Optional live Pinecone check (P7-2). Skipped in normal test runs; enable with RUN_PINECONE_SMOKE=1."""

from __future__ import annotations

import os

import pytest
from pinecone import Pinecone

pytestmark = pytest.mark.rag


@pytest.mark.skipif(
    os.getenv("RUN_PINECONE_SMOKE", "").strip() != "1",
    reason="set RUN_PINECONE_SMOKE=1 to run (manual / workflow_dispatch)",
)
def test_pinecone_live_index_reachable() -> None:
    key = (os.getenv("PINECONE_API_KEY") or "").strip()
    name = (os.getenv("PINECONE_INDEX") or "").strip()
    if not key or not name:
        pytest.skip("PINECONE_API_KEY and PINECONE_INDEX required for live smoke")
    stats = Pinecone(api_key=key).Index(name).describe_index_stats()
    assert stats is not None
