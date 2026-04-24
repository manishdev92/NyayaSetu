#!/usr/bin/env bash
# NyayaSetu — bootstrap ECR images + App Runner (Terraform in infra/terraform/nyayasetu).
# Prerequisites: aws CLI, docker, terraform; AWS credentials (e.g. AWS_PROFILE).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform/nyayasetu"
REGION="${AWS_REGION:-ap-south-1}"

export TF_VAR_aws_region="${TF_VAR_aws_region:-$REGION}"
# Default false: many AWS accounts already have the GitHub OIDC provider (409 if we try to create again).
# On a brand-new account with no provider, run: export TF_VAR_create_github_oidc_provider=true
export TF_VAR_create_github_oidc_provider="${TF_VAR_create_github_oidc_provider:-false}"
if [[ -f "$ROOT/backend/.env" && -z "${TF_VAR_openai_api_key:-}" && -z "${OPENAI_API_KEY:-}" ]]; then
  line="$(grep -E '^OPENAI_API_KEY=.' "$ROOT/backend/.env" | head -1)" || true
  if [[ -n "$line" ]]; then
    export OPENAI_API_KEY="${line#OPENAI_API_KEY=}"
  fi
fi
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  export TF_VAR_openai_api_key="$OPENAI_API_KEY"
fi

if [[ -f "$ROOT/frontend/.env" && -z "${TF_VAR_clerk_secret_key:-}" && -z "${CLERK_SECRET_KEY:-}" ]]; then
  line="$(grep -E '^CLERK_SECRET_KEY=.' "$ROOT/frontend/.env" | head -1)" || true
  if [[ -n "$line" ]]; then
    export CLERK_SECRET_KEY="${line#CLERK_SECRET_KEY=}"
  fi
fi
if [[ -f "$ROOT/frontend/.env" && -z "${TF_VAR_clerk_publishable_key:-}" && -z "${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]]; then
  line="$(grep -E '^NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=.' "$ROOT/frontend/.env" | head -1)" || true
  if [[ -n "$line" ]]; then
    export NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="${line#NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=}"
  fi
fi
if [[ -n "${CLERK_SECRET_KEY:-}" ]]; then
  export TF_VAR_clerk_secret_key="$CLERK_SECRET_KEY"
fi
if [[ -n "${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:-}" ]]; then
  export TF_VAR_clerk_publishable_key="$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
fi

# `docker build --platform` on Apple Silicon can still reuse wrong-arch layer cache. Buildx + --load avoids that.
docker_build_amd64() {
  local image_tag="$1"
  local ctx="$2"
  shift 2
  if docker buildx version >/dev/null 2>&1; then
    docker buildx build --platform linux/amd64 -t "$image_tag" --load "$@" "$ctx"
  else
    docker build --no-cache --platform linux/amd64 -t "$image_tag" "$@" "$ctx"
  fi
}

echo "==> Terraform: base stack (ECR + IAM + OIDC; no App Runner yet)"
(
  cd "$TF_DIR"
  terraform init -upgrade
  terraform apply -auto-approve \
    -var="create_github_oidc_provider=${TF_VAR_create_github_oidc_provider}" \
    -var="deploy_api_service=false" \
    -var="deploy_web_service=false"
)

REPO_URL="$(cd "$TF_DIR" && terraform output -raw ecr_api_repository_url)"
REGISTRY="${REPO_URL%/*}"
echo "==> ECR registry: $REGISTRY"

echo "==> Docker login"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

# App Runner is linux/amd64; base image is pinned in Dockerfiles.
echo "==> Build & push API (linux/amd64)"
docker_build_amd64 "${REGISTRY}/nyayasetu-api:latest" "${ROOT}/backend"
docker push "${REGISTRY}/nyayasetu-api:latest"

echo "==> Terraform: deploy API App Runner"
(
  cd "$TF_DIR"
  terraform apply -auto-approve \
    -var="create_github_oidc_provider=${TF_VAR_create_github_oidc_provider}" \
    -var="deploy_api_service=true" \
    -var="deploy_web_service=false"
)

API_PUBLIC="$(cd "$TF_DIR" && terraform output -raw api_public_url)"
echo "==> API URL: $API_PUBLIC"

echo "==> Build & push Web (NEXT_PUBLIC_API_URL baked at build time, linux/amd64)"
docker_build_amd64 "${REGISTRY}/nyayasetu-web:latest" "${ROOT}/frontend" \
  --build-arg "NEXT_PUBLIC_API_URL=${API_PUBLIC}"
docker push "${REGISTRY}/nyayasetu-web:latest"

echo "==> Terraform: deploy Web App Runner"
(
  cd "$TF_DIR"
  terraform apply -auto-approve \
    -var="create_github_oidc_provider=${TF_VAR_create_github_oidc_provider}" \
    -var="deploy_api_service=true" \
    -var="deploy_web_service=true"
)

echo "==> Done."
cd "$TF_DIR" && terraform output
