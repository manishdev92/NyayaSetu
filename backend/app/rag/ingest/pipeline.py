"""Sprint P4-3/4-4: normalized docs → knowledge entries with versioning fields."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from app.rag.ingest.chunker import chunk_statute_text
from app.rag.ingest.types import NormalizedDocument


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _doc_chunk_id(act_id: str, local_key: str, part_index: int) -> str:
    h = _sha256(f"{local_key}|{act_id}|{part_index}")[:10]
    safe_act = re.sub(r"[^a-zA-Z0-9._-]+", "-", (act_id or "act")[:200])
    return f"{safe_act}__{h}__p{int(part_index)}"


def build_entries_for_document(
    doc: NormalizedDocument,
    *,
    ingested_at: str,
    max_chunk_chars: int,
    overlap_chars: int,
) -> list[dict[str, Any]]:
    m = doc["meta"]
    tags = [t for t in (m.get("tags") or []) if str(t).strip()]
    base_tags = [str(m.get("act_id") or "").strip().lower()] + [x.lower() for x in tags]
    chs = chunk_statute_text(
        doc["text"],
        max_chunk_chars=max_chunk_chars,
        overlap_chars=overlap_chars,
    )
    act = str(m.get("act_id") or "act")
    local_key = str(m.get("local_path") or act)[:2_000]
    out: list[dict[str, Any]] = []
    for ch in chs:
        t = ch["text"]
        sec = (ch.get("section") or "")[:1_200]
        pid = _doc_chunk_id(act, local_key, ch["part_index"])
        hx = _sha256(t)
        out.append(
            {
                "id": pid,
                "act_id": act[:500],
                "content": t,
                "source_name": str(m.get("source_name") or act)[:1_200],
                "source_url": str(m.get("source_url") or "")[:2_000],
                "source_version": str(m.get("source_version") or "unspecified")[:500],
                "ingested_at": ingested_at,
                "content_sha256": hx,
                "domain": str(m.get("domain") or "general")[:64],
                "section": sec,
                "law_type": str(m.get("law_type") or "Act")[:32],
                "verified": bool(m.get("verified", True)),
                "tags": [x for x in base_tags if x][:64],
            }
        )
    return out


def iter_ingest_entries(
    source: Any,
    *,
    max_chunk_chars: int = 3_000,
    overlap_chars: int = 200,
    ingested_at: str | None = None,
) -> Iterator[dict[str, Any]]:
    ts = ingested_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for doc in source.iter_documents():
        for row in build_entries_for_document(
            doc,
            ingested_at=ts,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        ):
            yield row
