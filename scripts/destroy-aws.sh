#!/usr/bin/env bash
# NyayaSetu — destroy AWS resources managed by Terraform in infra/terraform/nyayasetu.
# Requires: aws, terraform; the same tfstate and AWS account used for apply.
#
# The GitHub "deploy" OIDC role (ECR push + App Runner start-deployment only) cannot run this.
# Run on the machine that has terraform.tfstate for this stack, or use remote state (S3) + the GitHub destroy workflow.
#
# Usage:
#   I_UNDERSTAND_DESTROY_NYAYASETU=YES ./scripts/destroy-aws.sh
#   I_UNDERSTAND_DESTROY_NYAYASETU=YES ./scripts/destroy-aws.sh --plan
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform/nyayasetu"
REGION="${AWS_REGION:-ap-south-1}"
export AWS_REGION
export TF_VAR_aws_region="${TF_VAR_aws_region:-$REGION}"
# Must match the value used at apply; affects whether the OIDC provider is in state.
export TF_VAR_create_github_oidc_provider="${TF_VAR_create_github_oidc_provider:-false}"

PLAN_ONLY=false
if [[ "${1:-}" == "--plan" || "${1:-}" == "-plan" || -n "${DESTROY_DRY_RUN:-}" ]]; then
  PLAN_ONLY=true
fi

if [[ -z "${I_UNDERSTAND_DESTROY_NYAYASETU:-}" || "${I_UNDERSTAND_DESTROY_NYAYASETU}" != "YES" ]]; then
  echo "Refusing: export I_UNDERSTAND_DESTROY_NYAYASETU=YES and re-run."
  echo "This destroys: App Runner services, ECR repositories, deploy IAM, App Runner ECR access role, ECR policies — and the GitHub OIDC provider if this stack created it (create_github_oidc_provider was true at apply time)."
  echo "Preview: I_UNDERSTAND_DESTROY_NYAYASETU=YES $0 --plan"
  exit 1
fi

echo "==> Terraform init ($TF_DIR)"
"${ROOT}/scripts/nyayasetu-terraform-init.sh"

if [[ "$PLAN_ONLY" == "true" ]]; then
  echo "==> terraform plan -destroy (no changes applied)"
  (
    cd "$TF_DIR"
    terraform plan -destroy -var="create_github_oidc_provider=${TF_VAR_create_github_oidc_provider}" -no-color
  )
  echo "==> Plan only — done. Remove --plan to run terraform destroy -auto-approve"
  exit 0
fi

echo "==> terraform destroy (auto-approve)"
(
  cd "$TF_DIR"
  terraform destroy -auto-approve -var="create_github_oidc_provider=${TF_VAR_create_github_oidc_provider}"
)

echo "==> Done. ECR image data is gone; App Runner and IAM in this state are removed."
echo "    Legacy: if you ever used infra/terraform/ecr as a separate state, run terraform destroy there too."
