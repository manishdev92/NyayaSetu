# Prioritized sprints and tasks (NyayaSetu)

**Purpose:** Ordered backlog so work can be picked **one task at a time**, implemented, **tested locally**, verified via **GitHub Actions** on push/PR (`/.github/workflows/ci.yml`: backend `python -m pytest tests/ -q`, frontend `tsc` + `build`), then merged. When a task needs product or legal input, it is marked **ASK**.

**Definition of done (each task):** Code + tests where applicable; `cd backend && python -m pytest tests/ -q`; `cd frontend && npx tsc --noEmit && npm run build` (with CI env vars if needed); no forbidden secrets; PR passes CI; merge to `main`/`master`.

**Note on Pinecone:** CI runs **without** live Pinecone keys; tests use mocks/monkeypatch (`test_pinecone_rag.py`). Live Pinecone smoke remains **manual** or optional workflow (see `backend/docs/RAG_PINECONE_RUNBOOK.md`).

---

## Sprint 0 — Lock scope and interfaces (1–3 days)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P0-1 | Document **user personas** (citizen vs lawyer) in one page: goals, disclaimers, depth expectations | **Done** — `docs/USER_PERSONAS.md` (v1 lawyer anchor: solo/small chamber unless product overrides) | Confirm v1 lawyer anchor: solo vs chamber-first |
| P0-2 | Define **v1 corpus boundary** (which Acts / sources are allowed for automated ingest v1) | **Done** — `docs/CORPUS_V1_BOUNDARY.md` (Tier A/B/C + metadata + **ASK** checklist); **engineering pilot** Acts in `docs/CORPUS_V1_PILOT.md` (not legal sign-off) | Legal/product: fill enumerated Act list + disclaimers |
| P0-3 | Add **engineering mode flag** design: e.g. `X-Client-Mode: citizen \| lawyer` or `user_tier` in body (behind auth later) | **Done** — `docs/CLIENT_MODE_DESIGN.md` + optional `client_mode` JSON / `X-Client-Mode`, echo on `GenerateResponse`, plumbed into `generate_legal_response` | Clerk / subscription field for “lawyer” yet? |

---

## Sprint 1 — Lawyer vs citizen (product slice, minimal code)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P1-1 | Extend generate schema (optional) for **client mode / tier**; default `citizen` | **Done** — P0-3 + optional **`LAWYER_CLIENT_MODE_REQUIRES_USER_ID`**; optional **`LAWYER_CLIENT_MODE_REQUIRES_PRO`** with **`BILLING_MODE=stripe`** (403 `lawyer_mode_requires_pro`); **`GET /config` / `GET /ready` → `lawyer_mode_requires_pro`**, `lawyer_pro_gate_active`; chat uses **`GET /billing/entitlements`**. *Optional later:* verify Clerk **JWT** on the API (Bearer) if product requires. | — |
| P1-2 | Wire tier into **`run_strict_rag_pipeline` `top_k`** (e.g. citizen 8 → keep; lawyer 12–16) + single pytest | **Done** — `client_mode` → `_rag_top_k_for_client_mode`; settings `RAG_TOP_K_CITIZEN` / `RAG_TOP_K_LAWYER` (defaults 8 / 12); `test_rag_top_k_for_client_mode_uses_settings` | Tune defaults per telemetry |
| P1-3 | API + `/ready` or public config: expose **non-secret** “modes supported” for UI | **Done** — `client_modes_supported` on `GET /ready` + `GET /config`; env `CLIENT_MODES_SUPPORTED`; `PublicConfig.client_modes_supported` in FE | — |
| P1-4 | Frontend: toggle or route guard for **lawyer mode** (feature flag env) | **Done** — `NEXT_PUBLIC_LAWYER_MODE_UI` + `client_modes_supported` includes `lawyer`; `LegalChat` segmented control, `client_mode` on stream payload, `lib/lawyerModeUi.ts` | — |

---

## Sprint 2 — Q&A vs drafting (answer + optional document)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P2-1 | Add **`response_style`** or `task_type`: `draft_letter \| qa_only \| draft_with_qa`** in request schema | **Done** — `GenerateRequest` / `GenerateResponse` in `generate_schemas.py`; `generate_legal_response(..., task_type=...)` | — |
| P2-2 | Prompt + formatter branches: **qa_only** prioritizes direct answer; **draft_*** keeps current letter flow | **Done** — `_task_type_formatter_addon` + `_normalize_task_type` in `ai_service.py` (formatter system tail) | — |
| P2-3 | Tests: golden or unit tests for new enum (no OpenAI if mocked) | **Done** — `tests/test_task_type.py` | — |
| P2-4 | LegalChat: mode selector when flag on | **Done** — `NEXT_PUBLIC_RESPONSE_TASK_UI` + `lib/responseTaskUi.ts` + i18n; sends `task_type` on stream/sync | — |

---

