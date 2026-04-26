# Case law and external research (Sprint 6) — design note

**Scope:** P6 is **separate** from the statute / Pinecone RAG path. It covers **licensed** case-law or judgment search (vendors, APIs, or org-licensed indices), not scraping public sites in production.

## Principles

- **No scraping in-app:** Production adapters must use explicit APIs or data products your organization is licensed to call.
- **Pluggable backend:** `app/research/case_law/adapter.CaseLawSource` defines `search(query, *, limit) -> list[CaseLawSnippet]`. The default is `NoopCaseLawSource` (empty).
- **Toggle:** `CASE_LAW_MODE=off` (default) hides the feature from API shape except empty lists; `CASE_LAW_MODE=noop` exposes the lawyer path with empty results; `CASE_LAW_MODE=tavily_preview` enables preview research snippets using `TAVILY_API_KEY` (non-authoritative external snippets).
- **UI:** `NEXT_PUBLIC_CASE_LAW_UI=1` and `case_law_research_mode` ≠ `off` on `GET /config` — show the **Case law (research)** panel for **lawyer** `client_mode` (optional empty state with compliance copy).

## Product / legal ASK (before a vendor implementation)

- Budget and preferred **licensed** provider.
- Citation and snippet length rules for the panel.
- Whether case-law output may feed prompts or is **display-only** (transparency default: display-only).

## Next implementation steps (when a vendor is chosen)

1. Add a new class implementing `CaseLawSource` (e.g. `app/research/case_law/vendors/xyz.py`).
2. Extend `get_case_law_source()` in `app/research/case_law/factory.py` to return it when `CASE_LAW_MODE=xyz` and env secrets are set.
3. Add `PYTHON` / GitHub **secrets** for that API; never commit keys.
4. Add a focused pytest (mocked HTTP) for the adapter.
