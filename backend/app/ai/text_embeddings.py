"""OpenAI text embeddings (shared by local RAG and Pinecone index)."""

from __future__ import annotations

from openai import OpenAI

from app.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.openai_api_key or not texts:
        return []
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [d.embedding for d in resp.data]
    except Exception:
        return []
