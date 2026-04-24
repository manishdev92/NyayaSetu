"""Deprecated alias — use `app.core.jurisdiction_graph`."""

from app.core.jurisdiction_graph import (
    INDIA_JURISDICTION_GRAPH,
    JurisdictionDomain,
    flatten_graph_paths,
)

__all__ = ["INDIA_JURISDICTION_GRAPH", "JurisdictionDomain", "flatten_graph_paths"]
