# NyayaSetu — Infrastructure (AWS)

This folder holds **Terraform** and related scripts for the NyayaSetu product: **ECR**, **App Runner** (API + web), **CloudFront** (in front of web), **GitHub OIDC** roles for **Deploy** and **Destroy** workflows, and (optional) **S3** remote state.

**Project docs:** [docs/DEPLOYMENT_AWS.md](../docs/DEPLOYMENT_AWS.md) (phased runbook) · [docs/ENVIRONMENT.md](../docs/ENVIRONMENT.md) (env vars, app secrets — not committed in production).

---

## Table of contents

1. [At a glance](#at-a-glance)  
2. [Repository layout](#repository-layout)  
3. [Architecture (what Terraform builds)](#architecture-what-terraform-builds)  
4. [Prerequisites](#prerequisites)  
5. [Terraform: `nyayasetu` stack](#terraform-nyayasetu-stack)  
6. [Remote state (S3)](#remote-state-s3)  
7. [Scripts (repo root)](#scripts-repo-root)  
8. [GitHub Actions](#github-actions)  
9. [Secrets and variables (GitHub)](#secrets-and-variables-github)  
10. [First-time bootstrap](#first-time-bootstrap)  
11. [Day-2 operations](#day-2-operations)  
12. [Custom domain (optional)](#custom-domain-optional)  
13. [Troubleshooting](#troubleshooting)  
14. [Security notes](#security-notes)  

---

## At a glance

| Goal | Where to start |
|------|----------------|
| **Provision** API + web on AWS from scratch | [First-time bootstrap](#first-time-bootstrap) — `./scripts/deploy-aws.sh` after S3 `backend.s3.hcl` exists |
| **Update** running images | Push to `main` (see [Deploy AWS](#deploy-aws) paths) or run **Actions → Deploy AWS** |
| **Tear down** the stack (dangerous) | [Destroy](#destroy-teardown) — `./scripts/destroy-aws.sh` or **Actions → Destroy AWS (Terraform)** |
| **State / CI** for infra only | S3 + `backend.s3.hcl`; destroy workflow needs the same bucket/key as in `backend.s3.hcl` |

---

## Repository layout

| Path | Purpose |
|------|---------|
| `infra/terraform/nyayasetu/` | **Main stack:** ECR (module) · IAM (GitHub deploy, GitHub **terraform destroy**, App Runner ECR access) · App Runner (API + web) · CloudFront (web) · optional OIDC provider |
| `infra/terraform/modules/ecr/` | Reusable ECR: two private repos, lifecycle, outputs |
| `infra/terraform/ecr/` | **Legacy** thin stack: ECR only (for experiments; prefer `nyayasetu`) |
| `infra/terraform/nyayasetu/backend.s3.hcl` | **Local only** (gitignored): S3 backend config. Copy from `backend.s3.hcl.example` |
| `infra/terraform/nyayasetu/terraform.tfvars.json` | **Committed** feature flags: `deploy_api_service`, `deploy_web_service`, `create_cloudfront_web`, `web_app_public_url`, etc. So a plain `apply` does not turn off services by accident |
| `scripts/deploy-aws.sh` | Bootstrap: apply (ECR/IAM) → build/push API → apply API → build/push web → apply web |
| `scripts/destroy-aws.sh` | Local `terraform destroy` with safety env var |
| `scripts/nyayasetu-terraform-init.sh` | `terraform init` with `backend.s3.hcl` (used by deploy/destroy scripts) |
| `scripts/bootstrap-terraform-s3-state-bucket.sh` | One-shot S3 + optional DynamoDB lock for state |
| `scripts/check-no-forbidden-secrets.sh` | CI: blocks committing `.env`, `*.tfstate`, etc. |

`.github/workflows/` (see [GitHub Actions](#github-actions)): `ci.yml` · `deploy-aws.yml` · `destroy-aws-terraform.yml` · `routing-golden-weekly.yml`.

---

## Architecture (what Terraform builds)

- **ECR:** `nyayasetu-api` and `nyayasetu-web` (private; lifecycle policies via module).  
- **App Runner – API:** FastAPI image; public URL of the form `https://<id>.<region>.awsapprunner.com` (e.g. `ap-south-1`).  
- **App Runner – web:** Next.js; needs **`NEXT_PUBLIC_API_URL`** at **image build** time.  
- **CloudFront (default on):** Distribution in front of **web** App Runner; default hostname `dxxxx.cloudfront.net`. Origins use HTTPS; **origin request** policy does not forward browser `Host` to App Runner (see *Browser URL* below).  
- **IAM:**  
  - `nyayasetu-apprunner-ecr-access` — ECR pull for App Runner.  
  - `nyayasetu-github-deploy` — **OIDC** to GitHub **this repo**; ECR push + (legacy) App Runner API permissions; ECR policies allow the role.  
  - `nyayasetu-github-terraform-destroy` — **OIDC** to same repo; **AdministratorAccess** (managed) for `terraform destroy` from GitHub. **Narrow in production** if you replace with a custom policy.  
- **Optional:** `aws_iam_openid_connect_provider` for `token.actions.githubusercontent.com` if `create_github_oidc_provider=true` (default `false` on most accounts that already have it).

**Browser / marketing URL:** Users should use **`web_app_public_url`** = CloudFront `https://…` (or your custom domain) so Next.js/Clerk metadata match what users see. If unset, the app may “think” the host is the App Runner hostname. Align the GitHub variable `WEB_APP_PUBLIC_URL`, the Terraform [terraform.tfvars.json](terraform/nyayasetu/terraform.tfvars.json) field `web_app_public_url`, and **Clerk** allowed origins as needed.

---

## Prerequisites

- **AWS account**, billing awareness, a chosen **region** (default `ap-south-1` in `variables.tf` and workflows).  
- **Tools (local):** [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-clipsv2.html), [Docker](https://docs.docker.com/get-docker/), [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5, **optionally** [`gh` CLI](https://cli.github.com/) for `gh secret set`.  
- **Permissions:** your IAM user/role can create S3, DynamoDB, ECR, App Runner, IAM, CloudFront (first deploy).  
- **GitHub:** the repo that matches `github_repository` in [variables](terraform/nyayasetu/variables.tf) (default `manishdev92/NyayaSetu` — override with `TF_VAR_github_repository=owner/name` if needed).  

---

## Terraform: `nyayasetu` stack

**Path:** `infra/terraform/nyayasetu/`

| File / area | Role |
|-------------|------|
| `versions.tf` | Terraform ≥ 1.5, **S3 backend** (settings via `backend.s3.hcl` or CI `ci-backend.hcl`) |
| `variables.tf` | Region, `github_repository`, deploy flags, Clerk/API keys, `create_github_oidc_provider`, `create_cloudfront_web`, `web_app_public_url` |
| `terraform.tfvars.json` | Committed defaults; adjust deploy flags and `web_app_public_url` for your environment |
| `ecr.tf` + `modules/ecr` | ECR repositories |
| `iam_github.tf` | OIDC, `nyayasetu-github-deploy` role, ECR repo policies |
| `iam_github_terraform_destroy.tf` | `nyayasetu-github-terraform-destroy` + AdministratorAccess attachment |
| `iam_apprunner.tf` | App Runner → ECR access role |
| `apprunner.tf` | App Runner services + autoscaling, env, CORS, etc. |
| `cloudfront_web.tf` | CloudFront distribution for web (when `deploy_web_service` and `create_cloudfront_web`) |
| `outputs.tf` | URLs, ARNs, `github_deploy_role_arn`, `github_terraform_destroy_role_arn`, `web_cloudfront_url`, etc. |

**Key commands** (from `infra/terraform/nyayasetu` after [remote state](#remote-state-s3) is set up):

```bash
../../scripts/nyayasetu-terraform-init.sh -upgrade
terraform plan
terraform apply
terraform output
```

**Imports:** If a resource was created outside Terraform, use `terraform import` and then `apply` (e.g. App Runner `web[0]`, module paths as in state).

---

## Remote state (S3)

Terraform in **`nyayasetu`** is configured to use the **[S3 backend](https://developer.hashicorp.com/terraform/language/settings/backends/s3)**. Local-only `terraform.tfstate` in git is forbidden by CI; **do not** commit state.

1. **Create** bucket (and **recommended** DynamoDB table for state locking), e.g.:  
   `BUCKET=YOUR_ACCOUNT_ID-nyayasetu-tfstate ./scripts/bootstrap-terraform-s3-state-bucket.sh`  
   (Set `AWS_REGION` if not `ap-south-1`.)
2. Copy `backend.s3.hcl.example` → **`backend.s3.hcl`** in `infra/terraform/nyayasetu/`, set `bucket`, `key` (e.g. `nyayasetu/terraform.tfstate`), `region`, and `dynamodb_table` if you use locking.
3. **First move from local state:**  
   `terraform init -backend-config=backend.s3.hcl -migrate-state`  
   (Do **not** combine with `-reconfigure` in the same run.)
4. **Already in S3** (new clone or changed laptop):  
   `terraform init -reconfigure -backend-config=backend.s3.hcl`
5. **Destroy workflow** in GitHub uses the same bucket (`TERRAFORM_S3_STATE_BUCKET`, optional key/region/lock) and must find the state object in S3 (`head-object` check) before `terraform` runs.

`backend.s3.hcl` is **gitignored**; share values with your team out of band.

---

## Scripts (repo root)

| Script | Use |
|--------|-----|
| `deploy-aws.sh` | End-to-end bootstrap (ECR + IAM, images, App Runner, outputs). **Requires** `backend.s3.hcl`. |
| `destroy-aws.sh` | `I_UNDERSTAND_DESTROY_NYAYASETU=YES` — `terraform plan -destroy` / `destroy` with matching `create_github_oidc_provider`. |
| `nyayasetu-terraform-init.sh` | `terraform init` with `backend.s3.hcl` ([`-upgrade]`, `[-reconfigure]`, `[-migrate-state]` when needed). |
| `bootstrap-terraform-s3-state-bucket.sh` | Create versioned, encrypted S3 + optional DynamoDB for locking. |
| `check-no-forbidden-secrets.sh` | Used by **CI** to block secrets/state in the repo. |

---

## GitHub Actions

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** (`ci.yml`) | Push/PR to `main` or `master` | Repo safety, YAML parse, backend **pytest**, frontend **tsc** + **build** (placeholders for Clerk in CI). No AWS deploy. |
| **Deploy AWS** (`deploy-aws.yml`) | Push to `main` on [paths] or **workflow_dispatch** | **OIDC** + `AWS_ROLE_TO_ASSUME`: build/push `nyayasetu-api` and `nyayasetu-web` to ECR. App Runner auto-deploys on **`:latest`**. **No** `StartDeployment` in the workflow. |
| **Destroy AWS (Terraform)** (`destroy-aws-terraform.yml`) | **Manual only** | `terraform plan -destroy` + `apply` with state from **S3**. **Confirm** must be exactly `destroy-nyayasetu`. **Destructive.** |
| **Routing golden weekly** (`routing-golden-weekly.yml`) | Monday cron + manual | Smaller Python routing / safety test slice. No AWS. |

[Deploy] **paths** on `main` include: `backend/Dockerfile`, `backend/requirements.txt`, `backend/app/**`, `frontend/**`, `deploy-aws.yml`, `docker-compose.yml`.

---

## Secrets and variables (GitHub)

**Location:** *Repository → Settings → Secrets and variables → Actions.*

| Type | Name | Required for | How to get / notes |
|------|------|--------------|---------------------|
| **Secret** | `AWS_ROLE_TO_ASSUME` | **Deploy** | `terraform output -raw github_deploy_role_arn` (role `nyayasetu-github-deploy`) |
| **Secret** | `NEXT_PUBLIC_API_URL` | **Deploy** (web build) | `terraform output -raw api_public_url` (HTTPS, no trailing slash) |
| **Secret** | `AWS_TERRAFORM_DESTROY_ROLE_ARN` | **Destroy** | `terraform output -raw github_terraform_destroy_role_arn` after the role exists in state |
| **Variable** (opt.) | `AWS_REGION` | **Deploy** / **Destroy** | e.g. `ap-south-1` if not defaulting in the workflow |
| **Variable** (opt.) | `WEB_APP_PUBLIC_URL` | **Deploy** | `terraform output -raw web_cloudfront_url` or your custom `https://` app URL; baked as `NEXT_PUBLIC_APP_URL` |
| **Variable** | `TERRAFORM_S3_STATE_BUCKET` | **Destroy** | Same S3 bucket name as in `backend.s3.hcl` |
| **Variable** (opt.) | `TERRAFORM_S3_STATE_KEY` | **Destroy** | Default `nyayasetu/terraform.tfstate` if unset |
| **Variable** (opt.) | `TERRAFORM_S3_STATE_REGION` | **Destroy** | State **bucket** region if different from the stack’s `AWS_REGION` / CLI default |
| **Variable** (opt.) | `TERRAFORM_S3_DYNAMODB_TABLE` | **Destroy** / lock | Must match `dynamodb_table` in `backend.s3.hcl` if you use locking |

`AWS_APPRUNNER_*_SERVICE_ARN` (if present) are **optional** for the current **Deploy** workflow; deploy relies on ECR + auto-deploy.

`gh` examples (after `terraform` works and you are in the right repo):

```bash
gh secret set AWS_ROLE_TO_ASSUME -b "$(terraform output -raw github_deploy_role_arn)" -R owner/repo
gh variable set TERRAFORM_S3_STATE_BUCKET -b "your-bucket" -R owner/repo
```

---

## First-time bootstrap

1. Complete [Remote state (S3)](#remote-state-s3) so `terraform init` succeeds.  
2. From the **repo root** with `aws` + `docker` + `terraform` on `PATH`, and (optionally) `OPENAI` / Clerk in env if you want them in TF:

```bash
export AWS_REGION=ap-south-1
./scripts/deploy-aws.sh
```

3. Set [GitHub secrets and variables](#secrets-and-variables-github) from `terraform output`.  
4. Push a change on **main** in the **Deploy** [paths] or run **Actions → Deploy AWS** to refresh images.  

**OIDC provider 409** (`EntityAlreadyExists`): set `create_github_oidc_provider=false` (default). Only new accounts: `export TF_VAR_create_github_oidc_provider=true` for the **first** apply.  

**Import:** If the GitHub **destroy** or **deploy** roles are missing, run `terraform plan` in `nyayasetu` and `apply` so IAM matches the repo.  

---

## Day-2 operations

| Task | Suggestion |
|------|------------|
| **New image for API or web** | Commit under [Deploy paths](#github-actions) on `main`, or **Run workflow** on **Deploy AWS**. |
| **Change stack (replicas, env, CloudFront, …)** | Edit `terraform/*.tf` or `terraform.tfvars.json` → `terraform plan` / `apply` in `nyayasetu`. |
| **Rotate GitHub `AWS_*` after IAM change** | `terraform output` again → update repo secrets. |
| **Tear down everything in this state** | [Destroy](#destroy-teardown) (local with confirm env var, or GitHub **Destroy** with all vars/secrets and **confirm** = `destroy-nyayasetu`). |

**Local destroy preview:**

```bash
export I_UNDERSTAND_DESTROY_NYAYASETU=YES
./scripts/destroy-aws.sh --plan
# then:
export I_UNDERSTAND_DESTROY_NYAYASETU=YES
./scripts/destroy-aws.sh
```

Match `TF_VAR_create_github_oidc_provider` to your last successful apply. After a full destroy, **recreate** deploy/destroy roles with a new `terraform apply` and update **GitHub** ARNs.  

**GitHub Destroy** additionally requires: destroy **secret** + S3 **bucket** variable, state file present in S3, and the **create_github_oidc_provider** form field matching your stack.  

---

## Custom domain (optional)

Use **ACM (public) in us-east-1** for **CloudFront**, add **CNAME/alias** in your DNS (e.g. Hostinger) for `app.yourdomain.com` → CloudFront, set **Alternate domain** + certificate on the distribution, then set **`web_app_public_url`**, `WEB_APP_PUBLIC_URL`, and API **CORS** as needed. See the longer discussion in the main [DEPLOYMENT_AWS](../docs/DEPLOYMENT_AWS.md) doc and in-repo comments on `cloudfront_web.tf`.  

---

## Troubleshooting

- **`terraform` / `terraform output` / `apply`:** “**Backend initialization required**” — run [Remote state](#remote-state-s3): `init` with `backend.s3.hcl` (`-migrate-state` or `-reconfigure` as appropriate). **Never** use both `-reconfigure` and `-migrate-state` in one command.  
- **S3** `NoSuchBucket` — create the bucket (script or console) and fix `backend.s3.hcl`.  
- **Deploy (Actions) — OIDC / `AssumeRoleWithWebIdentity`:** [Existing section B](#b-github-action-fails-on-configure-aws-oidc-or-stsassumerolewithwebidentity) below.  
- **ECR / App Runner AccessDenied** after assume: region, ECR policy, and role ARNs.  
- **No credentials in job:** [D](#d-no-valid-credential-sources-in-the-job).  
- **Destroy (Actions):** [F](#f-destroy-aws-terraform--missing-secret-missing-bucket-or-head-object-404) — `head-object` 404, wrong bucket/key/region, or destroy role not able to use S3/Dynamo + destroy APIs.  
- **App Runner “only two services” in region:** [E](#e-app-runner-account--is-restricted-and-can-support-only-two-app-runner-services-per-region).  
- **Git over HTTPS 401 in Terminal:** [A](#a-git-push-fails-not-actions) — not AWS.  

The following are adapted from the previous troubleshooting (details preserved):

### A) `git push` fails (not Actions)

That is **Git auth to GitHub**, not AWS. Use `gh auth login` + `gh auth setup-git`, or a **PAT** with `repo` scope. If a GUI sets `GIT_ASKPASS` incorrectly, in **Terminal** try `unset GIT_ASKPASS` and push again.

### B) GitHub Action fails on **Configure AWS (OIDC)** or `sts:AssumeRoleWithWebIdentity`

1. **Secret** name is exactly **`AWS_ROLE_TO_ASSUME`**, value is the full **deploy** role ARN — no extra spaces.  
2. **Trust** on that role: provider `token.actions.githubusercontent.com`, subject like `repo:owner/repo:*` (must match [variables](terraform/nyayasetu/variables.tf) `github_repository`).  
3. **OIDC provider** exists in the same account (or Terraform created it with `create_github_oidc_provider=true` once).  
4. **Repo settings → Actions → General** — workflow **Read and write** if the org allows; use the **same** repo (not a fork) for org secrets.  

### C) ECR or App Runner `AccessDenied` after role assumption

Align **region** (`vars.AWS_REGION`), and ARNs. Re-`apply` if policies drifted.

### D) “No valid credential sources” in the job

The **Deploy** / **Destroy** **secret** is missing in **this** repository’s Actions secrets (not only org default if the repo does not use them).  

### E) App Runner: `Account … is restricted and can support only two App Runner services per region`

Free or limited accounts: only **two** services per region. `nyayasetu-api` + `nyayasetu-web` use two slots. Remove other test services, change region, or request a limit from AWS.  

### F) **Destroy AWS (Terraform)** — missing secret, missing bucket, or `head-object` 404

1. The **destroy** **role** must be able to use the **S3** state (including `HeadObject`) and **DynamoDB** if locking, plus all services Terraform deletes. The **ECR push-only** “deploy” role is **not** sufficient.  
2. **TERRAFORM_S3_*** variables** must match the state object you actually migrated.  
3. **Regions** of bucket, lock table, and `AWS_REGION` in the workflow must be coherent.  

---

## Security notes

- **nyayasetu-github-terraform-destroy** is trusted only for **one GitHub repo**’s OIDC subject, but the attached policy is **broad (AdministratorAccess)** by design for frictionless `terraform destroy`. Tighten with a custom IAM policy in production.  
- **Never** commit: real `.env` files, `terraform.tfstate`, or credentials in `tfvars` that are not examples. **CI** blocks common mistakes.  
- **Root AWS account** — use for billing/IAM only; use IAM users/roles with least privilege for day to day, and **OIDC roles** for GitHub, not long-lived keys on the runner.  

---

*Last structure update matches the repository layout; adjust account IDs, regions, and repo name to your environment.*