## Sprint 3 — RAG quality knobs (config + observability)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P3-1 | Settings: **`RAG_TOP_K_DEFAULT`**, tier top-k in `app/config.py` + `.env.example` | **Done** — `RAG_TOP_K_DEFAULT` aliases `RAG_TOP_K_CITIZEN`; runbook + `.env.example` | — |
| P3-2 | Per-tier Pinecone pre-fetch (cost-aware cap) | **Done** — `PINECONE_QUERY_CANDIDATES_LAWYER` + `Settings.pinecone_query_fetch_size` → `run_strict_rag_pipeline` / `pinecone_rag_scored` | — |
| P3-3 | PII-safe RAG log: segment fields | **Done** — `client_mode`, `task_type`, optional `pinecone_fetch` in `rag_pipeline` JSON line | — |
| P3-4 | Tests for new fields and tier config | **Done** — `test_rag_pipeline_observability.py` + `test_rag_tier_config.py` | — |

---

## Sprint 4 — Ingestion pipeline MVP (statutes slice)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P4-1 | **Source adapter interface**: `LegalDocumentSource` → normalized records `{text, metadata}` | **Done** — `app/rag/ingest/types.py` (`LegalDocumentSource`, `NormalizedDocument`) + `LocalMarkdownDirectorySource` | Licensed drop path only |
| P4-2 | **Chunker v1**: hierarchical by Act / Section (configurable size overlap) | **Done** — `app/rag/ingest/chunker.py` (`chunk_statute_text`, char budget + overlap) | Char proxy for tokens |
| P4-3 | **CLI job**: `python -m app.rag.jobs.ingest_statutes` (dry-run, batch embed, upsert) | **Done** — `app/rag/jobs/ingest_statutes.py`; reuses `upsert_knowledge_entries` | Same Pinecone namespace as seed unless you split indexes |
| P4-4 | **Versioning**: store `source_version`, `ingested_at` in metadata | **Done** — `entry_to_metadata` / `metadata_to_entry` + pipeline rows | — |
| P4-5 | Tests: chunker + metadata unit tests (no network) | **Done** — `test_ingest_statutes_chunker.py`, `test_ingest_pinecone_metadata.py`, fixture `sample_act.md` | — |

---

## Sprint 5 — Retrieval: multi-namespace / metadata filters

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P5-1 | Pinecone query: **metadata filter** by `act_id`, `year` when provided | **Done** — `metadata_hints` → Pinecone `filter` (`act_id`, `source_year`) in `pinecone_rag_scored`; defensive post-filtering retained | — |
| P5-2 | Generate path: pass **jurisdiction / act hints** from classifier into RAG (optional) | **Done** — `_build_rag_metadata_hints(...)` in `ai_service.py`; passes `act_id` / `source_year` (+ future-safe jurisdiction/city hints) into `run_strict_rag_pipeline` | — |

---

## Sprint 6 — Case law and external research (high compliance)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P6-1 | **ASK** vendor/API choice (licensed case law) — design integration only | `docs/CASE_LAW_S6_DESIGN.md` (no scraping prod) | Budget + vendor |
| P6-2 | Adapter: `CaseLawSource.search(query) -> normalized snippets` | **MVP in repo** — `app/research/case_law/` + `NoopCaseLawSource`; `CASE_LAW_MODE=off` or `noop`; `case_law_references` on `/generate` (lawyer + `noop`); `GET /config` → `case_law_research_mode` | Real vendor: API keys in GH secrets for staging? |
| P6-3 | UI: “case references” panel for lawyer tier | **Done** — `NEXT_PUBLIC_CASE_LAW_UI` + `case_law_research_mode` in chat when API ≠ `off` | — |

---

## Sprint 7 — CI hardening (optional but recommended)

| Priority | Task | Outcome | ASK |
|----------|------|---------|-----|
| P7-1 | Add **marker** `@pytest.mark.rag` for RAG-only tests; document in `GOLDEN_ROUTING.md` | **Done** — `backend/pytest.ini` marker; module marks on RAG/ingest tests; `GOLDEN_ROUTING.md` **Pytest: `@pytest.mark.rag`** | Split job in GHA? (optional) |
| P7-2 | Optional workflow: **manual** `workflow_dispatch` with secrets for Pinecone smoke (not on every PR) | **Done** — `.github/workflows/pinecone-smoke.yml` + `tests/test_pinecone_smoke.py` (skipped unless `RUN_PINECONE_SMOKE=1` + env) | Repo admin to add `PINECONE_API_KEY` / `PINECONE_INDEX` |

---

## Execution order (single thread)

Work **P0 → P1 → P2 → P3** before heavy ingest (**P4**), unless **P0-2** is blocked — then still do **P1–P3** with current curated KB. **P5–P6** need **P4** corpus or **ASK** decisions.

---

## When the implementer will ask you

- Allowed **sources** and **copyright** stance for v1 ingest.  
- **Lawyer** authentication (Clerk role? Stripe SKU?).  
- Default **top_k** / cost caps for lawyer tier.  
- **Case law** vendor or “no case law in v1.”  
- **Product copy** and **Hindi** strings for new UI modes.

---

## Quick verification commands (local = same spirit as CI)

```bash
./scripts/check-no-forbidden-secrets.sh
cd backend && pip install -r requirements.txt && pip install "pytest>=7.0.0" && python -m pytest tests/ -q
cd frontend && npm ci && npx tsc --noEmit && npm run build
```

**Related:** `docs/USER_REQUEST_FLOW.md`, `docs/USER_PERSONAS.md`, `docs/CORPUS_V1_BOUNDARY.md`, `docs/CLIENT_MODE_DESIGN.md`, `backend/docs/RAG_PINECONE_RUNBOOK.md`, `backend/docs/GOLDEN_ROUTING.md`.
