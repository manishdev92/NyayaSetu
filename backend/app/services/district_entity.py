from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

# Signals of scraped / tabular junk (never treat as authority)
_SCRAPED_TABLE = re.compile(
    r"(<table\b|<tr\b|<td\b|</table>|^\s*\|.+ \|.+\|)",
    re.IGNORECASE | re.MULTILINE,
)
_PIPE_GRID = re.compile(r"(?:^\|.+\|\s*){3,}", re.MULTILINE)
_EXCESS_PIPES = re.compile(r"\|{4,}")


def normalize_place_token(s: str | None) -> str:
    if not s or not str(s).strip():
        return ""
    t = unicodedata.normalize("NFKC", str(s).strip().lower())
    t = re.sub(r"\s+", " ", t)
    return t


@lru_cache
def _authorities_city_keys() -> frozenset[str]:
    """District keys present in authorities.json — used to detect conflicting districts in text."""
    try:
        path = Path(__file__).resolve().parent.parent / "data" / "authorities.json"
        import json

        with path.open(encoding="utf-8") as f:
            raw: dict[str, Any] = json.load(f)
        return frozenset(k.lower() for k in raw.keys() if isinstance(k, str))
    except Exception:
        return frozenset()


def looks_like_scraped_html_table(text: str | None) -> bool:
    if not text:
        return False
    if _SCRAPED_TABLE.search(text):
        return True
    if _PIPE_GRID.search(text):
        return True
    if _EXCESS_PIPES.search(text):
        return True
    return False


def _whole_word_regex(token: str) -> re.Pattern[str]:
    """ASCII-safe word boundary; good enough for Indian district names in Latin script."""
    esc = re.escape(token)
    return re.compile(rf"(?<!\w){esc}(?!\w)", re.IGNORECASE)


def district_entity_check(
    *,
    user_district_normalized: str,
    combined_text: str,
    office_name: str,
    address: str | None,
) -> tuple[bool, str]:
    """
    External rows only: user district must appear as a whole-token match in authoritative text.
    Reject scraped/tabular junk and pages that reference multiple catalog districts or the wrong one.
    """
    ud = normalize_place_token(user_district_normalized)
    if not ud:
        return False, "missing_user_district"

    raw_bundle = f"{office_name}\n{address or ''}\n{combined_text}"
    if looks_like_scraped_html_table(raw_bundle):
        return False, "scraped_table_or_tabular_junk"

    bundle = normalize_place_token(raw_bundle)

    if not _whole_word_regex(ud).search(bundle):
        return False, "user_district_not_found_in_source_text"

    keys = _authorities_city_keys()
    catalog_hits = [k for k in keys if len(k) >= 3 and _whole_word_regex(k).search(bundle)]

    if len(catalog_hits) >= 2:
        return False, "multiple_known_districts_in_source"

    if len(catalog_hits) == 1 and catalog_hits[0] != ud:
        return False, "page_targets_different_catalog_district"

    return True, "district_ok"
