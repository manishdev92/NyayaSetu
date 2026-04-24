"""
CLI: embed curated `knowledge_seed` into Pinecone (production sync).

Usage (from `backend/`, venv on):

  export OPENAI_API_KEY=... PINECONE_API_KEY=... PINECONE_INDEX=nyaya-legal-kb
  # optional: RAG_VECTOR_STORE=pinecone
  python -m app.rag.pinecone_ingest
"""

from __future__ import annotations

from app.rag.pinecone_legal_index import upsert_curated_knowledge_from_file


def main() -> None:
    n = upsert_curated_knowledge_from_file()
    print("upserted_vectors", n)


if __name__ == "__main__":
    main()
