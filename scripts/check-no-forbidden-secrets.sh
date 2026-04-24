#!/usr/bin/env bash
# Fails the build if disallowed files are tracked. Run in CI and before commit.
# Does not replace secret scanning; blocks obvious mistakes.
set -euo pipefail
cd "$(dirname "$0")/.."

# Tracked .env (never .env.example, never *.example)
if git ls-files -z 2>/dev/null | tr '\0' '\n' | grep -E '(^|/)\\.env$' | grep -vE '\\.env\\.example$' | grep -q .; then
  echo "Error: a file named exactly .env is tracked. Use .env.example only; keep real .env out of git."
  git ls-files | grep -E '(^|/)\\.env$' | grep -vE '\\.env\\.example$' || true
  exit 1
fi

# Terraform state
if git ls-files 2>/dev/null | grep -E '\\.tfstate$|\\.tfstate\.'; then
  echo "Error: Terraform state file(s) are tracked. Remove and keep *.tfstate in .gitignore only."
  exit 1
fi

# Tracked .tfvars (except .example; root .gitignore has !*.tfvars.example)
if git ls-files 2>/dev/null | grep -E '\\.tfvars$' | grep -v '\\.tfvars\\.example$'; then
  echo "Error: *.tfvars (non-example) is tracked. Use terraform.tfvars.example; keep secrets in env/TF_VAR."
  exit 1
fi

echo "OK: no tracked .env, .tfstate, or secret tfvars."
