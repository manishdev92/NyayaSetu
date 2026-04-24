# NyayaSetu — AWS infrastructure

Full runbook: [docs/DEPLOYMENT_AWS.md](../docs/DEPLOYMENT_AWS.md).

## Layout

| Path | Purpose |
|------|---------|
| `terraform/modules/ecr/` | Reusable ECR module (two private repos + lifecycle). |
| `terraform/ecr/` | Thin wrapper: ECR only (quick apply). |
| `terraform/nyayasetu/` | **Full stack:** ECR + GitHub OIDC deploy role + App Runner ECR access role + optional App Runner services. |

**Secrets / `.env`:** do not commit real `backend/.env` or `frontend/.env` — they are gitignored. Use `*.env.example` and see [docs/ENVIRONMENT.md](../docs/ENVIRONMENT.md). CI enforces with `scripts/check-no-forbidden-secrets.sh`.

## One-shot bootstrap (recommended)

From the **repository root**, with AWS CLI configured (`aws sts get-caller-identity`):

```bash
export AWS_REGION=ap-south-1   # or your region
# Optional: export OPENAI_API_KEY=...  (passed into API container via Terraform)
./scripts/deploy-aws.sh
```

The script:

1. Applies Terraform with **App Runner off** (creates ECR, IAM, GitHub OIDC provider if missing).
2. Builds and pushes **`nyayasetu-api:latest`**.
3. Applies with **API App Runner on**.
4. Builds **`nyayasetu-web`** with `NEXT_PUBLIC_API_URL` set to the live API URL, pushes **`nyayasetu-web:latest`**.
5. Applies with **Web App Runner on** and prints `terraform output`.

**If apply fails with `EntityAlreadyExists` for `token.actions.githubusercontent.com` (409):** your account already has the GitHub OIDC provider. The Terraform default is now **`create_github_oidc_provider=false`**. Re-run apply or `./scripts/deploy-aws.sh` (no extra env needed). **Brand-new** AWS accounts with *no* such provider: run once with `export TF_VAR_create_github_oidc_provider=true`.

## Destroy (teardown)

**On the machine that has `terraform.tfstate`** for the stack (default local state in `infra/terraform/nyayasetu`):

```bash
export I_UNDERSTAND_DESTROY_NYAYASETU=YES
./scripts/destroy-aws.sh --plan   # optional: show plan only
export I_UNDERSTAND_DESTROY_NYAYASETU=YES
./scripts/destroy-aws.sh
```

`TF_VAR_create_github_oidc_provider` should match the value you used at apply (default `false`).

