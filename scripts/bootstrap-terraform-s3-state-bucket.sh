#!/usr/bin/env bash
# One-time: create an S3 bucket (and optional DynamoDB lock table) for Terraform state in ap-south-1.
# Usage: AWS_REGION=ap-south-1 BUCKET=your-account-nyayasetu-tfstate ./scripts/bootstrap-terraform-s3-state-bucket.sh
# Then copy backend.s3.hcl.example to infra/terraform/nyayasetu/backend.s3.hcl and run:
#   cd infra/terraform/nyayasetu && terraform init -backend-config=backend.s3.hcl -migrate-state
set -euo pipefail

BUCKET="${BUCKET:-}"
REGION="${AWS_REGION:-ap-south-1}"
DYNAMO_TABLE="${DYNAMO_TABLE:-nyayasetu-terraform-locks}"
ACCOUNT="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"

if [[ -z "$BUCKET" ]]; then
  echo "Set BUCKET, e.g. BUCKET=${ACCOUNT}-nyayasetu-tfstate" >&2
  exit 1
fi

echo "==> S3 bucket $BUCKET in $REGION (account $ACCOUNT)"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "   Bucket already exists, skipping create."
else
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=${REGION}" >/dev/null
  fi
  aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
  aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration '{
    "Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]
  }'
  aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

echo "==> DynamoDB table for state locking: $DYNAMO_TABLE"
if ! aws dynamodb describe-table --table-name "$DYNAMO_TABLE" --region "$REGION" &>/dev/null; then
  aws dynamodb create-table \
    --region "$REGION" \
    --table-name "$DYNAMO_TABLE" \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH
  aws dynamodb wait table-exists --table-name "$DYNAMO_TABLE" --region "$REGION"
fi

echo "==> Done. Put these into infra/terraform/nyayasetu/backend.s3.hcl (from example) and run terraform init -migrate-state."
