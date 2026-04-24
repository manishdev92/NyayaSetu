from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from app.services.search.bing_client import search_bing
from app.services.search.models import AuthorityCandidate
from app.services.search.queries import build_queries
from app.services.search.serpapi_client import search_serpapi
from app.services.search.tavily_client import search_tavily

logger = logging.getLogger(__name__)


def _norm_url(url: str) -> str:
    try:
        p = urlparse(url.strip().lower())
        path = p.path.rstrip("/") or ""
        return f"{p.netloc}{path}"
    except Exception:
        return url.strip().lower()


def dedupe_candidates(items: list[AuthorityCandidate]) -> list[AuthorityCandidate]:
    seen: set[str] = set()
    out: list[AuthorityCandidate] = []
    for c in items:
        u = c.get("url") or ""
        if not u:
            # keep local_json without URL
            key = f"nourl:{hash(c.get('name', ''))}"
        else:
            key = _norm_url(u)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def gather_remote_candidates(user_input: str, city: str | None, department: str) -> list[AuthorityCandidate]:
    """Run Tavily, SerpAPI, and Bing queries in parallel (including site:gov.in style queries)."""
    qs = build_queries(city, department, user_input)

    tasks: list[tuple[str, object]] = [
        ("tavily_main", lambda: search_tavily(qs["main"])),
        ("tavily_gov", lambda: search_tavily(qs["gov_in"])),
        ("serp_main", lambda: search_serpapi(qs["main"])),
        ("serp_gov", lambda: search_serpapi(qs["gov_in"])),
        ("bing_main", lambda: search_bing(qs["context"])),
        ("bing_gov", lambda: search_bing(qs["gov_in"])),
    ]

    merged: list[AuthorityCandidate] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                batch = fut.result()
                for c in batch:
                    cc = dict(c)
                    if "gov" in name and cc.get("source") in ("tavily", "serpapi", "bing"):
                        cc["source"] = f"{cc['source']}_gov_in"
                    merged.append(cc)
            except Exception as e:
                logger.warning("Search task %s failed: %s", name, e)

    return dedupe_candidates(merged)
