# User personas — citizen and lawyer (P0-1)

**Purpose:** Shared vocabulary for product, API design (`docs/SPRINTS_PRIORITIZED.md` P0-3 / P1), and UX. NyayaSetu serves **both** everyday users and **legal professionals**; depth, risk, and citation needs differ.

**Related:** `docs/USER_REQUEST_FLOW.md` (technical flow) · `docs/CORPUS_V1_BOUNDARY.md` (what may be ingested in v1) · `docs/SPRINTS_PRIORITIZED.md`

---

## Shared disclaimer (all personas)

NyayaSetu provides **informational and drafting assistance**, not a substitute for **legal advice** from an advocate enrolled with the Bar Council of India or other qualified counsel. **Courts and authorities decide outcomes**; the user must **verify** statutes, notifications, and citations against **official** sources and current law. **No attorney–client relationship** is formed by using the product.

---

## Persona A — General citizen (“citizen mode”)

| Dimension | Expectation |
|-----------|-------------|
| **Primary goal** | Understand what kind of problem they have, **what to do next** (which office, what documents, rough timeline), and get a **plain-language** draft or letter skeleton they can adapt. |
| **Depth** | **Shorter** answers, fewer retrieved chunks, emphasis on **safety** (crisis/emergency routing) and **accessibility** (simple words; EN / HI / hi_latn). |
| **Citations** | Helpful **pointers** to Acts or sections when grounded in the knowledge base; **not** a substitute for reading the bare Act or consulting a lawyer for contested matters. |
| **Risk posture** | **Conservative**: prefer clarification questions, avoid over-specific forum advice without facts, surface **verified authority** contacts where the pipeline allows. |
| **Success looks like** | User feels less lost, knows **next steps**, and has a **usable** draft or checklist without being overwhelmed. |

---

## Persona B — Lawyer / legal professional (“lawyer mode”)

| Dimension | Expectation |
|-----------|-------------|
| **Primary goal** | **Faster research scaffolding**: statute-grounded snippets, **structured** Q&A, memo-style reasoning, draft **applications / notices / issues**, and **argument outlines** with explicit separation of **retrieved text** vs **model synthesis**. |
| **Depth** | **Higher** retrieval budget (e.g. more `top_k` / candidates), willingness to read **longer** context blocks, optional **case-law** layer when licensed sources exist (future sprint). |
| **Citations** | **Strong expectation** of traceable references (Act, section, article / “dhara”, URL or source id where available). Lawyers **must** verify every citation before filing; the product should **never** hide that obligation. |
| **Risk posture** | Same **safety** gates for crisis situations; otherwise **professional** tone, procedural nuance, and explicit **“verify in official gazette / eCourts / India Code”** reminders. |
| **Success looks like** | Time saved on **first drafts** and **issue spotting**; clear **audit trail** of what came from retrieval vs generation; export-friendly structure (future). |

### Sub-segments (vocabulary only; v1 product choice)

| Sub-segment | Typical need | Notes for v1 |
|-------------|--------------|----------------|
| **Solo / small chamber** | Speed, templates, multi-tasking | **Default v1 “lawyer” anchor persona** unless product decides otherwise: optimize for breadth + self-serve. |
| **Mid / large chamber** | Consistency, junior review, firm style | Later: team features, shared libraries, approval flows — **out of scope** for P0/P1 unless explicitly prioritized. |
| **In-house counsel** | Risk framing, compliance memos | Overlap with lawyer mode; may need **corporate** issue-type tuning later. |

**Open product question (was P0-1 ASK):** Confirm whether **v1 “lawyer”** officially means **solo/small chamber first** (recommended default above), or **chamber/enterprise first**. Either way, **one** primary anchor keeps API and retrieval defaults coherent until telemetry proves otherwise.

---

## How personas map to engineering (preview)

| Concept | Citizen | Lawyer |
|---------|---------|--------|
| Retrieval depth | Lighter | Deeper (configurable `top_k` / pool — see Sprint 1 in `docs/SPRINTS_PRIORITIZED.md`) |
| Output shape | Letter + short explanation + next steps | Same + stronger **Q&A** and **citation blocks** when implemented |
| UI / gating | Default experience | Feature flag or subscription-gated **lawyer** entry (implementation in later tasks) |

This document does **not** change runtime behavior until P1+ tasks are implemented.
