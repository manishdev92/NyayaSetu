# Pinecone RAG — production runbook (P4-01)

This app can serve curated legal knowledge from an **in-process** embed index (`RAG_VECTOR_STORE=local`, default) or a **Pinecone** index (`RAG_VECTOR_STORE=pinecone`).

## 1. Index spec

- **Embedding model:** `text-embedding-3-small` in `app/ai/text_embeddings.py` → **1536 dimensions** (default for this model).  
- **Pinecone metric:** `cosine` (matches typical OpenAI embedding usage).  
- **Create the index** in the Pinecone console (serverless or pod) with dimension **1536** and cosine. Name it to match `PINECONE_INDEX` (default `nyaya-legal-kb`).

## 2. Environment (API)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Embeddings + optional generation |
| `RAG_VECTOR_STORE` | `local` or `pinecone` |
| `PINECONE_API_KEY` | From Pinecone |
| `PINECONE_INDEX` | Index name |
| `PINECONE_NAMESPACE` | Optional; default `""` |
| `PINECONE_QUERY_CANDIDATES` | Pre-filter fetch size (default 48) |

`GET /ready` includes `rag_vector_store` and `pinecone_configured` (key + index name, non-secret).

## 3. Ingest (upsert)

From the `backend/` directory with the venv active:

```bash
export OPENAI_API_KEY=sk-... PINECONE_API_KEY=... PINECONE_INDEX=nyaya-legal-kb
python -m app.rag.pinecone_ingest
```

This calls `upsert_curated_knowledge_from_file` in `app/rag/pinecone_legal_index.py` using the same curated source as the local RAG path.

## 4. Rollout

1. Create index → run ingest in staging → set `RAG_VECTOR_STORE=pinecone` on one environment → run routing/RAG tests (`test_pinecone_rag.py`, `test_rag_pipeline_observability.py`) → monitor logs for PII-safe retrieval lines.  
2. Roll back by switching `RAG_VECTOR_STORE=local` (no code deploy if only env changes).

## 5. See also

- Ingest entrypoint: `app/rag/pinecone_ingest.py`  
- Query path: `app/rag/pinecone_legal_index.py`  
- `docs/ROADMAP_TRACKER.md` Phase 4 row
