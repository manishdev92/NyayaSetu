# NyayaSetu — phase tracker (edit in place)

Use this as a **living** sheet. **Owner / ETA / Blockers** are placeholders for you to fill. **Status** and **Evidence** reflect the repository as of the last manual refresh.

| Phase | Goal (from roadmap) | Status | ~% (repo) | Evidence in repo (primary) | Key tests (examples) | Owner | ETA | Blockers / notes |
|-------|---------------------|--------|-----------|----------------------------|----------------------|-------|-----|------------------|
| **0** | Foundation: FE+BE, API, basic generation | **Done** | **~95%** | `frontend/`, `backend/app/main.py`, `backend/app/api/v1/generate.py` | — (smoke: run API + UI) | | | |
| **1** | Core MVP: document + next steps + explanation; upload | **In progress** | **~90%** | `POST /ingest-document`, `document_ingest.py` + optional `document_ocr.py` (`INGEST_OCR_PROVIDER`), `LegalChat` | `test_document_ingest.py` | | | Text-empty PDFs: optional PyMuPDF raster + OCR when OCR provider on (`INGEST_OCR_PDF_MAX_PAGES`). |
| **2** | Auth + monetization + usage | **Largely done** | **~98%** | Stripe + entitlements (SQLite or optional Postgres via `ENTITLEMENTS_DATABASE_URL`), `GET /billing/entitlements`, Pro UI + portal; optional **`REDIS_URL`** for shared daily counters (`usage_limit.py`, `docs/RATE_LIMIT_REDIS.md`) | `test_billing_stripe.py`, `test_pro_entitlements.py`, `test_usage_limit_redis.py` | | | |
| **3** | Multimodal: PDF/images, extract + explain | **Largely done** | **~70%** | P3-01 OCR + P3-02 empty-PDF hint + P3-03 raster PDF OCR; `docs/OCR_AND_AWS.md` | `test_document_ingest.py` | | | Tune `INGEST_OCR_PDF_MAX_PAGES` for cost/latency in prod. |
| **4** | RAG + knowledge layer | **Largely done** | **~95%** | PII-safe RAG logs + `RAG_VECTOR_STORE=local|pinecone`, `app/rag/pinecone_legal_index.py`, `python -m app.rag.pinecone_ingest` (upsert) | `test_rag_pipeline_observability.py`, `test_pinecone_rag.py` | | | **Prod:** create Pinecone index 1536-dim cosine, run ingest, set env. |
| **5** | Localization & context (location, India, Hindi) | **Largely done** | **~90%** | `frontend/lib/i18n.ts` (en/hi/hiLatn UI), authority status labels, dashboard strings; `response_language` `hi_latn` on `GenerateRequest`, `ai_service` Roman-Hindi addon, `test_response_language.py` | `test_response_language.py` | | | **Gap:** deeper Hindi UI for every control. |
| **6** | Multi-agent + guardrails + trust | **Largely done** | **~76%** | `backend/app/services/phase6_agents.py`, `backend/app/services/phase6_guardrails.py`, `backend/app/services/crisis_triage.py`, `backend/app/trust/trust_engine.py`, `backend/app/ai/evaluator.py`, `backend/app/evaluators/legal_verifier.py` | `test_crisis_triage.py`, `test_hybrid_routing.py`, `test_strict_land_guard.py`, `test_emergency_*.py`, `test_phase6_*.py` + `test_authority_domain_resolution.py` | | | Authority gate: `test_strict_gate_rejects_labour_for_criminal_police`. Log: `backend/app/logs/README.md`. |
| **7** | Offline + model fallback + sync | **Largely done** | **~72%** | SW + offline queue (localStorage or IndexedDB), async queue API, auto-retry on `online` flag | — | | | Optional: larger payloads / sync beyond IDB. |
| **8** | Advanced: lawyer dashboard, bulk, case tracking | **In progress** | **~35%** | `docs/P8_DASHBOARD_SPEC.md`, `/dashboard` + `GET|POST|DELETE /dashboard/cases`, SQLite `dashboard_cases_store` | `test_dashboard_cases.py` | | | Detail view / replay from saved `result` JSON next. |
| **9** | GTM: channels, pilot users, feedback | **N/A in repo** | **0%** | (process) | — | | | Use analytics + issue tracker outside git. |
| **10** | Android / mass mobile | **Not started** | **0%** | (no `mobile/`) | — | | | Expo/Flutter as per roadmap. |

