---
marp: true
theme: default
paginate: true
header: NyayaSetu — Technical demo
footer: Andela AI Engineering Bootcamp · 10 min
style: |
  section { font-size: 28px; }
  h1 { font-size: 1.6em; color: #1c1917; }
  h2 { font-size: 1.25em; color: #292524; }
---

<!-- 
  Render: VS Code "Marp for VS Code" extension → Export PDF/HTML/PPTX
  Or: npx @marp-team/marp-cli docs/demo/DEMO_TECH_SLIDES_MARP.md -o NyayaSetu-demo.pdf
-->

# NyayaSetu
## AI legal companion for India · Technical overview

**Live:** https://jhkdghx4dc.ap-south-1.awsapprunner.com/chat

*Educational support — not a substitute for a qualified advocate.*

---

# Problem

- People struggle to map **facts → right authority** (police vs consumer forum vs court).
- Generic LLMs give **fluent but unsafe** answers: wrong venue, invented contacts, no jurisdiction discipline.
- Need **structured drafts**, **explicit uncertainty**, and paths to **official sources** (e.g. India Code).

---

# Product (what ships today)

| Area | Capability |
|------|----------------|
| **Chat** | Streaming progress, clarification when routing is ambiguous |
| **Drafting** | Formal letter / complaint / application templates per authority |
| **Grounding** | RAG + fallback labelling; confidence surfaced where relevant |
| **Modes** | Citizen vs lawyer-oriented context window (deployment-configured) |

---

# High-level architecture

```
Browser (Next.js)
       │  HTTPS
       ▼
┌──────────────────┐     ┌─────────────────┐
│  Web App Runner   │     │ API App Runner   │
│  Next.js          │────▶│ FastAPI          │
└──────────────────┘     └────────┬─────────┘
                                  │
                    Pinecone / local RAG · OpenAI · classifiers · evaluators
```

*Optional:* CloudFront in front of web; custom `.in` domain via Terraform path in repo.*

---

# Backend (FastAPI)

- **Legal routing / classification** — intent, severity, jurisdiction hints.
- **Streaming generate** — phases + clarification + structured JSON output.
- **Safety / triage** — e.g. crisis vs administrative follow-up (explicit rules).
- **RAG** — curated chunks; Pinecone when configured · keyword fallback paths.
- **Governance** — usage limits, billing hooks, configurable feature flags.

---

# Frontend (Next.js)

- ** `/chat`** — streamed assistant UX, attachments (where enabled), locale (EN / HI / Roman Hindi).
- **Marketing** — static-friendly pages; Clerk for auth where required.
- **Exports** — copy / Word / print-PDF client-side from draft text.

---

# AWS production (this deployment)

| Layer | Service |
|-------|---------|
| **Images** | Amazon **ECR** (`nyayasetu-api`, `nyayasetu-web`) |
| **Runtime** | **AWS App Runner** — API :8000, Web :3000 |
| **CDN** (typical) | **CloudFront** in front of web (optional / Terraform) |
| **DNS / domain** | Route 53 + ACM — see `docs/CUSTOM_DOMAIN_IN.md` |

**Not in core path:** Lambda, API Gateway, RDS for this stack’s default deploy.

---

# CI/CD (GitHub Actions)

- **CI** on `main` / PR: repo safety scan · **pytest** (backend) · **tsc + lint + build** (frontend).
- **Deploy AWS** on push to `main` (paths: `backend/app/**`, `frontend/**`, Docker, workflow):
  - OIDC → **assume IAM role** → **docker build/push** `:latest` → App Runner **auto-deploy** from ECR.

Secrets: `AWS_ROLE_TO_ASSUME`, `NEXT_PUBLIC_API_URL`; optional `WEB_APP_PUBLIC_URL` for baked app URL.

---

# Trust & transparency (engineering choice)

- Disclaimers and **“verify on official portals / India Code”** messaging.
- **RAG grounding labels** — retrieved vs general fallback; confidence where exposed.
- **Authority blocks** — verified vs suggested vs unknown; no invented government phone numbers.

---

# Live demo script (2–4 min)

1. Open **https://jhkdghx4dc.ap-south-1.awsapprunner.com/chat**
2. One **routing-rich** scenario (clarification chips or follow-up police delay).
3. Show **draft** + **references / next steps** + **export**.

*Backup: screen recording if Wi‑Fi fails.*

---

# Differentiation (positioning)

| Generic chat | NyayaSetu |
|--------------|-----------|
| One-size answer | **Authority-aware** structure + escalation path |
| No provenance | **RAG / citation-style refs** + honest low-match labels |
| Risky urgency | **Triage rules** + educational framing |

---

# What I learned (bootcamp angle)

- **Product == model + UX + guardrails + deploy**, not “prompt only”.
- **Prod discipline** (tests, lint, container deploy) makes weekly iteration credible.

---

# Links & repo

- **App:** https://jhkdghx4dc.ap-south-1.awsapprunner.com/
- **Chat:** https://jhkdghx4dc.ap-south-1.awsapprunner.com/chat
- **Docs:** `docs/DEPLOYMENT_AWS.md`, `infra/README.md`, `docs/CUSTOM_DOMAIN_IN.md`

**Thank you — questions?**
