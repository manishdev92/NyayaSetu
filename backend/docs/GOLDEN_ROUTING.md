# Golden routing & safety sets (P6-01)

**Goal:** keep jurisdiction, crisis triage, and authority gates regressions visible without a single “mega” e2e suite. Use this doc to know **where** the golden cases live; extend by adding a test next to the referenced files.

**Classifier taxonomy smoke:** table-driven rows in **`tests/test_classifier_golden_cases.py`** (`_GOLDEN`) — one pass per line over `issue_type`, `domain`, and `router_intent`.

## Authority ↔ domain (criminal / labour, etc.)

| Intention (human) | Automated check | File |
|-------------------|-----------------|------|
| Criminal route must not return Labour office as verified | `test_strict_gate_rejects_labour_for_criminal_police` | `tests/test_authority_domain_resolution.py` |
| Router intent → department + domain gate | `department_for_router_intent`, `strict_authority_passes_domain_gate` | `tests/test_authority_domain_resolution.py` |

**Mismatch log:** `app/logs/authority_mismatch.json` (append-only). Triage new rows into tests per `ROADMAP_TRACKER.md` (NS-S1-01 / P6-01).

## Crisis & emergency

| Area | File(s) |
|------|---------|
| Emergency detection / triage | `test_emergency_intelligence.py`, `test_crisis_triage.py` |
| Hybrid routing | `test_hybrid_routing.py` |
| Land / strict guard | `test_strict_land_guard.py` |

## Clarification & RAG (observability, not “golden answers”)

| Area | File |
|------|------|
| RAG PII-safe logging, grounding | `test_rag_pipeline_observability.py` |
| Pinecone adapter (when enabled) | `test_pinecone_rag.py` |
| LLM clarifier (when not mocked) | `test_llm_clarification_agent.py` |

## How to run fast routing/safety slice

```bash
cd backend && ./scripts/run_routing_safety_tests.sh
```

**CI:** `.github/workflows/routing-golden-weekly.yml` runs the classifier golden file and this script on a **weekly** schedule (and `workflow_dispatch`).

Full suite:

```bash
cd backend && python -m pytest tests/ -q
```

## Evaluator / verifier layer map

See `docs/EVALUATORS.md` for which layer owns legal phrasing, output shape, and optional deterministic checks.

When adding a **new golden** row, prefer: one focused `pytest` + a one-line reference in the table above.

## Verifier review cadence (P6-01)

- After **material classifier or routing changes**, run `tests/test_classifier_golden_cases.py` and the routing/safety script; add rows for any new taxonomy bucket you rely on in production.
- **Quarterly** (or before a major demo): skim `EVALUATORS.md`, re-run the full backend `pytest` suite, and spot-check `authority_mismatch` logs if enabled.
- When **statutes or helplines** change in the real world, update curated JSON / emergency data first, then add a regression test if the bug was user-visible.

