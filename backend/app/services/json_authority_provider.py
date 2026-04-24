from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.authority_provider import AuthorityLookupProvider, AuthorityRecord


@lru_cache
def _load_authorities_file(path_str: str) -> dict[str, Any]:
    with Path(path_str).open(encoding="utf-8") as f:
        return json.load(f)


class JsonFileAuthorityProvider(AuthorityLookupProvider):
    """Local JSON-backed authority directory (deterministic, auditable)."""

    _CITY_ALIASES: dict[str, str] = {
        "banaras": "varanasi",
        "benares": "varanasi",
        "kashi": "varanasi",
        "new delhi": "delhi",
        "ncr delhi": "delhi",
        "gurgaon": "delhi",
        "gurugram": "delhi",
    }

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path(__file__).resolve().parent.parent / "data" / "authorities.json"

    def _normalize_city_token(self, city: str) -> str:
        s = city.strip().lower()
        return re.sub(r"\s+", " ", s)

    def resolve_city_key(self, city: str | None) -> str | None:
        if not city or not str(city).strip():
            return None
        raw = _load_authorities_file(str(self._path))
        t = self._normalize_city_token(str(city))
        if t in self._CITY_ALIASES:
            t = self._CITY_ALIASES[t]
        if t in raw:
            return t
        return None

    @staticmethod
    def _blank_to_none(v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    def get_local_authority(self, city: str, issue_type: str) -> AuthorityRecord | None:
        ck = self.resolve_city_key(city)
        if not ck:
            return None

        raw = _load_authorities_file(str(self._path))
        city_block = raw.get(ck)
        if not isinstance(city_block, dict):
            return None

        dept = issue_type if issue_type in city_block else None
        if dept is None:
            return None

        rec = city_block.get(dept)
        if not isinstance(rec, dict):
            return None

        name = self._blank_to_none(rec.get("name"))
        if not name:
            return None

        rec_out: AuthorityRecord = {
            "found": True,
            "department": dept,
            "name": name,
            "address": self._blank_to_none(rec.get("address")),
            "phone": self._blank_to_none(rec.get("phone")),
            "email": self._blank_to_none(rec.get("email")),
            "source": "json_v1",
        }
        return rec_out


_default_json_provider = JsonFileAuthorityProvider()


def get_default_authority_provider() -> AuthorityLookupProvider:
    return _default_json_provider
