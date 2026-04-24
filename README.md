# NyayaSetu

**NyayaSetu** is a full-stack legal AI product: a **Next.js** web app and **FastAPI** backend for document understanding, chat, guardrails, billing, and an India-oriented localization path. This repository is a **monorepo** (frontend, backend, infrastructure as code, and docs).

| Area | Path | Tech |
|------|------|------|
| **Web** | [`frontend/`](frontend/) | Next.js 16, React 19, TypeScript, Tailwind, Clerk |
| **API** | [`backend/`](backend/) | Python 3.11, FastAPI, pytest |
| **Infra (AWS)** | [`infra/`](infra/) | Terraform (App Runner, ECR, CloudFront, IAM, optional S3 state) |
| **Docs** | [`docs/`](docs/) | Deployment, environment, roadmaps, specs |
| **Scripts** | [`scripts/`](scripts/) | Deploy, destroy, S3 state bootstrap, checks |

**Deep-dive (AWS & Terraform):** [infra/README.md](infra/README.md)  
**Phased deployment & milestones:** [docs/DEPLOYMENT_AWS.md](docs/DEPLOYMENT_AWS.md)  
**Environment variables:** [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) (see also `*.env.example` in `backend/` and `frontend/`)

---

## Quick start (local)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) (or run API + web manually with Node 20+ and Python 3.11+).

1. **Clone and env:** Copy env templates; set API keys and Clerk keys as needed.

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

2. **Compose (API on :8000, web on :3000):**

   ```bash
   docker compose up --build
   ```

3. **Open** `http://localhost:3000` (web) → API at `http://localhost:8000` (CORS is configured for the local web origin in compose).

**Dev without Docker (typical):**

- API: `cd backend && pip install -r requirements.txt` → `uvicorn` / your usual run (see `backend` docs).  
- Web: `cd frontend && npm ci && npm run dev` — set `NEXT_PUBLIC_API_URL` to your local API (e.g. `http://127.0.0.1:8000`).

Do **not** commit real `.env` files. CI enforces a basic check: [`scripts/check-no-forbidden-secrets.sh`](scripts/check-no-forbidden-secrets.sh).

---

## Testing

```bash
# Backend
cd backend && pip install -r requirements.txt && pip install "pytest>=7" && python -m pytest tests/ -q

# Frontend
cd frontend && npm ci && npx tsc --noEmit && npm run build
```

**GitHub Actions** on `main` / `master` runs a **CI** workflow: repo safety, workflow YAML parse, backend tests, and frontend typecheck + production build (with placeholder Clerk env for build).

---

## Cloud deployment (summary)

- **Path:** ECR → App Runner (API + web) → optional **CloudFront** in front of the web service. **GitHub Actions** builds and pushes images with **OIDC**; App Runner can auto-deploy on `:latest`.
- **Full runbook, secrets, destroy workflow, S3 state:** [infra/README.md](infra/README.md)  
- **Phased checklist:** [docs/DEPLOYMENT_AWS.md](docs/DEPLOYMENT_AWS.md)

---

## Workflows (GitHub Actions)

| Workflow | Purpose |
|----------|---------|
| [CI](.github/workflows/ci.yml) | Tests + static checks; no cloud deploy. |
| [Deploy AWS](.github/workflows/deploy-aws.yml) | Build & push to ECR on `main` (path-filtered) or manual run. |
| [Destroy AWS (Terraform)](.github/workflows/destroy-aws-terraform.yml) | **Manual only** — full `terraform destroy` of the stack (destructive). |
| [Routing golden weekly](.github/workflows/routing-golden-weekly.yml) | Scheduled routing / safety pytest slice. |

---

## Project status & roadmap

- **Living phase tracker:** [docs/ROADMAP_TRACKER.md](docs/ROADMAP_TRACKER.md)  
- **Dashboard spec (P8):** [docs/P8_DASHBOARD_SPEC.md](docs/P8_DASHBOARD_SPEC.md)

---

## Contributing

- Prefer **focused** changes with tests where applicable.  
- Run **CI** locally (commands above) before opening a PR when you touch `backend/`, `frontend/`, or workflows.  
- **Infrastructure** changes: document in or alongside [infra/README.md](infra/README.md) and use Terraform in `infra/terraform/nyayasetu/` with remote state (see that README).

---

## License

Add a `LICENSE` file at the repository root if you intend to open-source or share this project; the repo may not include one by default.
