#!/usr/bin/env bash
# NyayaSetu — bootstrap ECR images + App Runner (Terraform in infra/terraform/nyayasetu).
# Prerequisites: aws CLI, docker, terraform; AWS credentials (e.g. AWS_PROFILE).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform/nyayasetu"
REGION="${AWS_REGION:-ap-south-1}"

export TF_VAR_aws_region="${TF_VAR_aws_region:-$REGION}"
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  export TF_VAR_openai_api_key="$OPENAI_API_KEY"
fi

echo "==> Terraform: base stack (ECR + IAM + OIDC; no App Runner yet)"
(
  cd "$TF_DIR"
  terraform init -upgrade
  terraform apply -auto-approve \
    -var="deploy_api_service=false" \
    -var="deploy_web_service=false"
)

REPO_URL="$(cd "$TF_DIR" && terraform output -raw ecr_api_repository_url)"
REGISTRY="${REPO_URL%/*}"
echo "==> ECR registry: $REGISTRY"

echo "==> Docker login"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "==> Build & push API"
docker build -t "${REGISTRY}/nyayasetu-api:latest" "${ROOT}/backend"
docker push "${REGISTRY}/nyayasetu-api:latest"

echo "==> Terraform: deploy API App Runner"
(
  cd "$TF_DIR"
  terraform apply -auto-approve \
    -var="deploy_api_service=true" \
    -var="deploy_web_service=false"
)

API_PUBLIC="$(cd "$TF_DIR" && terraform output -raw api_public_url)"
echo "==> API URL: $API_PUBLIC"

echo "==> Build & push Web (NEXT_PUBLIC_API_URL baked at build time)"
docker build \
  --build-arg "NEXT_PUBLIC_API_URL=${API_PUBLIC}" \
  -t "${REGISTRY}/nyayasetu-web:latest" \
  "${ROOT}/frontend"
docker push "${REGISTRY}/nyayasetu-web:latest"

echo "==> Terraform: deploy Web App Runner"
(
  cd "$TF_DIR"
  terraform apply -auto-approve \
    -var="deploy_api_service=true" \
    -var="deploy_web_service=true"
)

echo "==> Done."
cd "$TF_DIR" && terraform output
