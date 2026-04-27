from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.research.case_law.types import CaseLawSnippet

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"

_CASE_LAW_DOMAIN_ALLOWLIST = (
    "indiankanoon.org",
    "sci.gov.in",
    "ecourts.gov.in",
    "judis.nic.in",
    "hcservices.ecourts.gov.in",
    "districts.ecourts.gov.in",
)

_DOMAIN_BLOCKLIST_TOKENS = (
    "blog",
    "chronicle",
    "nseindia",
    "aibi",
    "youtube",
    "twitter",
    "facebook",
    "instagram",
)

_CASE_LAW_TEXT_MARKERS = (
    "judgment",
    "judgement",
    "precedent",
    "appeal",
    "petition",
    "writ",
    "bench",
    "supreme court",
    "high court",
    "district court",
    "tribunal",
    "ratio decidendi",
    "section",
    "article",
    "act",
    "tenant",
    "landlord",
    "lease",
    "rent control",
    "v.",
    " vs ",
    " versus ",
)

_QUERY_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "about",
    "under",
    "issue",
    "legal",
    "india",
    "case",
    "law",
    "laws",
    "court",
}


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


def _host_from_url(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").strip().lower()
    except Exception:
        return ""


def _blocked_domain(host: str) -> bool:
    if not host:
        return True
    return any(token in host for token in _DOMAIN_BLOCKLIST_TOKENS)


def _is_likely_case_law_domain(url: str) -> bool:
    host = _host_from_url(url)
    if _blocked_domain(host):
        return False
    if host.endswith(".gov.in") or host.endswith(".nic.in"):
        return True
    if any(host == d or host.endswith(f".{d}") for d in _CASE_LAW_DOMAIN_ALLOWLIST):
        return True
    if "kanoon" in host:
        return True
    if "court" in host or "courts" in host or "judiciary" in host:
        return True
    return False


def _looks_case_law_content(title: str, snippet: str) -> bool:
    blob = f"{title} {snippet}".strip().lower()
    if not blob:
        return False
    return any(marker in blob for marker in _CASE_LAW_TEXT_MARKERS)


def _tokenize_query_terms(query: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-zA-Z]{4,}", (query or "").lower()):
        if token in _QUERY_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
        if len(out) >= 6:
            break
    return out


def _relevance_reason(
    *,
    query_terms: list[str],
    title: str,
    snippet: str,
    url: str,
    legalish_domain: bool,
) -> str:
    blob = f"{title} {snippet}".lower()
    matched_terms = [t for t in query_terms if t in blob][:3]
    matched_markers = [m for m in _CASE_LAW_TEXT_MARKERS if m in blob][:2]
    parts: list[str] = []
    if matched_terms:
        parts.append(f"matches issue terms: {', '.join(matched_terms)}")
    if matched_markers:
        parts.append(f"legal markers: {', '.join(matched_markers)}")
    if legalish_domain:
        parts.append("source domain looks court/legal")
    else:
        host = _host_from_url(url)
        if host:
            parts.append(f"content matched but source host is {host}")
    if not parts:
        return "keyword overlap with the issue context"
    return "; ".join(parts)[:300]


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
        query_terms = _tokenize_query_terms(q)
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
        fallback: list[CaseLawSnippet] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("content") or item.get("raw_content") or "").strip()
            if not title or not url:
                continue
            legalish_domain = _is_likely_case_law_domain(url)
            legalish_content = _looks_case_law_content(title, snippet)
            if not legalish_content:
                continue
            blob = f"{title}\n{snippet}"
            row = CaseLawSnippet(
                title=title[:500],
                citation=_extract_citation(title, snippet),
                court="",
                year=_extract_year(blob),
                source="tavily_preview",
                url=url[:2000],
                snippet=snippet[:1200],
                relevance_reason=_relevance_reason(
                    query_terms=query_terms,
                    title=title,
                    snippet=snippet,
                    url=url,
                    legalish_domain=legalish_domain,
                ),
            )
            if legalish_domain:
                out.append(row)
            else:
                fallback.append(row)
        if out:
            return out[:max_results]
        # Keep panel non-empty when strict domain filter excludes all items.
        return fallback[:max_results]
