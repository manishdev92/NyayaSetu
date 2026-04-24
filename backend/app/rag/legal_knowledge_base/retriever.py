from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ISSUE_TO_DOMAINS: dict[str, list[str]] = {
    "corporate": ["civil", "procedure", "administrative"],
    "salary": ["labour", "employment"],
    "fraud": ["criminal", "procedure"],
    "traffic": ["traffic", "motor"],
    "land": ["land", "revenue"],
    "police": ["criminal", "procedure"],
    "police_oversight": ["criminal", "procedure"],
    "family": ["family"],
    "cyber": ["cyber", "it_act"],
    "consumer": ["consumer"],
    "financial": ["banking", "administrative", "civil"],
    "rti": ["administrative", "procedure"],
    "civic": ["administrative", "civil"],
    "education": ["administrative", "consumer", "civil"],
    "women_child": ["family", "criminal", "procedure"],
    "senior_citizen": ["family", "administrative"],
    "general": ["civil", "procedure", "administrative"],
    "civil_dispute": ["civil", "procedure", "administrative"],
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


@lru_cache
def _load_entries() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parent / "knowledge_seed.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("entries", [])
    return [r for r in rows if r.get("verified") is True and (r.get("source_url") or "").strip()]


def load_knowledge_entries() -> list[dict[str, Any]]:
    """Public loader for strict RAG pipeline (curated ingest only)."""
    return list(_load_entries())


def retrieve_legal_knowledge(
    query: str,
    issue_type: str,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """
    Keyword + domain hybrid retrieval over the curated knowledge base.
    Only returns entries marked verified=True (ingestion-time gate).
    """
    entries = _load_entries()
    if not entries:
        return []

    q_tokens = _tokenize(query)
    preferred_domains = set(_ISSUE_TO_DOMAINS.get(issue_type, []))

    scored: list[tuple[float, dict[str, Any]]] = []
    for e in entries:
        dom = (e.get("domain") or "").lower()
        tags = [t.lower() for t in (e.get("tags") or [])]
        text = f"{e.get('content', '')} {e.get('source_name', '')} {' '.join(tags)}"
        t_tokens = _tokenize(text)
        overlap = len(q_tokens & t_tokens)
        domain_boost = 2.5 if dom in preferred_domains or preferred_domains & set(tags) else 0.0
        score = overlap + domain_boost + (0.5 if dom in preferred_domains else 0.0)
        scored.append((score, e))

    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [e for s, e in scored if s > 0][:limit]
