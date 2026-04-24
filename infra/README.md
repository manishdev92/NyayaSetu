# NyayaSetu — AWS infrastructure

Full runbook: [docs/DEPLOYMENT_AWS.md](../docs/DEPLOYMENT_AWS.md).

## Layout

| Path | Purpose |
|------|---------|
| `terraform/modules/ecr/` | Reusable ECR module (two private repos + lifecycle). |
| `terraform/ecr/` | Thin wrapper: ECR only (quick apply). |
| `terraform/nyayasetu/` | **Full stack:** ECR + GitHub OIDC deploy role + App Runner ECR access role + optional App Runner services. |

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

**If OIDC provider already exists** in the account (error on apply):

```bash
cd infra/terraform/nyayasetu
terraform apply -var="create_github_oidc_provider=false" ...
```

## ECR-only (legacy)

```bash
cd infra/terraform/ecr
terraform init
terraform apply
```

Use `-var="aws_region=..."` as needed.

## GitHub Actions (OIDC)

After the first successful `terraform apply` in `nyayasetu`:

1. **AWS** — note `terraform output github_deploy_role_arn`.
2. **GitHub** → *Settings → Secrets and variables → Actions*  
   - **Secret:** `AWS_ROLE_TO_ASSUME` = that role ARN.  
   - **Secret:** `NEXT_PUBLIC_API_URL` = value of `terraform output -raw api_public_url` (HTTPS, no trailing slash).  
   - **Variables:** `AWS_APPRUNNER_API_SERVICE_ARN`, `AWS_APPRUNNER_WEB_SERVICE_ARN` = `terraform output` ARNs.
3. Run workflow **Deploy AWS** (*Actions* tab → *workflow_dispatch*).

Federation in AWS (console): IAM → Identity providers — `token.actions.githubusercontent.com` must exist once per account (Terraform creates it when `create_github_oidc_provider=true`).

The Terraform default for GitHub trust is **`manishdev92/NyayaSetu`** (`infra/terraform/nyayasetu/variables.tf`). Change with `TF_VAR_github_repository` if the clone URL differs.

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
