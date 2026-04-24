# P8-01 — Lawyer / org dashboard (product sketch)

## Goal

A **signed-in** area for lawyers or small firms to **reuse the same NyayaSetu API** as the public chat: saved cases, client labels, export of drafts, and (later) org billing. This doc is the minimum product frame before building data models.

## MVP (suggested order)

1. **Auth** — Clerk only; same `X-User-Id` as today for usage and Stripe entitlements.
2. **Case list** — Client-side or server-stored rows: `{ id, title, updated_at, last_response_summary }` with deep link to a detail view that reuses generate/ingest APIs.
3. **Detail** — Read-only replay of last `GenerateResponse` JSON (or link “Open in main chat” with pre-filled context).
4. **Org (later)** — Clerk Organizations; map `org_id` → shared seat count / Stripe customer.

## Non-goals (initial scaffold)

- No custom Postgres schema in this repo slice beyond optional entitlements (see `ENTITLEMENTS_POSTGRES.md`).
- No replacement for India-specific legal disclaimers; dashboard copy stays **educational / not legal advice**.

## Scaffold in repo

- Route: **`/dashboard`** (`frontend/app/dashboard/page.tsx`) — Clerk-gated UI: list, create, delete saved cases.
- API (same `X-User-Id` as billing/usage): **`GET /dashboard/cases`**, **`POST /dashboard/cases`**, **`DELETE /dashboard/cases/{id}`** — `backend/app/api/v1/dashboard_cases.py`, SQLite store `backend/app/services/dashboard_cases_store.py`, env **`CASES_DB_PATH`** (see `backend/.env.example`).
