"""
Pinecone vector search for the curated legal KB (NS-S5-02).
Uses the same `filter_entries_by_issue_type` contract as the local pipeline.
Falls back to the JSON pipeline when not configured.
"""

from __future__ import annotations

import logging
from typing import Any

from pinecone import Pinecone

from app.ai.text_embeddings import EMBEDDING_MODEL, embed_texts
from app.config import settings
from app.rag.legal_knowledge_base.retriever import load_knowledge_entries
from app.services.legal_relevance_filter import filter_entries_by_issue_type

logger = logging.getLogger(__name__)

_index: Any = None


def _get_index() -> Any:
    global _index
    if _index is not None:
        return _index
    if not (settings.pinecone_api_key and str(settings.pinecone_index or "").strip()):
        raise RuntimeError("Pinecone not configured")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    _index = pc.Index(str(settings.pinecone_index).strip())
    return _index


def _is_pinecone_available() -> bool:
    return bool(
        str(settings.pinecone_api_key or "").strip() and str(settings.pinecone_index or "").strip()
    )


def metadata_to_entry(metadata: dict[str, Any] | None, match_id: str) -> dict[str, Any] | None:
    if not metadata:
        return None
    raw_tags = metadata.get("tags")
    if isinstance(raw_tags, list) and all(isinstance(x, str) for x in raw_tags):
        tags = [x.strip() for x in raw_tags if str(x).strip()]
    else:
        ts = str(metadata.get("tags_csv") or "")
        tags = [t.strip() for t in ts.split(",") if t.strip()]
    return {
        "id": str(metadata.get("entry_id") or match_id),
        "domain": str(metadata.get("domain") or "").strip().lower(),
        "content": str(metadata.get("content") or ""),
        "source_name": str(metadata.get("source_name") or ""),
        "source_url": str(metadata.get("source_url") or ""),
        "section": str(metadata.get("section") or ""),
        "law_type": str(metadata.get("law_type") or ""),
        "verified": bool(metadata.get("verified", True)),
        "tags": tags,
    }


def entry_to_metadata(entry: dict[str, Any], *, content_max: int = 32_000) -> dict[str, Any]:
    tags = [str(t).strip() for t in (entry.get("tags") or []) if str(t).strip()]
    content = str(entry.get("content") or "")
    if len(content) > content_max:
        content = content[:content_max] + "\n[truncated]"
    m: dict[str, Any] = {
        "entry_id": str(entry.get("id") or ""),
        "domain": str(entry.get("domain") or "").lower(),
        "content": content,
        "source_name": str(entry.get("source_name") or "")[:2_000],
        "source_url": str(entry.get("source_url") or "")[:2_000],
        "section": str(entry.get("section") or "")[:1_000],
        "tags_csv": ",".join(t.lower() for t in tags),
        "verified": bool(entry.get("verified", True)),
    }
    if len(tags) <= 64:
        m["tags"] = tags
    if entry.get("law_type"):
        m["law_type"] = str(entry.get("law_type"))[:500]
    return m


def _entry_key(e: dict[str, Any]) -> str:
    return str(e.get("id") or "").strip() or str(e.get("source_url") or "").strip() or str(hash(e.get("content", "")[:200]))


def _match_to_dict(m: Any) -> tuple[str, float, dict[str, Any] | None]:
    sc = float(
        (getattr(m, "score", None) or (m.get("score") if isinstance(m, dict) else None) or 0.0) or 0.0
    )
    sc = max(0.0, min(1.0, sc))
    mid = str(
        (getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else None) or "").strip() or "unknown"
    )
    raw_meta: dict[str, Any] | None = None
    meta_obj = getattr(m, "metadata", None) or (m.get("metadata") if isinstance(m, dict) else None)
    if isinstance(meta_obj, dict):
        raw_meta = meta_obj
    return (mid, sc, raw_meta)


