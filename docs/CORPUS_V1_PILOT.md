# v1 corpus — engineering pilot (dev / staging)

**Not legal approval.** This list is a **concrete allow-list** for **pipeline and staging tests** (chunker, `ingest_statutes`, metadata). Product and legal should replace or extend it in **`docs/CORPUS_V1_BOUNDARY.md`** under “Approved v1 corpus” when ready.

| Priority | Short title | India Code / official path | Notes |
|----------|-------------|----------------------------|--------|
| Pilot 1 | Constitution of India | `indiacode.nic.in` (Constitution) | Large; chunk by Part/Article. |
| Pilot 2 | Indian Penal Code, 1860 | `indiacode.nic.in` (IPC) | Common cross-reference. |
| Pilot 3 | Code of Civil Procedure, 1908 | `indiacode.nic.in` (CPC) | Procedure-heavy. |

**Rule:** Ingest only from hosts that pass `is_allowed_legal_source_url` in `backend/app/rag/legal_store/policy.py`, with frontmatter (`act_id`, `source_url`, `source_version`, `ingested_at` semantics) as in `backend/docs/RAG_PINECONE_RUNBOOK.md`.

**ASK** (unchanged from `CORPUS_V1_BOUNDARY.md`): final Act enumeration, state statutes, Tier B vendors, and UI disclaimer for gazette lag.
