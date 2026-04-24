# Jurisdiction graph (single source of truth)

- **Canonical module:** `app.core.jurisdiction_graph`  
  - `INDIA_JURISDICTION_GRAPH`, `JurisdictionDomain`, `flatten_graph_paths`
  - India-oriented forum labels (police, labour, civil, consumer, land, etc.)

- **Deprecated shim:** `app.core.legal_jurisdiction_graph`  
  - Re-exports the same symbols for older imports. **New code should import from `jurisdiction_graph` only.**
  - A future refactor can replace `from app.core.legal_jurisdiction_graph import X` with `jurisdiction_graph` and delete the shim in one PR (search `rg 'legal_jurisdiction_graph'` first).

- **Consumer:** `app.services.legal_router.route_case` and related routing docs in code comments there.

No merge of two *different* graphs: there is one graph; the second file is an alias.
