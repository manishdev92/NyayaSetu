# Postgres entitlements (multi-instance)

When the API runs **more than one process** (or serverless workers), SQLite on local disk is not shared. Set **`ENTITLEMENTS_DATABASE_URL`** to a **PostgreSQL** connection string to persist Stripe → Clerk subscription rows in Postgres instead of SQLite.

## Environment

| Variable | When | Notes |
|----------|------|--------|
| `ENTITLEMENTS_DATABASE_URL` | Optional | e.g. `postgresql://user:pass@host:5432/dbname?sslmode=require`. When **non-empty**, the API uses Postgres for `clerk_entitlements`. |
| `ENTITLEMENTS_DB_PATH` | SQLite only | Ignored for entitlement **reads/writes** once `ENTITLEMENTS_DATABASE_URL` is set. |

`GET /config` exposes **`entitlements_store`**: `"sqlite"` or `"postgres"` (non-secret).

## Schema

The API creates this table on first connect (same columns as SQLite):

```sql
CREATE TABLE IF NOT EXISTS clerk_entitlements (
    clerk_user_id TEXT PRIMARY KEY,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL,
    current_period_end INTEGER,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_clerk_entitlements_subscription
ON clerk_entitlements (stripe_subscription_id)
WHERE stripe_subscription_id IS NOT NULL AND stripe_subscription_id <> '';
```

## Dependencies

Install **`psycopg2-binary`** (already listed in `backend/requirements.txt`).

## Operations

- Run **migrations** manually if you manage schema outside the app (align DDL with the snippet above).
- Prefer a **managed Postgres** (RDS, Cloud SQL, etc.) with backups and TLS.
- Webhook endpoint must hit **one** logical writer or use idempotent upserts only (current upserts are safe for duplicate delivery).
