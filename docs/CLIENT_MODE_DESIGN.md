# Client mode — citizen vs lawyer (P0-3)

**Purpose:** Stable **extension point** for tiered behaviour (retrieval depth, prompts, UI) without breaking existing clients. **Trust is not implied:** `client_mode=lawyer` is **not** authentication; later tie to **Clerk roles** or **billing SKU** (see Sprint 1 / P1-4).

**Related:** `docs/USER_PERSONAS.md` · `docs/SPRINTS_PRIORITIZED.md`

---

## Canonical values

| Value | Meaning |
|--------|---------|
| `citizen` | Default; lighter product expectations (see personas doc). |
| `lawyer` | Legal professional / power-user path; same safety gates; deeper knobs in later sprints. |

---

## Where the client sends it

### 1. JSON body (preferred)

```json
{
  "user_input": "…",
  "client_mode": "lawyer"
}
```

- **Omit** `client_mode` → same as `citizen` unless header (below) is set.
- Invalid body value → **422** validation error (Pydantic).

### 2. Optional header `X-Client-Mode`

- Values: `citizen` or `lawyer` (case-insensitive). Aliases accepted: `legal_professional`, `pro` → **lawyer**; `public`, `general` → **citizen**.
- Invalid non-empty value → **422** with `error_code`: `invalid_client_mode`.

### Precedence

**Body wins.** If `client_mode` is present in JSON (`citizen` or `lawyer`), the header is ignored. If body omits the field (or sends `null`), `X-Client-Mode` is used. If both omit, **`citizen`**.

---

## API response echo

`POST /generate` response includes **`client_mode`** so clients can confirm what the server applied (useful for debugging and for proxies that strip headers).

SSE `type: "result"` payloads from `POST /generate-stream` include **`client_mode`** on clarification-only and full-result paths.

### Discovery (P1-3)

- **`GET /config`** and **`GET /ready`** include **`client_modes_supported`**: a JSON array of mode strings the deployment **advertises** for UI (e.g. whether to show a lawyer toggle).
- Ops: set **`CLIENT_MODES_SUPPORTED`** on the API to a comma-separated subset of `citizen` and `lawyer` (default `citizen,lawyer`). If the list includes **`lawyer`**, the API returns **`["citizen","lawyer"]`** in fixed order. **`citizen`** alone returns **`["citizen"]`** (hide lawyer entry point in UI).

---

## Backend wiring (current)

| Location | Behaviour |
|----------|-----------|
| `GenerateRequest.client_mode` | Optional `citizen` \| `lawyer`. |
| `GenerateResponse.client_mode` | Always set to resolved value. |
| `generate_legal_response(..., client_mode=...)` | Echoed on response; drives **strict RAG** `top_k` (P1-2). |

### RAG `top_k` by mode (P1-2)

- **`run_strict_rag_pipeline`** receives `top_k` from **`_rag_top_k_for_client_mode`** in `app/services/ai_service.py`.
- **Settings** (env): `RAG_TOP_K_CITIZEN` (default **8**), `RAG_TOP_K_LAWYER` (default **12**); each clamped to **3–24** in `app/config.py`.
- **Crisis path** skips normal RAG; `client_mode` does not apply there.

---

## Security note (product + engineering)

Until **auth-bound** tiers exist, **`client_mode` is self-declared**. Do not expose paid-only features solely on this flag; gate with **Clerk + entitlements** when lawyer SKU ships.

**P1-1 (optional):** Set **`LAWYER_CLIENT_MODE_REQUIRES_USER_ID=true`** so **`POST /generate`** and **`POST /generate-stream`** return **403** with **`error_code`: `lawyer_mode_requires_sign_in`** when **`client_mode`** resolves to **`lawyer`** but **`X-User-Id`** is empty. **`GET /config`** includes **`lawyer_mode_requires_sign_in`** for the UI. This only checks that a user id was sent (e.g. Clerk in the browser), not JWT verification on the API.

**P1-1 (Pro, Stripe):** Set **`LAWYER_CLIENT_MODE_REQUIRES_PRO=true`** with **`BILLING_MODE=stripe`**. The API enforces an **active Pro** row (Stripe webhook → entitlements DB) for **`client_mode=lawyer`**; **403** with **`error_code`: `lawyer_mode_requires_pro`** otherwise. **`GET /config`** and **`GET /ready`** include **`lawyer_mode_requires_pro`**, **`lawyer_pro_gate_active`** (true only when this flag and Stripe are both on), and the chat uses **`GET /billing/entitlements`** to allow the lawyer control for Pro users.

---

## Frontend (P1-4)

- When **`NEXT_PUBLIC_LAWYER_MODE_UI`** is `1` / `true` / `yes` at **build** time **and** `GET /config` → **`client_modes_supported`** includes **`lawyer`**, the chat shows a **General user** vs **Lawyer / legal professional** control. Choice is stored in **`localStorage`** (`nyaya-client-mode`) and sent as **`client_mode`** on each generate stream request.
- If **`lawyer_mode_requires_sign_in`** is **true**, the lawyer control is disabled until the user is signed in (so **`X-User-Id`** is sent).
- If **`lawyer_pro_gate_active`** is **true**, the lawyer control is disabled until **`GET /billing/entitlements`** returns **`pro: true`**.
- If the flag is off or the API does not list `lawyer`, the toggle is hidden and the API default (**citizen**) applies.
