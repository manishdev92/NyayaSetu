# v1 corpus boundary — automated ingest and RAG sources (P0-2)

**Purpose:** Lock **engineering scope** for what may enter the **automated** download → chunk → embed → Pinecone (or successor) pipeline in **v1**, so work never defaults to “scrape the whole web.” **Legal/compliance** still must **sign off** on the final allow-list and any publisher agreements; this document is the **product + engineering** contract until that sign-off lands.

**Related:** `backend/app/rag/legal_store/policy.py` (`is_allowed_legal_source_url`) · `backend/docs/RAG_PINECONE_RUNBOOK.md` · `docs/USER_PERSONAS.md` · `docs/SPRINTS_PRIORITIZED.md`

---

## Current production baseline (no change required to ship)

| Source | Role today |
|--------|------------|
| **`backend/app/rag/legal_knowledge_base/knowledge_seed.json`** | Sole curated KB for strict RAG; entries are **human-curated**, `verified=true`, with `source_url`. |
| **Pinecone** | Same **logical** corpus as the JSON file after **`python -m app.rag.pinecone_ingest`**; not a separate wild corpus. |
| **Statute Markdown ingest (P4)** | Optional **`python -m app.rag.jobs.ingest_statutes --path …`** on **local** `.md` with frontmatter (`act_id`, `source_url`, `source_version`, …); see `backend/docs/RAG_PINECONE_RUNBOOK.md` §3b. |

v1 **does not** require bulk statute ingest to ship; it defines **what is allowed to start building** ingest jobs (Sprint 4).

---

## Alignment with “official URL” policy (code)

Highest-trust **verified** RAG chunks in code are gated toward **India official** patterns: see `ALLOWED_LEGAL_HOST_SUFFIXES` and `FORBIDDEN_HOST_HINTS` in `backend/app/rag/legal_store/policy.py` (e.g. `indiacode.nic.in`, `*.gov.in`, `ecourts.gov.in`; excludes Wikipedia, generic blogs).

**v1 rule:** Any **new** automated ingest whose output is labeled **official / verified** in-product must use **sources that satisfy** (or a **stricter** superset approved by compliance) that URL policy, plus **version metadata** (see below).

---

## Tier A — In scope for v1 **automated** ingest (engineering may build pipelines)

All of the following require **recorded** `source_url`, `fetched_at`, and **content hash** per chunk in metadata.

| Category | Boundary | Notes |
|----------|----------|--------|
| **Central bare Acts** | Text published on **India Code** (`indiacode.nic.in`) or other URLs that pass `is_allowed_legal_source_url` | **Which** Acts are in v1 is a **product + legal** checklist (see **ASK** below); engineering does not decide statute list alone. |
| **Constitution of India** | Same: official publication path only | Large; chunk by Part / Article in Sprint 4 design. |
| **Central rules / subordinate legislation** | Only if same official host policy and clearly versioned | Lower priority than parent Act unless product says otherwise. |

**Out of Tier A until explicitly approved:** state Acts (50+ jurisdictions), bilingual gazette scraping at scale, **commentaries / textbooks** (usually publisher copyright).

---

## Tier B — Allowed only with **explicit license or contract**

| Category | Boundary |
|----------|----------|
| **Law publisher PDFs** (commentaries, digests) | Written license + permitted use (ingest, derivative index, display). |
| **Commercial case-law APIs** (e.g. SCC, Manupatra-style) | API terms + key management; no scraping behind paywall. |
| **Chamber / firm private precedents** | Customer-owned data path; separate namespace; not part of NyayaSetu default corpus. |

Tier B is **not** v1 “automated open web ingest”; it is **integrations**.

---

## Tier C — Out of scope for **automated** v1 ingest (do not build scrapers for these)

| Category | Reason |
|----------|--------|
| **General web search / arbitrary blogs / forums / Quora / social** | Unreliable, unclear copyright, harms trust. |
| **Wikipedia** | Explicitly discouraged in `FORBIDDEN_HOST_HINTS` for official-trust path. |
| **Paywalled or ToS-prohibited sites** | Legal and operational risk. |
| **“Download every book lawyers cite”** | Not a bounded or licensable v1 goal; use Tier B instead. |

Ad-hoc **LLM browsing** to copy full works into Pinecone is **Tier C** unless narrowed to **Tier A** allow-list fetchers with compliance review.

---

## Human-curated path (always allowed)

Adding or editing rows in **`knowledge_seed.json`** (with valid `source_url` and review) remains valid **without** automated ingest. This is the **fallback** when a statute is not yet in the automated pipeline.

---

## Versioning and amendments (required metadata for any automated chunk)

Minimum metadata for each ingested chunk (v1 target):

- `source_url`, `act_short_title` (or equivalent), `section_or_article_label`
- `source_fetched_at` (ISO date)
- `content_sha256` (or similar) for dedupe and re-ingest detection
- Optional: `india_code_last_seen` if the portal exposes a revision indicator

Re-ingest policy: **on demand** per release or when legal flags an amendment; no promise of same-day gazette sync in v1.

---

## ASK — legal / product (fill before expanding production corpus)

1. **Enumerated list of Acts** (and optionally rules) approved for **v1** automated ingest from **India Code** only.  
2. **Whether state statutes** appear in v1.0 or v1.1.  
3. **Whether any Tier B** vendor is approved for budget and timeline.  
4. **Disclaimer text** for “automated statutory text may lag gazette” (exact wording for UI).

Until (1) is answered, engineering should implement **pipeline scaffolding** with **one pilot Act** chosen by stakeholders (placeholder: product picks **one** central Act for dev/staging only). A **non-binding engineering pilot** list is in **`docs/CORPUS_V1_PILOT.md`**.

---

## Sprint table update

When (1)–(4) are answered, append a short **“Approved v1 corpus — YYYY-MM-DD”** subsection here or in a linked `CORPUS_V1_APPROVED.md` owned by compliance.
