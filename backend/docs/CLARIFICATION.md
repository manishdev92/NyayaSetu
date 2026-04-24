# Clarification stack (request → questions → draft)

Read this before editing any `clarification_*.py` file. **Call order** is in `app/services/ai_service.py` (`generate_legal_response` / `maybe_clarification_only_response` / `prefetch_intent` + streaming path in `app/api/v1/generate.py`).

## High-level flow

1. **Intent** — `classify_intent_pipeline` → hybrid / priority / issue profile (`prefetch_intent` or full pipeline).
2. **Deterministic gate** — `clarification_engine`: `should_ask_clarification` → `needs_clarification` (structured options/points) or `law_order_safety_gate_*` for violence/crisis.
3. **LLM path (optional)** — `should_use_llm_clarification` + `ambiguous_intent_for_llm_clarification` → `llm_clarification_agent.run_llm_clarification_agent`.
4. **Conversational text** — `clarification_questions_llm.generate_clarification_questions` (chip/caption helper).
5. **Structured + follow-up** — `clarification_structured_llm` / `clarification_followup` when a round of chips was chosen.
6. **Merge** — `get_llm_clarifications` in `ai_service` builds the clarification payload; API streams `clarification` / `result` in `generate.py`.

## File map (what to touch for what)

| Module | Role |
|--------|------|
| `clarification_engine.py` | When to ask; deterministic options; law-order safety; missing-entity flags |
| `clarification_gate.py` | Gate composition (orchestrates with classifier confidence) |
| `llm_clarification_agent.py` | LLM product questions + JSON shape |
| `clarification_questions_llm.py` | Extra wording / chip text |
| `clarification_structured_llm.py` | Structured follow-ups after first answer |
| `clarification_followup.py` | Next-round logic |
| `clarification_agent.py` | Lower-level agent helpers (if still imported) |

## Rules

- Prefer **one more clarification round** over a wrong `issue_type` / wrong authority; hybrid and crisis paths override in `ai_service`.
- New behaviour should get a test under `backend/tests/test_*clarification*`.
