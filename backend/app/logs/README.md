# Runtime logs (local / server)

## `authority_mismatch.json`

Append-only JSON array written when `strict_authority_passes_domain_gate` rejects a candidate office type (e.g. Labour for a criminal route). **Expected in production:** occasional rows when search returns off-domain matches; the gate blocks them from the user response.

- Duplicate-looking rows (same `input` / `status`) can happen if the same case is retried; safe to delete or trim the file in dev.
- If this file grows large, add rotation or a max-length policy in a dedicated PR (do not silently drop events without a product decision).

**Tests:** `tests/test_authority_domain_resolution.py` encodes the Labour-vs-criminal expectation (`test_strict_gate_rejects_labour_for_criminal_police`).
