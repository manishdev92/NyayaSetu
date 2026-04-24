"""Pinecone RAG path: mocked client + settings (NS-S5-02)."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.ai.rag_pipeline import run_strict_rag_pipeline
from app.config import settings
from app.rag import pinecone_legal_index as pci


def test_pinecone_not_configured_uses_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rag_vector_store", "pinecone")
    monkeypatch.setattr(settings, "pinecone_api_key", "")
    monkeypatch.setattr(pci, "_index", None, raising=False)
    r = run_strict_rag_pipeline("fraud complaint police fir", "police", top_k=3)
    assert r["grounding_label"] in ("rag_retrieved", "general_not_case_specific", "no_match")


@mock.patch(
    "app.rag.pinecone_legal_index.embed_texts",
    return_value=[[0.01] * 1536],
)
@mock.patch("app.rag.pinecone_legal_index._get_index", autospec=True)
def test_pinecone_happy_path(mock_index, _em, caplog, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "x")
    monkeypatch.setattr(settings, "rag_vector_store", "pinecone")
    monkeypatch.setattr(settings, "pinecone_api_key", "k")
    monkeypatch.setattr(settings, "pinecone_index", "idx")
    pci._index = None

    class M:
        score = 0.62
        id = "bns-fir-overview"
        metadata = {
            "entry_id": "bns-fir-overview",
            "domain": "criminal",
            "content": "FIR and investigation",
            "source_name": "Test",
            "source_url": "https://www.indiacode.nic.in/",
            "section": "s1",
            "tags_csv": "fir,police,ipc",
            "verified": True,
        }

    class R:
        matches = [M()]

    def fake_query(
        *a,
        **kw,
    ):
        return R()

    mock_index.return_value.query = fake_query

    caplog.set_level("INFO", logger="app.ai.rag_pipeline")
    r = run_strict_rag_pipeline("I need a police FIR in Varanasi", "police", top_k=3)
    assert isinstance(r.get("retrieved_laws"), list)
    lines = " ".join(caplog.messages)
    assert "rag_pipeline" in lines
