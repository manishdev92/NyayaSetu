#!/usr/bin/env bash
# Poll until App Runner accepts StartDeployment: Service.Status=RUNNING and the latest
# list-operations entry is not PENDING/IN_PROGRESS/ROLLBACK_IN_PROGRESS.
# (Describe "RUNNING" is not enough: a deploy/rollback may still be in progress.)
# Usage: wait_app_runner_running.sh <service-arn> [region]
# Env: WAIT_MAX_ATTEMPTS (default 100), WAIT_SLEEP_SECS (default 15)
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
    --query 'Service.Status' --output text 2>/dev/null | tr -d '\r' | xargs || true)
  echo "App Runner service status: ${STATUS:-unknown} (attempt $i/$MAX)"
  if [[ "$STATUS" == "DELETED" ]]; then
    echo "This App Runner service was DELETED. The ARN in GitHub (AWS_APPRUNNER_*_SERVICE_ARN) is stale."
    echo "Recreate the service (e.g. terraform apply with deploy_*, or ./scripts/deploy-aws.sh), then update the variable."
    exit 1
  fi
  if [[ "$STATUS" == "CREATE_FAILED" || "$STATUS" == "DELETE_FAILED" ]]; then
    echo "Service is in terminal state: $STATUS — check App Runner events, then fix or recreate."
    exit 1
  fi
  if [[ "$STATUS" == "PAUSED" ]]; then
    echo "Service is PAUSED — resume it in App Runner, then re-run the workflow."
    exit 1
  fi
  if [[ "$STATUS" != "RUNNING" ]]; then
    if [[ $i -eq $MAX ]]; then
      echo "Timeout waiting for RUNNING (last status: ${STATUS:-n/a})."
      exit 1
    fi
    sleep "$SLEEP"
    continue
  fi

  LOP=$(aws apprunner list-operations --service-arn "$ARN" --region "$REGION" --max-results 1 \
    --query 'OperationSummaryList[0].Status' --output text 2>/dev/null | tr -d '\r' | xargs || true)
  LOP=${LOP:-}
  if [[ -z "$LOP" || "$LOP" == "None" ]]; then
    echo "  no recent operation; ready for start-deployment"
    exit 0
  fi
  echo "  latest operation: $LOP"
  case "$LOP" in
    PENDING|IN_PROGRESS|ROLLBACK_IN_PROGRESS)
      if [[ $i -eq $MAX ]]; then
        echo "Timeout: an operation is still in progress; try again or check App Runner console."
        exit 1
      fi
      sleep "$SLEEP"
      ;;
    *)
      echo "  ready for start-deployment"
      exit 0
      ;;
  esac
done

echo "Timeout waiting for deploy-ready state."
exit 1
