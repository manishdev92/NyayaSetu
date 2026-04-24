# Authority code: optional `app/authority/` package (RISK-01, staged)

**Status:** **Batches 1–2 done** — `app/authority/__init__.py` re-exports:

- `app.services.authority_schema` (types + helpers);
- `department_for_router_intent` and `strict_authority_passes_domain_gate` from `authority_intent_resolver`;
- `get_default_authority_provider` from `json_authority_provider`.

**Consumers on `app.authority` include:** `ai_service`, `authority_pipeline`, `authority_hierarchy_service`, `ai/authority_evaluator`, `authority_service`, and `ai/authority_alignment` (lazy import for the gate). Further optional batch: re-export or relocate additional helpers only if import churn is worth it.

**Goal (future):** one import root for authority + routing + alignment code under `app/authority/`, with shims to avoid double maintenance during migration.

## Current clusters (file locations)

| Area | Path(s) |
|------|--------|
| **Pipeline / resolution** | `app/services/authority_pipeline.py`, `authority_service.py`, `authority_provider.py`, `authority_intent_resolver.py` |
| **Schema / types** | `app/services/authority_schema.py` |
| **Directory / search** | `app/services/authority_hierarchy_service.py`, `app/services/authority_provider.py` (incl. JSON) |
| **Routers & validation** | `app/services/authority_router.py`, `authority_validation.py`, `authority_validator.py` |
| **Classifiers** | `app/services/authority_classifier.py` |
| **AI / alignment** | `app/ai/authority_alignment.py`, `app/ai/authority_evaluator.py` |
| **Data access** | `app/services/json_authority_provider.py` (and related) |

**Related but not `authority_` prefix:** `app/trust/trust_engine.py` (consumed by pipeline).

## Suggested execution order (when you pick this up)

1. **Shim re-export** `app/authority/__init__.py` that re-exports only **public** names from the old modules; keep old modules as source of truth.  
2. **Switch one consumer** (e.g. a small import in `ai_service` or a single test) to the new path; `pytest` green.  
3. **Repeat in batches** (pipeline → services → `ai/`), not all files at once.  
4. **Remove** old public paths only after all imports and docs point to `app/authority/`.

## Tests to run per batch

```bash
cd backend && python -m pytest tests/ -q
./scripts/run_routing_safety_tests.sh
```

## Notes

- Canonical **trust** reference remains `app/trust/trust_engine.py` (not duplicated in `app/services` except re-exports; see S1-03 in `ROADMAP_TRACKER.md`).
