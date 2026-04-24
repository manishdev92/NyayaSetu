from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.services.search.models import AuthorityCandidate
from app.services.search.text_extract import extract_email, extract_phone, first_line

logger = logging.getLogger(__name__)


def search_bing(query: str) -> list[AuthorityCandidate]:
    key = getattr(settings, "bing_search_api_key", "") or ""
    endpoint = getattr(settings, "bing_search_endpoint", "") or "https://api.bing.microsoft.com/v7.0/search"
    if not key.strip():
        return []
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(
                endpoint.rstrip("/"),
                params={"q": query, "count": 8, "mkt": "en-IN"},
                headers={"Ocp-Apim-Subscription-Key": key.strip()},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Bing search failed: %s", e)
        return []

    pages = (data.get("webPages") or {}).get("value") or []
    out: list[AuthorityCandidate] = []
    for item in pages:
        if not isinstance(item, dict):
            continue
        title = str(item.get("name") or "").strip()
        url = str(item.get("url") or "").strip()
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
                source="bing",
                url=url,
                snippet=first_line(snippet),
            )
        )
    return out
