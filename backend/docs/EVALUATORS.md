# Evaluators and verification (RISK-02)

NyayaSetu uses **several small, single-purpose “evaluators”** in the generate path. They are **intentionally separate** so each concern can be tested in isolation. **Do not merge** them into one “god module” without a design review and regression tests (routing + `pytest` + authority smoke).

## Layer map (call order in `ai_service` generation path)

| Module | Role | When it runs |
|--------|------|--------------|
| `app/ai/evaluator.py` | `approve_final_response` + `RESPONSE_DISCLAIMER` | After formatter JSON; checks **consistency** between **authority block** and **trust** flags (verified vs suggested/unknown). |
| `app/ai/output_evaluator.py` | `evaluate_generation_output` / `should_regenerate` | Heuristic **draft quality** (0–10) on `document` + `issue_profile` + `authority_block` + category; can trigger a **regeneration** with `STRICT_REGEN_ADDON` + quality addon. |
| `app/ai/authority_alignment.py` | (imported from alignment helpers) | Used in `_regenerate_until_authority_alignment`; not the same as the three above—see that module. |
| `app/evaluators/legal_verifier.py` | `evaluate_response` | **Post-draft** “deterministic legal judge” on **text + authority + RAG ref list**; drives **hallucination_risk** / `fix_required` in **trust_report** (not a regen trigger by itself in the current pipeline). |
| `app/services/output_formatter.py` | `evaluate_response_bundle` | **Final polish**: dedupe, cap `next_steps`, emergency strips, `validate_output_bundle`—**not** a scoring model. |

**Imports today (primary consumer):** `app/services/ai_service.py` pulls `approve_final_response` and `evaluate_generation_output` in the **formatter** branch; `evaluate_response` (legal_verifier) near **response assembly** for `trust_report`; `evaluate_response_bundle` on the **output bundle** before the client response.

`app/api/v1/generate.py` and `app/services/authority_pipeline.py` only use `RESPONSE_DISCLAIMER` from `app/ai/evaluator.py`.

## Conventions (avoid silent behavior change)

- **`app/ai/evaluator.py`**: only **authority / trust** consistency. Do not add heuristics on phones in the document here; that belongs in `output_evaluator` or `legal_verifier`.
- **`app/ai/output_evaluator.py`**: heuristics that **suggest a second model pass** (`should_regenerate`). Keep scoring stable or update tests and golden baselines.
- **`app/evaluators/legal_verifier.py`**: trust UX / risk label; keep outputs compatible with `build_trust_report` and API mappers.
- **Aliases**: `evaluate_output` in `output_evaluator` is an alias of `evaluate_generation_output` (external name).

## Related tests (non-exhaustive)

- `tests/test_output_formatter.py` — `evaluate_response_bundle`
- Routing + authority suite: `./scripts/run_routing_safety_tests.sh`
- Wider: `python -m pytest tests/ -q`

## Merging boundary (not planned in RISK-02)

Consolidating `ai/evaluator`, `ai/output_evaluator`, and `evaluators/legal_verifier` would require:

1. A single public facade with explicit sub-steps (for logging and A/B).  
2. Merged golden tests and explicit changelog for any score threshold change.

Until then, keep modules separate and add cross-links in docstrings if you add new evaluators.
