# Stripe Checkout + Pro entitlements (P2-01 / P2-02)

NyayaSetu can open **Stripe Checkout** for a subscription when `BILLING_MODE=stripe` and the secrets below are set. **P2-02** persists subscription state from webhooks into **SQLite** (default `var/entitlements.sqlite` under the API working directory, or `ENTITLEMENTS_DB_PATH`), maps **Clerk** `client_reference_id` / subscription metadata, raises **`DAILY_LIMIT_PRO`** for active/trialing subscribers, and exposes **`GET /billing/entitlements`** for the UI.

## Environment variables

| Variable | Required for Checkout | Notes |
|----------|-------------------------|--------|
| `BILLING_MODE` | Yes | Must be `stripe` (not `stub` / `none`). |
| `STRIPE_SECRET_KEY` | Yes | `sk_test_…` or `sk_live_…`. |
| `STRIPE_PRICE_ID` | Yes | Recurring **Price** id (e.g. `price_…`) attached to a Product. |
| `PUBLIC_APP_URL` | Recommended | Origin for success/cancel redirects (default `http://localhost:3000`). No trailing slash stored. |
| `STRIPE_WEBHOOK_SECRET` | For webhooks only | `whsec_…` from Stripe CLI or Dashboard endpoint. Without it, `POST /billing/stripe-webhook` returns **503**. |
| `DAILY_LIMIT_PRO` | No | Default **500** — daily generate/ingest cap for users with `active` or `trialing` subscription in the entitlements DB. |
| `ENTITLEMENTS_DB_PATH` | No | SQLite path; default `var/entitlements.sqlite`. Use `:memory:` only for tests. |

`GET /config` exposes **`stripe_checkout_ready`**, **`stripe_portal_ready`**, **`stripe_webhook_ready`**, and **`entitlements_store`** (`sqlite` \| `postgres`, non-secret). `GET /ready` includes **`stripe_checkout_ready`** and **`stripe_portal_ready`**. Multi-instance entitlements: see **`ENTITLEMENTS_POSTGRES.md`** when using **`ENTITLEMENTS_DATABASE_URL`**.

## Stripe Dashboard (test mode)

1. **Product** — e.g. “NyayaSetu Pro” with recurring price (monthly/yearly as you prefer).  
2. Copy **Price id** → `STRIPE_PRICE_ID`.  
3. **Developers → API keys** → secret key → `STRIPE_SECRET_KEY`.  
4. **Developers → Webhooks** — add endpoint `https://<your-api-host>/billing/stripe-webhook`, select at minimum **`checkout.session.completed`**, **`customer.subscription.updated`**, **`customer.subscription.deleted`**. Copy **signing secret** → `STRIPE_WEBHOOK_SECRET`.  
5. Local tunnel: `stripe listen --forward-to localhost:8000/billing/stripe-webhook`.

## API

- **`POST /billing/create-checkout-session`**  
  - Headers: optional **`X-User-Id`** (Clerk user id) → `client_reference_id` + `metadata.clerk_user_id`.  
  - Response: `{ "checkout_url": "https://checkout.stripe.com/..." }`.

- **`POST /billing/create-portal-session`** (P2-03 — Customer Portal)  
  - Headers: **`X-User-Id`** (required) — resolves `stripe_customer_id` from the entitlements row.  
  - Response: `{ "portal_url": "https://billing.stripe.com/..." }`.  
  - Configure the **Customer portal** in Stripe Dashboard (test/live) so customers can manage/cancel the subscription.  
  - Errors: **`stripe_portal_not_configured`** (503, no secret), **`billing_portal_user_required`** (400, no header), **`stripe_customer_missing`** (404, checkout/webhook not synced yet).

- **`POST /billing/stripe-webhook`**  
  - Raw body + **`Stripe-Signature`**. Returns `{ "received": true }` on success. Updates the entitlements store from supported events.

- **`GET /billing/entitlements`**  
  - Header: **`X-User-Id`** (Clerk id). Response: `{ "pro": bool, "subscription_status": string | null, "daily_limit": number }`. When `BILLING_MODE` is not `stripe`, `pro` is always `false`.

## Frontend

With `stripe_checkout_ready` and `billing_mode === "stripe"`, the home paywall shows **Upgrade with Stripe** until **`GET /billing/entitlements`** reports `pro: true`, then a **Pro active** panel is shown. When **`stripe_portal_ready`** is true, **Manage billing** calls **`POST /billing/create-portal-session`** (requires sign-in). User should be **signed in** so `X-User-Id` is sent on checkout, portal, and entitlement checks.

## CORS

Ensure `CORS_ORIGINS` includes your Next.js origin so the browser can call the billing API.