def pinecone_rag_scored(
    query: str,
    issue_type: str,
    *,
    top_k: int,
    max_candidates: int,
) -> tuple[list[tuple[float, dict[str, Any]]], int, bool, bool]:
    """
    If Pinecone is selected and configured, return ranked (score, entry) plus flags.
    Fourth: True = Pinecone produced this path (use even when empty; do not re-run local JSON RAG for the same case).
    False = caller should run the in-process / JSON pipeline.
    """
    if not _is_pinecone_available():
        return ([], 0, bool(settings.openai_api_key), False)

    embs = embed_texts([query])
    if not embs or not embs[0]:
        logger.warning("rag_pinecone: no query embedding, falling back to local")
        return ([], 0, bool(settings.openai_api_key), False)

    n_fetch = min(200, max(8, int(max_candidates)))
    ns = (settings.pinecone_namespace or "").strip()

    try:
        index = _get_index()
    except Exception as e:
        logger.warning("rag_pinecone: index open failed: %s", e)
        return ([], 0, bool(settings.openai_api_key), False)

    try:
        res = index.query(
            vector=embs[0],
            top_k=n_fetch,
            include_metadata=True,
            namespace=ns,
        )
    except Exception as e:
        logger.warning("rag_pinecone: query failed, falling back to local: %s", e)
        return ([], 0, bool(settings.openai_api_key), False)

    raw_matches: list[Any] = []
    if res is not None:
        if hasattr(res, "matches") and res.matches is not None:
            raw_matches = list(res.matches)
        elif isinstance(res, dict) and "matches" in res:
            raw_matches = list(res.get("matches") or [])

    by_key: dict[str, tuple[float, dict[str, Any]]] = {}
    for m in raw_matches:
        mid, sc, raw_meta = _match_to_dict(m)
        if not raw_meta:
            continue
        en = metadata_to_entry(raw_meta, mid)
        if not en or not str(en.get("source_url") or "").strip():
            continue
        if not en.get("verified", True):
            continue
        k = _entry_key(en)
        if k not in by_key or sc > by_key[k][0]:
            by_key[k] = (sc, en)

    if not by_key:
        return ([], 0, bool(settings.openai_api_key) and bool(embs[0]), True)

    # Preserve Pinecone order (best first) for stable tie-break, then run issue filter.
    ordered = [e for _, e in sorted(by_key.values(), key=lambda t: -t[0])]
    seen_k: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for e in ordered:
        k2 = _entry_key(e)
        if k2 in seen_k:
            continue
        seen_k.add(k2)
        deduped.append(e)

    issue_filtered = filter_entries_by_issue_type(deduped, issue_type)
    pool_size = len(issue_filtered)
    out: list[tuple[float, dict[str, Any]]] = []
    for e in issue_filtered:
        s = by_key.get(_entry_key(e), (0.0, e))[0]
        out.append((float(s), e))
    out.sort(key=lambda t: -t[0])
    out = out[:top_k]
    embedding_used = bool(settings.openai_api_key) and bool(embs[0])
    return (out, pool_size, embedding_used, True)


def upsert_curated_knowledge_from_file(batch_size: int = 20) -> int:
    """
    Embed `knowledge_seed` entries and upsert into the configured Pinecone index.
    Re-run when content or the embedding model changes. Index must exist (dimension 1536, cosine, same model as queries).
    """
    if not _is_pinecone_available():
        raise ValueError("Set pinecone_api_key and pinecone_index in environment / .env (see app.config).")
    entries = load_knowledge_entries()
    if not entries:
        return 0
    index = _get_index()
    ns = (settings.pinecone_namespace or "").strip()
    total = 0
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        texts = [str(e.get("content") or e.get("source_name") or "") for e in batch]
        embs = embed_texts(texts)
        if len(embs) != len(batch):
            raise RuntimeError("OpenAI embed failed: got %d vectors for %d items" % (len(embs), len(batch)))
        to_upsert: list[dict[str, Any]] = []
        for e, vec in zip(batch, embs, strict=True):
            pid = str(e.get("id") or "").strip() or f"e{hash((e.get('source_url'), e.get('content', '')[:200]))%10**10}"
            to_upsert.append(
                {
                    "id": pid,
                    "values": vec,
                    "metadata": entry_to_metadata(e),
                }
            )
        if ns:
            index.upsert(vectors=to_upsert, namespace=ns)  # type: ignore[call-arg]
        else:
            index.upsert(vectors=to_upsert)
        total += len(to_upsert)
    logger.info("pinecone_upserted count=%d model=%s", total, EMBEDDING_MODEL)
    return total