### Phases 1–10 — backlog (post S1–S6; pick top-down)

| ID | Phase | Task | Status | Notes |
|----|-------|------|--------|--------|
| **P1-01** | 1 | `GET /config` exposes `max_upload_bytes`; LegalChat shows cap + client pre-check + i18n | **Done** | Server cap unchanged (`app.config`); `test_public_config` |
| **P1-02** | 1 | Optional: stable `error_code` on `/ingest-document` errors for i18n (size, image, type) | **Done** | `DocumentIngestError` + JSON `detail.{message,error_code}`; 413/422/429; `IngestRequestError` + `messageForIngestError` in FE |
| **P2-01** | 2 | Stripe Checkout (test → prod), webhook, map Clerk user → customer | **Done** | `billing.py`, `STRIPE.md`, `createStripeCheckoutSession` + paywall when `stripe_checkout_ready`; `test_billing_stripe.py`; prod: set `STRIPE_WEBHOOK_SECRET`, price, `PUBLIC_APP_URL` |
| **P2-02** | 2 | Entitlements: Pro tier gates (limits / features) from subscription state | **Done** | Webhook → SQLite; `active`/`trialing` → `daily_limit_pro`; `GET /billing/entitlements`; `subscription_data.metadata` on Checkout; `test_pro_entitlements.py` |
| **P2-03** | 2 | Stripe Customer Portal + “Manage billing” in UI | **Done** | `POST /billing/create-portal-session`, `stripe_portal_ready` on `GET /config`, FE `createBillingPortalSession` + Pro panel button; `STRIPE.md` |
| **P3-01** | 3 | Image OCR path (Tesseract, cloud vision, or OpenAI vision) behind flag + cost cap | **Done** | `document_ocr.py`, `INGEST_OCR_*`, AWS Textract + resize cap; `GET /config` `ingest_ocr_*`; FE hints + `ingestAfterImage` |
| **P3-02** | 3 | UX: “Explain what we can’t read” flow for scans / image-only PDFs | **Done** | `ingestExplainScanHint` + `INGEST_SERVER_WARN_NO_TEXT_PDF` match in `LegalChat` when extract empty |
| **P3-03** | 3 | OCR for text-empty PDF (rasterize first N pages + same OCR as images) | **Done** | `pymupdf` + `ocr_pdf_raster_pages`, `INGEST_OCR_PDF_MAX_PAGES`; `test_document_ingest.py`; AWS async path still optional |
| **P4-01** | 4 | Runbook: Pinecone index 1536-dim, ingest, `RAG_VECTOR_STORE=pinecone` in prod | **Done** | `backend/docs/RAG_PINECONE_RUNBOOK.md` (1536 = `text-embedding-3-small`) |
| **P5-01** | 5 | i18n sweep: remaining hard-coded UI strings in `page.tsx` / `LegalChat` / errors | **Largely done** | `/generate` + `/generate-stream`: structured `detail` + SSE `error_code`; FE `ServerApiError` + `apiErrorMessages` map; `authority.status` + dashboard API errors; `tests/test_generate_errors.py` |
| **P5-02** | 5 | Optional `hi-Latn` or regional variants | **Done** | API `response_language` `hi_latn` / `hi-Latn`; FE locale `hiLatn`; `_formatter_language_addon` Roman Hindi; `test_response_language.py` |
| **P6-01** | 6 | Eval harness: golden routing sets + periodic legal verifier review | **Largely done** | `backend/docs/GOLDEN_ROUTING.md` (incl. weekly CI) + `EVALUATORS.md` + `test_classifier_golden_cases.py`; `.github/workflows/routing-golden-weekly.yml` |
| **P7-01** | 7 | PWA manifest + service worker: cache shell; offline “read only” or queued send | **Largely done** | `public/sw.js` (shell cache + `/offline`), `ServiceWorkerRegister`, `app/offline/page.tsx`; queued send = **P7-02** |
| **P7-02** | 7 | Retry queue for failed generate when back online | **Done** | `lib/offlineGenerateQueue.ts` (localStorage, max 5), `StreamNetworkFailed` in `api.ts`, LegalChat banner + `online` hint |
| **P7-03** | 7 | Optional: auto-retry queued generate on `online` + IndexedDB for larger queue | **Done** | `NEXT_PUBLIC_AUTO_RETRY_QUEUE_ONLINE` + `NEXT_PUBLIC_OFFLINE_QUEUE_IDB` + async queue in `offlineGenerateQueue.ts` / `LegalChat` |
| **P8-01** | 8 | Lawyer / org dashboard (auth, case list) — product spec first | **Largely done** | `docs/P8_DASHBOARD_SPEC.md` + `/dashboard` UI + `dashboard_cases` API + `frontend/services/api.ts`; optional detail/replay |
| **P9-01** | 9 | GTM: analytics, pilot cohort, feedback loop (outside repo) | N/A | Process |
| **P10-01** | 10 | Mobile shell (Expo) consuming same API | Todo | |

