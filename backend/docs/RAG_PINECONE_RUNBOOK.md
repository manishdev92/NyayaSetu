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
| `PINECONE_QUERY_CANDIDATES` | Pre–issue-filter fetch (citizen tier; default 48) |
| `PINECONE_QUERY_CANDIDATES_LAWYER` | Optional; larger fetch for `client_mode=lawyer` (8–200). If unset, uses `min(200, PINECONE_QUERY_CANDIDATES+24).` |
| `RAG_TOP_K_DEFAULT` | Alias for `RAG_TOP_K_CITIZEN` (strict RAG `top_k` for citizen) |
| `RAG_TOP_K_CITIZEN` / `RAG_TOP_K_LAWYER` | Strict RAG `top_k` by tier (3–24) |

`GET /ready` includes `rag_vector_store` and `pinecone_configured` (key + index name, non-secret).

## 3. Ingest (upsert)

**Primary path (recommended): GitHub Actions** — no local keys on laptops; use **Repository secrets** and run workflows manually after merging changes to the KB.

| Workflow | When | Repo secrets (minimum) |
|----------|------|------------------------|
| [`pinecone-kb-ingest.yml`](../../.github/workflows/pinecone-kb-ingest.yml) | Push curated `knowledge_seed.json` to `main`, then refresh Pinecone with that commit. | **Secrets:** `OPENAI_API_KEY`, `PINECONE_API_KEY` (must be under *Secrets*, not *Variables*). `PINECONE_INDEX` = Secret **or** **Variable** (same name). Optional `PINECONE_NAMESPACE` (Secret or Variable). |
| [`pinecone-statute-s3-ingest.yml`](../../.github/workflows/pinecone-statute-s3-ingest.yml) | Ingest `*.md` from **S3** (licensed drops under a **prefix**). | Same three Pinecone/OpenAI · plus `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` with `s3:ListBucket` + `s3:GetObject` on the prefix · optional `S3_STATUTES_URI` or type **s3_uri** in the workflow form · optional Variable `AWS_DEFAULT_REGION` (default `ap-south-1`) |

Steps: **Actions** → pick the workflow → **Run workflow** (branch = usually `main`). For S3, leave **dry_run** true on the first run, confirm the JSON summary, then run again with **dry_run** false to upsert.

To require a **human approval** before production upserts, add to the `ingest` job in the YAML: `environment: your-env-name` and create that [Environment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment) with required reviewers.

**Local CLI (alternative):** from the `backend/` directory with a venv:

```bash
export OPENAI_API_KEY=sk-... PINECONE_API_KEY=... PINECONE_INDEX=nyaya-legal-kb
python -m app.rag.pinecone_ingest
```

This calls `upsert_curated_knowledge_from_file` in `app/rag/pinecone_legal_index.py` using the same curated source as the local RAG path.

### 3b. Statute Markdown drop (Sprint P4)

Licensed **`.md`** with YAML frontmatter (`act_id`, `source_url`, `source_version`, …) is chunked and upserted. **Prefer the S3 GitHub Action** (table above) once files are in S3. **Local CLI** options:

```bash
python -m app.rag.jobs.ingest_statutes --path /path/to/act_folder --dry-run
python -m app.rag.jobs.ingest_statutes --path /path/to/act_folder
```

**S3 (same code path as Actions):** **Do not** use `s3://bucket` with an empty prefix; use a dedicated prefix, e.g. `s3://my-bucket/ingest/v1/`.

```bash
export AWS_DEFAULT_REGION=ap-south-1
export OPENAI_API_KEY=... PINECONE_API_KEY=... PINECONE_INDEX=...
python -m app.rag.jobs.ingest_statutes --s3-uri s3://my-bucket/ingest/v1/ --dry-run
python -m app.rag.jobs.ingest_statutes --s3-uri s3://my-bucket/ingest/v1/
```

**Terraform (optional):** set `ingest_corpus_bucket_name` in `infra/terraform/nyayasetu` to create a private versioned bucket (output `ingest_corpus_bucket`). Create an IAM user, least-privilege policy for that prefix, and add keys to **GitHub secrets** for the workflow.

See `docs/CORPUS_V1_BOUNDARY.md` and `tests/fixtures/ingest_statutes/sample_act.md` for shape. Metadata includes `ingested_at`, `content_sha256`, `act_id`, `source_version` for re-ingest tracking.

## 4. Rollout

1. Create index → run ingest in staging → set `RAG_VECTOR_STORE=pinecone` on one environment → run routing/RAG tests (`test_pinecone_rag.py`, `test_rag_pipeline_observability.py`) → monitor logs for PII-safe retrieval lines.  
2. Roll back by switching `RAG_VECTOR_STORE=local` (no code deploy if only env changes).

## 5. AWS (App Runner) — who sets the env

**GitHub `Deploy AWS` workflow** (`.github/workflows/deploy-aws.yml`) only **builds and pushes** ECR images. It does **not** apply Terraform, so it does **not** change `RAG_VECTOR_STORE` / `PINECONE_*` on the running API.

**Where prod/staging API env comes from:** `infra/terraform/nyayasetu/apprunner.tf` — App Runner `runtime_environment_variables` for the API service.

- **Set once (or when rotating keys):** run Terraform with `TF_VAR_` (or `-var=…`) and apply so App Runner picks up the new values:
  - `TF_VAR_rag_vector_store=pinecone`
  - `TF_VAR_pinecone_api_key=…` (sensitive; never commit to git)
  - `TF_VAR_pinecone_index=…` (must match the index you created; default in Terraform is `nyaya-legal-kb`)
  - `TF_VAR_pinecone_namespace=…` (optional; use `""` for default namespace)
- **Convenience:** `scripts/deploy-aws.sh` can **read** `RAG_VECTOR_STORE` / `PINECONE_*` from a local `backend/.env` (if you did not already export the matching `TF_VAR_*`), then apply Terraform. Override anytime by exporting `TF_VAR_*` in your shell.
- **After** env changes, App Runner may need a new deployment. Pushing a new `nyayasetu-api` image to ECR usually triggers that when auto-deploy is enabled; otherwise use the App Runner console **Deploy** (or a deployment API call).

## 6. See also

- Ingest entrypoint: `app/rag/pinecone_ingest.py`  
- Query path: `app/rag/pinecone_legal_index.py`  
- `docs/ROADMAP_TRACKER.md` Phase 4 row
