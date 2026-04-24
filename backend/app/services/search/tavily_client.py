from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.services.search.models import AuthorityCandidate
from app.services.search.text_extract import extract_email, extract_phone, first_line

logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"


def search_tavily(query: str) -> list[AuthorityCandidate]:
    key = getattr(settings, "tavily_api_key", "") or ""
    if not key.strip():
        return []
    payload: dict[str, Any] = {
        "api_key": key.strip(),
        "query": query,
        "search_depth": "basic",
        "max_results": 6,
        "include_answer": False,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(TAVILY_URL, json=payload)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return []

    out: list[AuthorityCandidate] = []
    for item in data.get("results") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        content = str(item.get("content") or item.get("raw_content") or "")
        if not title or not url:
            continue
        snippet = first_line(content) or first_line(title)
        text_blob = f"{content}\n{title}"
        out.append(
            AuthorityCandidate(
                name=title[:300],
                address=first_line(content, 400),
                phone=extract_phone(text_blob),
                email=extract_email(text_blob),
                source="tavily",
                url=url,
                snippet=snippet,
            )
        )
    return out
