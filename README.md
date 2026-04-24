# NyayaSetu

## About the project

**NyayaSetu** (“nyaya” ≈ justice, “setu” ≈ bridge) is a **legal AI assistant** platform: users can upload legal materials, get structured explanations and next steps, and chat in a **safety-aware** pipeline designed for **India-relevant** context—authorities, land and emergency signals, and **English + Hindi** (including Romanized Hindi) in the UI and API.

**What it does**

- **Document intelligence** — Ingest PDFs and images, optional **OCR** (including difficult scans / empty-text PDFs where configured), extract text, and ground answers with configurable **RAG** (local or Pinecone).
- **Conversational legal help** — Streamed and non-streamed generation, routing through **multi-agent** logic, **crisis / emergency** triage, **authority** and domain checks, and eval hooks (see e.g. golden routing tests in CI).
- **Product features** — **Clerk** authentication, **Stripe** subscriptions and entitlements, usage limits, **offline** / retry queue on the web client, and a **lawyer-style dashboard** (in progress) for saved cases.
- **Operations** — FastAPI service, Next.js PWA-style shell, **pytest**-heavy backend, and **AWS** (App Runner, ECR, CloudFront) with **GitHub Actions** for build and optional Terraform lifecycle.

**What to expect**

- This is **decision support and drafting help**, not a law firm. Users should **verify** outcomes with a qualified professional for matters that require it.  
- The codebase is an active product: see [docs/ROADMAP_TRACKER.md](docs/ROADMAP_TRACKER.md) for phase status and [docs/DEPLOYMENT_AWS.md](docs/DEPLOYMENT_AWS.md) for how it is run in the cloud.

---

## Repository layout

| Area | Path | Tech |
|------|------|------|
| **Web** | [`frontend/`](frontend/) | Next.js 16, React 19, TypeScript, Tailwind, Clerk |
| **API** | [`backend/`](backend/) | Python 3.11, FastAPI, pytest |
| **Infra (AWS)** | [`infra/`](infra/) | Terraform (App Runner, ECR, CloudFront, IAM, optional S3 state) |
| **Docs** | [`docs/`](docs/) | Deployment, environment, roadmaps, specs |
| **Scripts** | [`scripts/`](scripts/) | Deploy, destroy, S3 state bootstrap, checks |

**Deep-dive (AWS & Terraform):** [infra/README.md](infra/README.md)  
**Phased deployment & milestones:** [docs/DEPLOYMENT_AWS.md](docs/DEPLOYMENT_AWS.md)  
**User request flow (UI → API → layers → output):** [docs/USER_REQUEST_FLOW.md](docs/USER_REQUEST_FLOW.md)  
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
