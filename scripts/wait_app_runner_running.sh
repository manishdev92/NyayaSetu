#!/usr/bin/env bash
# Poll until an App Runner service is RUNNING (required before StartDeployment).
# Usage: wait_app_runner_running.sh <service-arn> [region]
# Env: WAIT_MAX_ATTEMPTS (default 100), WAIT_SLEEP_SECS (default 15) → up to ~25 min default.
set -euo pipefail

ARN="${1:-}"
REGION="${2:-${AWS_REGION:-ap-south-1}}"
if [[ -z "$ARN" ]]; then
  echo "usage: $0 <service-arn> [region]" >&2
  exit 1
fi

MAX="${WAIT_MAX_ATTEMPTS:-100}"
SLEEP="${WAIT_SLEEP_SECS:-15}"

for i in $(seq 1 "$MAX"); do
  STATUS=$(aws apprunner describe-service --service-arn "$ARN" --region "$REGION" \
    --query 'Service.Status' --output text 2>/dev/null || true)
  echo "App Runner status: ${STATUS:-unknown} (attempt $i/$MAX)"
  if [[ "$STATUS" == "RUNNING" ]]; then
    exit 0
  fi
  if [[ "$STATUS" == "DELETED" ]]; then
    echo "This App Runner service was DELETED. The ARN in GitHub (AWS_APPRUNNER_API_SERVICE_ARN / _WEB) is stale."
    echo "Recreate the service (e.g. terraform apply with deploy_*, or ./scripts/deploy-aws.sh), then update the repository variable to terraform output api_service_arn / web_service_arn."
    exit 1
  fi
  if [[ "$STATUS" == "CREATE_FAILED" || "$STATUS" == "DELETE_FAILED" ]]; then
    echo "Service is in terminal state: $STATUS — check App Runner events in the console, then fix or recreate the service."
    exit 1
  fi
  if [[ "$STATUS" == "PAUSED" ]]; then
    echo "Service is PAUSED — resume it in AWS App Runner, then re-run the workflow."
    exit 1
  fi
  if [[ $i -eq $MAX ]]; then
    echo "Timeout waiting for RUNNING (last status: ${STATUS:-n/a})."
    exit 1
  fi
  sleep "$SLEEP"
done
