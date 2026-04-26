#!/usr/bin/env bash
# Run terraform init in infra/terraform/nyayasetu with S3 backend (backend.s3.hcl).
# First-time migration from local .tfstate to S3 (use one command; do not combine -reconfigure and -migrate-state):
#   terraform init -backend-config=backend.s3.hcl -migrate-state
# If state is already in S3: terraform init -reconfigure -backend-config=backend.s3.hcl
# Extra args are passed through (e.g. -upgrade, -reconfigure, -migrate-state).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform/nyayasetu"

if [[ ! -f "${TF_DIR}/backend.s3.hcl" ]]; then
  echo "Missing ${TF_DIR}/backend.s3.hcl" >&2
  echo "Copy backend.s3.hcl.example, create the S3 bucket, then (from that dir) migrate with:" >&2
  echo "  (local state → S3) terraform init -backend-config=backend.s3.hcl -migrate-state" >&2
  echo "  (already in S3)  terraform init -reconfigure -backend-config=backend.s3.hcl" >&2
  echo "See: infra/README.md (Remote state / S3)." >&2
  exit 1
fi

( cd "$TF_DIR" && exec terraform init -input=false -backend-config=backend.s3.hcl "$@" )
