from __future__ import annotations

from typing import Any, Literal

from app.config import settings
from app.research.case_law.adapter import CaseLawSource
from app.research.case_law.noop_source import NoopCaseLawSource
from app.research.case_law.tavily_source import TavilyPreviewCaseLawSource


def get_case_law_source() -> CaseLawSource:
    """Dispatch by `case_law_mode` (off treated before call site)."""
    m: Literal["off", "noop", "tavily_preview"] | str = str(
        getattr(settings, "case_law_mode", "off") or "off"
    ).strip().lower()
    if m == "noop":
        return NoopCaseLawSource()
    if m == "tavily_preview":
        return TavilyPreviewCaseLawSource()
    return NoopCaseLawSource()


def _snippet_to_api_dict(s: Any) -> dict[str, Any]:
    if not isinstance(s, dict):
        return {}
    out: dict[str, Any] = {
        "title": str(s.get("title") or "")[:500],
        "citation": str(s.get("citation") or "")[:500],
        "court": str(s.get("court") or "")[:300],
        "source": str(s.get("source") or "")[:120],
        "url": str(s.get("url") or "")[:2000],
        "snippet": str(s.get("snippet") or "")[:4000],
    }
    y = s.get("year")
    if isinstance(y, int) and 1600 < y < 2200:
        out["year"] = y
    else:
        out["year"] = None
    return out


def search_case_law_references(
    query: str,
    *,
    client_mode: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Lawyer-only research side-path. Returns `[]` when case law is off, or for citizen mode.
    """
    if str(client_mode or "").strip().lower() != "lawyer":
        return []
    mode = str(getattr(settings, "case_law_mode", "off") or "off").strip().lower()
    if mode == "off":
        return []
    src = get_case_law_source()
    max_results = int(getattr(settings, "case_law_max_results", 5) or 5)
    want = max(1, min(10, min(int(limit or 5), max_results)))
    raw = src.search((query or "").strip(), limit=want)
    return [_snippet_to_api_dict(x) for x in raw if x]