**GitHub Actions** (manual only): **Actions** → **Destroy AWS (Terraform)** → **Run workflow** (see [`.github/workflows/destroy-aws-terraform.yml`](../.github/workflows/destroy-aws-terraform.yml)). It runs `terraform destroy` only when the stack uses the same [remote state](https://developer.hashicorp.com/terraform/language/settings/backends/s3) as your applies; a runner cannot use a local `terraform.tfstate`. Set repository secret `AWS_TERRAFORM_DESTROY_ROLE_ARN` (broad **destroy** rights — not the ECR deploy role) and, in the form, set **confirm** to `destroy-nyayasetu` exactly.

## ECR-only (legacy)

```bash
cd infra/terraform/ecr
terraform init
terraform apply
```

Use `-var="aws_region=..."` as needed.

## GitHub Actions (OIDC)

**One-time:** complete `./scripts/deploy-aws.sh` (or equivalent Terraform) so ECR, App Runner services, and the GitHub deploy IAM role already exist.

Then in **GitHub** → *Settings → Secrets and variables → Actions*:

| Type | Name | Value |
|------|------|--------|
| Secret | `AWS_ROLE_TO_ASSUME` | `terraform output -raw github_deploy_role_arn` |
| Secret | `NEXT_PUBLIC_API_URL` | `terraform output -raw api_public_url` (HTTPS, no trailing slash) |
| Variable | `AWS_APPRUNNER_API_SERVICE_ARN` | `terraform output -raw api_service_arn` |
| Variable | `AWS_APPRUNNER_WEB_SERVICE_ARN` | `terraform output -raw web_service_arn` |
| Variable (optional) | `AWS_REGION` | e.g. `ap-south-1` — only if not using the default in the workflow |

**After that:** every **push to `main`** that changes `backend/`, `frontend/`, the deploy workflow file, or `docker-compose.yml` runs **Deploy AWS** automatically (build → ECR → App Runner). You can still run **Actions → Deploy AWS → Run workflow** manually.

Federation: IAM must have an OIDC provider for `token.actions.githubusercontent.com` (Terraform creates it when `create_github_oidc_provider=true`). The deploy role trust must match this repo: default **`manishdev92/NyayaSetu`** in `infra/terraform/nyayasetu/variables.tf` (override with `TF_VAR_github_repository` if needed).

## Troubleshooting: “permission denied” / failed deploy

### A) `git push` fails (not Actions)

That is **Git auth to GitHub**, not AWS. Use `gh auth login` + `gh auth setup-git`, or a **PAT** with `repo` scope, and if Cursor shows 401 run `unset GIT_ASKPASS` in **Terminal.app** and push again.

### B) GitHub Action fails on **Configure AWS (OIDC)** or `sts:AssumeRoleWithWebIdentity`

1. **Secret name** must be exactly **`AWS_ROLE_TO_ASSUME`** (full ARN), e.g. `arn:aws:iam::123456789012:role/nyayasetu-github-deploy` — from `terraform output -raw github_deploy_role_arn`. No extra spaces.
2. **Trust policy** must allow **this** repo. In **AWS** → **IAM** → **Roles** → `nyayasetu-github-deploy` → **Trust relationships**, you should see:
   - Provider: `token.actions.githubusercontent.com`
   - Condition on `sub`: `repo:manishdev92/NyayaSetu:*` (or the owner/repo you set in `TF_VAR_github_repository`).  
   If the repo name differs, re-apply Terraform:  
   `terraform apply -var='github_repository=YOUR_ORG/YOUR_REPO'`
3. **OIDC provider** must exist in the same AWS account (Terraform resource `aws_iam_openid_connect_provider.github` or an existing one). Thumbprints: see `iam_github.tf`.
4. **GitHub repo** → **Settings** → **Actions** → **General** → **Workflow permissions**: use **Read and write**; ensure **Allow GitHub Actions to create and approve pull requests** is on if your org requires it. **Forks** of private repos do not get secrets — use the canonical repo, not a fork, for deploy.

### C) ECR or App Runner `AccessDenied` after role assumption

- **Region:** set repository variable **`AWS_REGION`** to the same region as ECR/App Runner (e.g. `ap-south-1`) if you did not deploy there.
- **ARNs:** `AWS_APPRUNNER_API_SERVICE_ARN` / `WEB` must be from `terraform output` in **that** account/region.
- Re-run `terraform apply` if ECR or role policies drifted.

### D) “No valid credential sources” in the job

`AWS_ROLE_TO_ASSUME` is missing or the secret is empty — add the secret in the **same** repository where the workflow runs (not only org-level if the repo does not inherit).

### E) App Runner: `Account … is restricted and can support only two App Runner services per region`

Your AWS account can only run **two** App Runner services in that **region** (common on newer or limited accounts). **Options:**

1. **Free two slots** — In **AWS Console → App Runner** (same region, e.g. `ap-south-1`), delete or pause **old / test** services you do not need, then run `./scripts/deploy-aws.sh` again.
2. **Use another region** — e.g. deploy with `ap-south-1` full: set `export AWS_REGION=us-east-1` (or another region) and re-run **Terraform** in `infra/terraform/nyayasetu` so ECR and App Runner are in that region (you will recreate ECR repos there or use a new state; simplest is a clean `terraform apply` in the new region after updating `aws_region`).
3. **Ask AWS** — **Support** can raise the limit or remove the “restricted” flag on the account.

`nyayasetu-api` + `nyayasetu-web` need **two** services — you must have **zero** other App Runner services in that region, or use a region/limit that allows two new ones.

## Docker login (manual push)

```bash
REGION=ap-south-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
```

## Verify ECR

```bash
aws ecr describe-repositories --repository-names nyayasetu-api nyayasetu-web --region "$REGION"
```
