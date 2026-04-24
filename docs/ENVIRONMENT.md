# Local secrets and environment files

- **Do not commit** `backend/.env`, `frontend/.env`, or any `*.local` files with real API keys. They are listed in `.gitignore` (and `frontend/.gitignore`).
- **Templates only in git:** `backend/.env.example`, `frontend/.env.example` — copy to `.env` and fill in values; never put production secrets in a committed file.
- **CI** (`/.github/workflows/ci.yml`) uses placeholder values for Clerk/Next in the `npm run build` step so the public repo can build without your keys.
- **AWS / production:** `OPENAI_API_KEY`, `CLERK_*`, etc. are injected via **Terraform** (`TF_VAR_*`) and App Runner, or GitHub **secrets** (see `infra/README.md` and `docs/DEPLOYMENT_AWS.md`). The **Deploy AWS** workflow does not read a `.env` from the branch.
- A guard script `scripts/check-no-forbidden-secrets.sh` runs in **CI** to block accidental tracking of root `.env` files, `.tfstate`, and secret `*.tfvars`.
- If you **ever** committed a secret, rotate the key in the provider (Clerk, OpenAI, etc.) and consider [removing it from git history](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
