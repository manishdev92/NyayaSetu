"""Sprint P3: RAG tier config (default alias, Pinecone fetch by client_mode)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.rag

from app.config import Settings


def test_pinecone_query_fetch_size_citizen_and_lawyer_bump() -> None:
    s = Settings(
        pinecone_query_candidates=40,
        pinecone_query_candidates_lawyer=None,
    )
    assert s.pinecone_query_fetch_size("citizen") == 40
    assert s.pinecone_query_fetch_size("lawyer") == min(200, max(8, 40 + 24))


def test_pinecone_query_lawyer_explicit() -> None:
    s = Settings(
        pinecone_query_candidates=48,
        pinecone_query_candidates_lawyer=90,
    )
    assert s.pinecone_query_fetch_size("lawyer") == 90
    assert s.pinecone_query_fetch_size("citizen") == 48


def test_rag_top_k_default_env_alias_resolves_to_citizen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_TOP_K_CITIZEN", raising=False)
    monkeypatch.delenv("RAG_TOP_K_DEFAULT", raising=False)
    monkeypatch.setenv("RAG_TOP_K_DEFAULT", "11")
    # Avoid shadowing from backend/.env when RAG_TOP_K_CITIZEN is set there.
    s = Settings(_env_file=None)
    assert s.rag_top_k_citizen == 11
