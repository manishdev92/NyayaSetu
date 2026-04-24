# NyayaSetu — AWS deployment plan (Option A)

**Target architecture:** GitHub Actions → **Amazon ECR** → **AWS App Runner** (two services: **API** + **Web**), **IAM (OIDC)**, **CloudWatch** logs. Optional later: **Secrets Manager**, **CloudFront**, **Route 53**, **RDS / ElastiCache**.

**Repo facts:** `backend/Dockerfile` (FastAPI on port **8000**, health: **`GET /health`**), `frontend/Dockerfile` (Next.js on port **3000**; build arg **`NEXT_PUBLIC_API_URL`** must match the **public** API URL).

### Quick path (implemented in repo)

- **Full Terraform stack:** `infra/terraform/nyayasetu/` — ECR, GitHub OIDC deploy role, App Runner ECR access role, optional App Runner API + Web.
- **Bootstrap script:** `./scripts/deploy-aws.sh` from repo root (Docker + AWS CLI + Terraform).
- **CI workflow:** `.github/workflows/deploy-aws.yml` (`workflow_dispatch`); wire `AWS_ROLE_TO_ASSUME`, `NEXT_PUBLIC_API_URL`, and App Runner service ARNs as in `infra/README.md`.
- **API CORS on AWS:** Terraform sets `CORS_ALLOW_APPRUNNER_REGEX=true` so HTTPS `*.awsapprunner.com` browser origins are allowed alongside `CORS_ORIGINS` (tighten to explicit web URL later if you prefer).

Override GitHub repo for OIDC trust if needed: `TF_VAR_github_repository=owner/repo` when applying (default matches `git@github.com:manishdev92/NyayaSetu.git`).

---

## How to use this document

1. Work **phases in order** (each phase ends with a verifiable milestone).
2. Check boxes `[ ]` → `[x]` as you finish (in Git or locally).
3. Keep a short **run log** at the bottom (date, what you did, URLs) for demos and handoffs.

---

## Phase 0 — Preconditions

- [ ] **P0-1** Confirm AWS account, billing alert (e.g. Budgets), and **region** choice (e.g. `ap-south-1` or `us-east-1`).
- [ ] **P0-2** Install locally: `aws` CLI v2, `docker`, `terraform` (if using Terraform for infra).
- [ ] **P0-3** Decide **hostnames**: e.g. `api.example.com` + `app.example.com` (optional for first cut — App Runner default URLs are fine for internal demo).
- [ ] **P0-4** List **secrets** the app needs (from `backend/.env` / Stripe/OpenAI docs — **do not** commit values): e.g. `OPENAI_API_KEY`, `CORS_ORIGINS`, Stripe keys, `NEXT_PUBLIC_*`, optional `ENTITLEMENTS_DATABASE_URL`, `redis_url`.

**Milestone:** Written list of env vars for API vs Web; region chosen.

---

## Phase 1 — Amazon ECR

**Implemented in repo:** `infra/terraform/modules/ecr/` (module); wrappers **`infra/terraform/ecr/`** (ECR-only) and **`infra/terraform/nyayasetu/`** (full stack). See `infra/README.md`.

- [ ] **P1-1** Create **ECR repository** `nyayasetu-api` (private). → `./scripts/deploy-aws.sh` **or** `cd infra/terraform/ecr && terraform apply`
- [ ] **P1-2** Create **ECR repository** `nyayasetu-web` (private). → same
- [ ] **P1-3** Note **registry URI** (`terraform output`) and confirm lifecycle policy in console or CLI.

**Milestone:** `aws ecr describe-repositories` shows both repos.

---

## Phase 2 — IAM for GitHub Actions (OIDC)

**Implemented in repo:** `infra/terraform/nyayasetu/iam_github.tf` — OIDC provider (optional), role `nyayasetu-github-deploy`, ECR + App Runner deploy policy. Trust uses `repo:OWNER/REPO:*` (default `manishdev92/NyayaSetu`; override with `TF_VAR_github_repository`).

- [ ] **P2-1** OIDC provider `token.actions.githubusercontent.com` — created by Terraform unless `create_github_oidc_provider=false` (when it already exists).
- [ ] **P2-2**–**P2-3** IAM role + policy — included in `nyayasetu` apply.
- [ ] **P2-4** GitHub: **Secret** `AWS_ROLE_TO_ASSUME` = `terraform output -raw github_deploy_role_arn` (workflow name uses this secret; not `AWS_ROLE_ARN`).

**Milestone:** A test workflow can assume the role and call `sts get-caller-identity` + `ecr DescribeRepositories` without access denied.

---

## Phase 3 — IAM roles for App Runner

**Implemented in repo:** `infra/terraform/nyayasetu/iam_apprunner.tf` — role `nyayasetu-apprunner-ecr-access` + `AWSAppRunnerServicePolicyForECRAccess`. Instance role optional (not created yet).

- [ ] **P3-1**–**P3-3** Covered by `nyayasetu` apply; ARN: `terraform output apprunner_ecr_access_role_arn`.

**Milestone:** ECR access role ARN present; App Runner services can pull private images.

---

## Phase 4 — First images (local prove-out)