### Next 5 to execute (ordered)

1. **P8-01** (remainder) — Case detail view / “open in chat” from saved `result` JSON; optional org scope.
2. **P6-01** (remainder) — Expand golden rows as new routing edges appear; optional legal verifier in CI.
3. **P5-01** (remainder) — Deeper Hindi / hi-Latn for `LegalChat` and minor labels.
4. **Ops** — Runbooks: prod `REDIS_URL`, `CASES_DB_PATH`, backups for SQLite dashboard DB.
5. **P10-01** — Mobile shell (Expo) consuming the same API.

*Recently completed: **P8-01** (case APIs + FE list/create/delete), **P6-01** (extra golden rows + weekly workflow), **P5-01** (`authority.status` + dashboard errors), **Redis rate-limit** (`REDIS_URL` + `test_usage_limit_redis.py`). Prior: **P7-03**, **Postgres entitlements**, **P2-03**, **P3-03**.*

---

## How to run the “proof” test suite (backend)

From `backend/`:

```bash
python -m pytest tests/ -q
```

To scope to routing/safety (fast gate, **NS-S1-05**):

```bash
./backend/scripts/run_routing_safety_tests.sh
```

---

## Project manager mode (how this works with AI)

- **Reality:** One assistant session does **not** run 24/7 with separate “worker” processes. What works well is: **PM script** (this doc) + you say *“continue **NS-S2-01** (BE role)”* and the model **implements + tests + updates the table** in the same turn.
- **Delegate:** Use **one ID per message** for clean handoffs. If you need a **`.env` key** (OpenAI, Stripe, Tavily), the model will list **name + where it is read**; you add it and reply *“keys set”*.
- **Definition of “fully functional” for the whole product:** Shipped by completing **S1→S6** (and your GTM), not a single chat. Track **Sprint %** and **Program %** below.

### Current snapshot (update when sprints move)

| Scope | Progress | Notes |
|--------|----------|--------|
| **Sprint S1** (6 items) | **~100%** (6/6) | `generate_schemas` + `generate_mappers` + thin `generate.py` |
| **Sprints S1–S6** (21 queue rows) | **~100%** (21/21) | NS + RISK queue items done; optional deeper authority file moves are follow-up |
| **End-to-end product** (phases 0–10) | **~66%** | **Next:** P8 detail view, P10 mobile, P5 depth |

*Last PM pass: **P8-01** case persistence + UI, **P6-01** golden+weekly CI, **P5-01** status i18n, **Redis** shared counters + `GET /config` `rate_limit_backend`.*

---

## Suggested next edits to this file

1. Set **Owner** and **ETA** per phase.
2. Replace **~%** with your own scoring rules (optional).
3. Add a row under **Blockers** when a phase is waiting on a dependency (e.g. payment provider, OCR vendor).

---

## One-line rollup (for standups / decks)

- **Core web (Phases 0–6, code in repo):** on the order of **~60–70%** of a “complete” Phase 0–6 slice (upload + billing + i18n; RAG metrics next).
- **Full roadmap (Phases 0–10 + GTM):** on the order of **~35–45%** if phases are **equal-weighted**; higher if you weight 0–6 more heavily (recommended).

When you change the codebase, bump **Evidence** and re-run the relevant tests so this doc stays defensible.

---

## How to use this with AI / engineers (one task at a time)

