from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.services.search.models import AuthorityCandidate
from app.services.search.text_extract import extract_email, extract_phone, first_line

logger = logging.getLogger(__name__)


def search_serpapi(query: str) -> list[AuthorityCandidate]:
    key = getattr(settings, "serpapi_api_key", "") or ""
    if not key.strip():
        return []
    params: dict[str, Any] = {
        "engine": "google",
        "q": query,
        "api_key": key.strip(),
        "num": 8,
        "hl": "en",
        "gl": "in",
    }
    try:
        with httpx.Client(timeout=25.0) as client:
            r = client.get("https://serpapi.com/search.json", params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("SerpAPI search failed: %s", e)
        return []

    out: list[AuthorityCandidate] = []
    for item in data.get("organic_results") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("link") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        if not title or not url:
            continue
        text_blob = f"{snippet}\n{title}"
        out.append(
            AuthorityCandidate(
                name=title[:300],
                address=first_line(snippet, 400),
                phone=extract_phone(text_blob),
                email=extract_email(text_blob),
                source="serpapi",
                url=url,
                snippet=first_line(snippet),
            )
        )
    return out