- [ ] **P4-1** Build API: `docker build -t nyayasetu-api:local ./backend` and run with `-p 8000:8000`; curl `http://localhost:8000/health`.
- [ ] **P4-2** Decide **production API URL** placeholder (App Runner URL until custom domain), e.g. `https://xxxx.ap-south-1.awsapprunner.com`.
- [ ] **P4-3** Build Web with correct API URL at **build time**:  
  `docker build --build-arg NEXT_PUBLIC_API_URL=https://<your-api-apprunner-url> -t nyayasetu-web:local ./frontend`  
  Run `-p 3000:3000`; confirm browser network calls hit the API (CORS must allow the web origin — see Phase 6).

**Milestone:** Both images run locally with the **same** URLs you will use in AWS.

---

## Phase 5 — AWS App Runner services

**Implemented in repo:** `infra/terraform/nyayasetu/apprunner.tf` — services `nyayasetu-api` / `nyayasetu-web`, ports **8000** / **3000**, health **`/health`** / **`/`**, `auto_deployments_enabled=true`. Enable with `deploy_api_service` / `deploy_web_service` (script does this in order).

- [ ] **P5-1**–**P5-3** Run `./scripts/deploy-aws.sh` **or** manual apply steps in `infra/README.md`.
- [ ] **P5-4** Auto-deploy on new ECR images is **on**; GitHub workflow also calls **`StartDeployment`** after push.

**Milestone:** Public web URL loads UI; a draft/legal flow calls the API without CORS errors.

---

## Phase 6 — CORS and environment consistency

- [ ] **P6-1** Terraform sets **`CORS_ORIGINS=http://localhost:3000`** and **`CORS_ALLOW_APPRUNNER_REGEX=true`** for App Runner HTTPS hosts. Optionally tighten later to the exact web URL only.
- [ ] **P6-2** Rebuild **web** image whenever **`NEXT_PUBLIC_API_URL`** changes (Next bakes this at build time).
- [ ] **P6-3** Confirm **no** secrets in client bundle: only `NEXT_PUBLIC_*` belongs in frontend; server keys stay on API service only.

**Milestone:** Browser devtools: no blocked CORS; no leaked server keys in web chunk.

---

## Phase 7 — GitHub Actions CI/CD

- [ ] **P7-1** Workflow **`.github/workflows/deploy-aws.yml`** — `workflow_dispatch` (manual). CI for tests remains **`.github/workflows/ci.yml`**.
- [ ] **P7-2** (Optional) Extend `ci.yml` with ruff / `npm run lint` if desired.
- [ ] **P7-3**–**P7-4** Deploy job: OIDC → ECR login → build/push API → `StartDeployment` API → build/push Web with **`secrets.NEXT_PUBLIC_API_URL`** → `StartDeployment` Web.
- [ ] **P7-5** Protect **`main`**: require PR / review (optional), environment **approval** for production (strong demo narrative).

**Milestone:** Push to `main` updates running services without manual `docker push` from laptop.

---

## Phase 8 — Observability and hygiene

- [ ] **P8-1** Open **CloudWatch** log groups for both App Runner services; verify request logs on traffic.
- [ ] **P8-2** Add **metric filter / alarm** (optional): 5xx rate or unhealthy target (if using custom health).
- [ ] **P8-3** Document **rollback**: redeploy previous image tag via ECR + App Runner.

**Milestone:** You can show logs in the demo within 1 minute of a test request.

---

## Phase 9 — Custom domain (optional)

- [ ] **P9-1** **ACM** certificate in the same region as App Runner (or follow AWS docs for custom domain on App Runner).
- [ ] **P9-2** **Route 53** (or external DNS) CNAME/ALIAS to App Runner domain.
- [ ] **P9-3** Update **`CORS_ORIGINS`** and rebuild web with new **`NEXT_PUBLIC_API_URL`**.

**Milestone:** `https://app.yourdomain.com` works end-to-end.

---

## Phase 10 — Hardening backlog (post-demo)

- [ ] **P10-1** Move runtime secrets from GitHub-only to **Secrets Manager**; reference from App Runner; rotate keys.
- [ ] **P10-2** **CloudFront** in front of web (and optionally API) for CDN + TLS + future **WAF**.
- [ ] **P10-3** Add **RDS PostgreSQL** + `ENTITLEMENTS_DATABASE_URL` when you need durable entitlements (see `backend/docs/ENTITLEMENTS_POSTGRES.md`).
- [ ] **P10-4** Add **ElastiCache Redis** when you need distributed rate limits (see `backend/docs/RATE_LIMIT_REDIS.md`).
- [ ] **P10-5** **Terraform**: state in **S3** + **DynamoDB** lock; modules for ECR, IAM, App Runner.

---

## Run log (fill as you go)

| Date | Phase / task | Notes (URLs, ARNs redacted) |
|------|----------------|-----------------------------|
|      |                |                             |

---

## Quick reference — ports and paths

| Service | Container port | Health / check |
|--------|----------------|----------------|
| API (FastAPI) | 8000 | `GET /health` |
| Web (Next.js) | 3000 | HTTP GET `/` (confirm in App Runner health settings) |
