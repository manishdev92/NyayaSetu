from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.research.case_law.types import CaseLawSnippet

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"


def _extract_year(blob: str) -> int | None:
    m = re.search(r"\b(19|20)\d{2}\b", blob)
    if not m:
        return None
    y = int(m.group(0))
    return y if 1900 <= y <= 2100 else None


def _extract_citation(title: str, snippet: str) -> str:
    hay = f"{title} {snippet}".strip()
    # Basic Indian-style citation fallback: "v." / "vs." strings are usually the strongest clue.
    m = re.search(r"([A-Z][^,\n]{5,120}\b(v\.|vs\.|versus)\b[^,\n]{5,120})", hay, re.I)
    if m:
        return m.group(1).strip()
    return title.strip()[:250]


class TavilyPreviewCaseLawSource:
    """
    Preview-only research adapter.
    Uses Tavily results to populate the lawyer case-law panel with external snippets.
    """

    def search(self, query: str, *, limit: int = 5) -> list[CaseLawSnippet]:
        key = str(getattr(settings, "tavily_api_key", "") or "").strip()
        q = str(query or "").strip()
        if not key or not q:
            return []
        max_results = max(1, min(10, int(limit or 5)))
        payload: dict[str, Any] = {
            "api_key": key,
            "query": f"{q} India case law judgment precedent",
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(_TAVILY_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("case_law_tavily_preview_failed: %s", e)
            return []

        out: list[CaseLawSnippet] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("content") or item.get("raw_content") or "").strip()
            if not title or not url:
                continue
            blob = f"{title}\n{snippet}"
            out.append(
                CaseLawSnippet(
                    title=title[:500],
                    citation=_extract_citation(title, snippet),
                    court="",
                    year=_extract_year(blob),
                    source="tavily_preview",
                    url=url[:2000],
                    snippet=snippet[:1200],
                )
            )
        return out