1. **Pick a row** in [Sprint work queue](#sprint-work-queue-pick-in-order) by **ID** (e.g. `NS-S1-01`).
2. In chat, say: *“Work item **NS-S1-01**; act as **primary role**; read `docs/ROADMAP_TRACKER.md` for scope.”*
3. When the item is **Done**, set **Status** to `Done` and add a one-line **PR / commit** note in the Notes column.
4. **Refactor** items: only do them in the same sprint as tests + smoke checks; if risk is high, split into a follow-up ID.

**Role tags**

| Tag | When to use | Typical output |
|-----|-------------|----------------|
| **BE** | Senior backend | API, services, types, performance, `pytest` |
| **FE** | Senior frontend | Next.js, `api.ts` mapping, UX, a11y |
| **AI** | Senior AI / ML engineer | RAG, prompts, classification, eval harness |
| **DO** | Senior DevOps | Docker, CI, env, deploy, observability |
| **TE** | Senior test / QA | Tests, golden sets, load/smoke, bug repro |

If an item has two roles, do **primary first**, then hand off.

---

## Sprint plan (suggested: 2 weeks each)

Adjust dates in your own copy. Order balances **value**, **refactor risk**, and **test safety**.

| Sprint | Theme | Outcomes (definition of done) | Primary roles |
|--------|--------|----------------------------------|---------------|
| **S1** | **Stabilize & trust** | Authority mismatch log triaged to tests or fixes; clarifier/routing regression suite green; `ai_service` / `generate` entrypoints documented; optional thin refactors (see queue) | BE, TE, AI |
| **S2** | **MVP+ upload** | `POST` upload (PDF/image) → text extract → same generate pipeline; FE file picker + errors | BE, FE, AI |
| **S3** | **Productize usage** | “Queries left” UI; server returns remaining/limits; paywall *stub* or Stripe test mode; Clerk tier field if needed | FE, BE, DO |
| **S4** | **i18n v1** | `en` / `hi` (or `hi-Latn`) for UI strings + one response-language toggle to backend; no full legal translation scope in v1 | FE, BE, AI |
| **S5** | **RAG & observability** | RAG quality metrics, logging for retrieval; optional chunk-ingestion doc; *optional* vector DB PoC behind flag | AI, DO, BE |
| **S6** | **Ship path** | Dockerfile + compose; health check; CORS/prod env checklist; basic CI (lint + pytest + fe build) | DO, BE, TE |

Later: **S7** PWA/offline lite; **S8** mobile shell (Expo).

---

## Sprint work queue (pick in order)

**Status:** `Todo` | `InProgress` | `Done` | `Blocked`  
**Refactor?** `Y` only when the task is explicitly about consolidate/delete/rename (expect extra test time).

| ID | Spr | Task | Refactor? | Primary | Status | Dependencies | Key files / notes |
|----|-----|------|----------|---------|--------|-------------|-------------------|
| NS-S1-01 | S1 | Triage `authority_mismatch.json`: convert top repeats into `pytest` cases or classifier/router fixes | N | BE / AI | **Done** | | Added `test_strict_gate_rejects_labour_for_criminal_police`; log reset `[]` + `app/logs/README.md` |
| NS-S1-02 | S1 | Map **clarification** modules: one short `CLARIFICATION.md` in `backend/docs/` (who calls whom) *or* a module docstring index | Y | BE | **Done** | | `backend/docs/CLARIFICATION.md` |
| NS-S1-03 | S1 | `trust_engine`: keep single source of truth — `app/trust/trust_engine.py` vs `services/trust_engine.py` re-export; document; avoid duplicate edits | Y | BE | **Done** | | Docstring in `app/services/trust_engine.py` (canonical: `app.trust.trust_engine`) |
| NS-S1-04 | S1 | Jurisdiction: audit overlap `jurisdiction_graph.py` vs `legal_jurisdiction_graph.py` — document or merge safe layers | Y | BE / AI | **Done** | | `backend/docs/JURISDICTION.md` (shim = re-export, not second graph) |
| NS-S1-05 | S1 | Add `pytest` marker / script to run “routing + safety” suite in CI (fast gate) | N | TE / DO | **Done** | | `backend/pytest.ini` (`routing` marker), `backend/scripts/run_routing_safety_tests.sh` |
| NS-S1-06 | S1 | Split or section `api/v1/generate.py` if >700 lines: extract response mappers to `app/api/v1/generate_mappers.py` (no API shape change) | Y | BE | **Done** | | `generate_schemas.py` + `generate_mappers.py`; `generate.py` = routes only |
| NS-S2-01 | S2 | Backend: multipart upload endpoint; file size cap; extract text → client pastes as `user_input` | N | BE | **Done** | | `POST /ingest-document`, `document_ingest.py` (pypdf + .txt); not `text_extract` (emails/phones) |
| NS-S2-02 | S2 | Frontend: upload control + error states; pipe to new endpoint then existing stream | N | FE | **Done** | NS-S2-01 | `ingestDocument` + “Attach .pdf / .txt” in `LegalChat` |
| NS-S2-03 | S2 | E2E happy path: sample PDF in `tests/fixtures/`, one integration test (optional) | N | TE | **Done** | | `test_document_ingest.test_extract_pdf_path_with_stub_pages` (pypdf stubbed) |
| NS-S3-01 | S3 | Expose `X-RateLimit-*` or JSON body: `usage: { used, limit, reset }` on 200 + 429 | N | BE | **Done** | | `consume_request` + `usage` in JSON + `http_rate_limit_headers` |
| NS-S3-02 | S3 | UI: show remaining calls; handle 429 copy | N | FE | **Done** | NS-S3-01 | `result.usage` banner, attach note; 429 still uses `onError` |
| NS-S3-03 | S3 | Plan stub: env `BILLING_MODE=none|stub|stripe` + feature flag (no real money until configured) | N | BE / FE | **Done** | | `GET /config`, `app/config.py` `billing_mode`, `page.tsx` paywall; `BILLING_MODE=stub` in API `.env` |
| NS-S4-01 | S4 | i18n: `next-intl` or simple dictionary for UI strings (pick one) | N | FE | **Done** | | `frontend/lib/i18n.ts`, `page.tsx`, `LegalChat.tsx`, `localStorage` + locale toggle |
| NS-S4-02 | S4 | API: `Accept-Language` or `user_locale` in payload; prompt wrapper for one extra language in responses | N | BE / AI | **Done** | | `GenerateRequest.response_language`, `Accept-Language` fallback, `_formatter_language_addon` in `ai_service.py` + Hindi emergency copy |
| NS-S5-01 | S5 | Log RAG: query hash, top-k scores, `grounding_label` (PII-safe) | N | AI / DO | **Done** | | `app/ai/rag_pipeline.py` — `logger.info` + JSON; `test_rag_pipeline_observability.py` |
| NS-S5-02 | S5 | **Optional** Pinecone/FAISS: feature-flagged adapter; same interface as `load_knowledge_entries` | Y | AI / BE | **Done** | | `RAG_VECTOR_STORE` + `pinecone_legal_index` + `app/rag/pinecone_ingest.py` (ingest) |
| NS-S6-01 | S6 | `Dockerfile` + `docker-compose` for `frontend` + `backend` (dev) | N | DO | **Done** | | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| NS-S6-02 | S6 | CI: GitHub Actions — `pytest`, `ruff`/`ruff` optional, `npx tsc --noEmit`, `npm run build` | N | DO / TE | **Done** | | `.github/workflows/ci.yml` |
| NS-S6-03 | S6 | `/health` and `/ready` with dependency checks (OpenAI key optional) | N | DO / BE | **Done** | | `GET /ready`: `openai_configured`, `openai_model`, `rag_vector_store`, `pinecone_configured` (non-secret); `test_ready_endpoint.py` |
| RISK-01 | any | “Authority” folder: after S1, consider `app/authority/` package bundling `authority_*.py` (large move — own sprint) | Y | BE | **Done** | NS-S1-01 done | **Batches 1–2:** `app/authority` re-exports schema + `authority_intent_resolver` + `get_default_authority_provider`. Plan: `backend/docs/AUTHORITY_PACKAGE_PLAN.md` |
| RISK-02 | any | Evaluate merging `ai/evaluator.py`, `ai/output_evaluator.py`, `evaluators/legal_verifier` boundaries — documentation first | Y | AI | **Done** | | `backend/docs/EVALUATORS.md` (layer map + merge guidance; no merge) |

---

## Refactor rules (so cleanup does not break prod)

- **No drive-by** refactors mixed with product features: separate PRs when possible.
- **Rename/move files:** do one directory at a time; `rg` for imports; run full `pytest`.
- **Delete files:** only after `rg` shows no imports and tests pass; keep git history.
- **Large files (`ai_service.py` etc.):** prefer **extract** helpers to new files over inline churn.

---

## When you finish a work item (template for PR description)

- **ID:** `NS-…`  
- **What changed** (1–2 sentences)  
- **Risks** and **How tested** (commands)  
- **Follow-ups** (next ID if any)
