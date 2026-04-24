#!/usr/bin/env bash
# start-deployment with retries (covers rare races after wait_app_runner_running.sh).
# Usage: apprunner_start_deployment.sh <service-arn> [region]
# Env: APPRUNNER_START_DEPLOY_RETRIES (default 8), APPRUNNER_START_DEPLOY_DELAY (default 15)
set -euo pipefail
ARN="${1:-}"
REGION="${2:-${AWS_REGION:-ap-south-1}}"
N="${APPRUNNER_START_DEPLOY_RETRIES:-8}"
DELAY="${APPRUNNER_START_DEPLOY_DELAY:-15}"
if [[ -z "$ARN" ]]; then
  echo "usage: $0 <service-arn> [region]" >&2
  exit 1
fi
set +e
for i in $(seq 1 "$N"); do
  err=$(aws apprunner start-deployment --service-arn "$ARN" --region "$REGION" 2>&1)
  code=$?
  if [[ $code -eq 0 ]]; then
    echo "$err"
    echo "StartDeployment accepted."
    set -e
    exit 0
  fi
  echo "$err" >&2
  if [[ $i -lt $N ]]; then
    echo "StartDeployment not accepted (attempt $i/$N), retrying in ${DELAY}s..." >&2
    sleep "$DELAY"
  fi
done
set -e
exit 1
