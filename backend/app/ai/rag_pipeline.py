from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)

from app.ai.text_embeddings import embed_texts
from app.config import settings
from app.rag.legal_knowledge_base.retriever import load_knowledge_entries
from app.rag.legal_store.policy import is_allowed_legal_source_url
from app.services.legal_relevance_filter import filter_entries_by_issue_type

VERIFIED_RETRIEVAL_THRESHOLD = 0.75
_KEYWORD_SCORE_CAP = 0.72


class RetrievedLawOut(TypedDict):
    law: str
    section: str
    chunk: str
    source_url: str
    retrieval_score: float
    verified: bool


class RagPipelineOut(TypedDict):
    retrieved_laws: list[RetrievedLawOut]
    confidence_score: float
    embedding_used: bool
    grounding_label: Literal["rag_retrieved", "general_not_case_specific", "no_match"]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _is_official_source_url(url: str) -> bool:
    return is_allowed_legal_source_url(url)


def _keyword_relevance_score(query: str, entry: dict[str, Any]) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    blob = f"{entry.get('content', '')} {entry.get('source_name', '')} {' '.join(entry.get('tags') or [])}"
    t_tokens = _tokenize(blob)
    overlap = len(q_tokens & t_tokens)
    base = overlap / max(len(q_tokens), 4)
    return min(_KEYWORD_SCORE_CAP, 0.08 + base * 0.64)


def _query_hash(query: str) -> str:
    """PII-safe fingerprint for log correlation; never log raw query text."""
    return hashlib.sha256((query or "").encode("utf-8")).hexdigest()[:20]


def _log_rag_observability(
    *,
    query_hash: str,
    issue_type: str,
    top_k: int,
    pool_size: int,
    top_scores: list[float],
    grounding_label: str,
    embedding_used: bool,
    confidence: float,
    n_retrieved: int,
) -> None:
    """Structured one-line log (JSON payload) for retrieval metrics — no PII in payload."""
    payload = {
        "query_hash": query_hash,
        "issue_type": issue_type,
        "top_k": top_k,
        "pool_size": pool_size,
        "top_scores": top_scores,
        "grounding_label": grounding_label,
        "embedding_used": embedding_used,
        "confidence": round(float(confidence), 4),
        "n_retrieved": n_retrieved,
    }
    logger.info("rag_pipeline %s", json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    # Map cosine [-1,1] to [0,1] for display thresholds
    c = dot / (na * nb)
    return max(0.0, min(1.0, (c + 1.0) / 2.0))


def run_strict_rag_pipeline(
    query: str,
    issue_type: str,
    *,
    top_k: int = 5,
) -> RagPipelineOut:
    """
    Strict pipeline: classify domain filter → relevance score → rank → top-k.
    Only retrieved chunk text may be cited as law content downstream.
    """
    qh = _query_hash(query)

    pine_ok = False
    if settings.rag_vector_store == "pinecone":
        try:
            from app.rag.pinecone_legal_index import pinecone_rag_scored  # local import: optional at runtime

            scored, pool_size, embedding_used, pine_ok = pinecone_rag_scored(
                query,
                issue_type,
                top_k=top_k,
                max_candidates=settings.pinecone_query_candidates,
            )
        except Exception as e:
            logger.warning("rag_pinecone path failed, using local: %s", e)
            pine_ok = False
            scored = []
            pool_size = 0
            embedding_used = bool(settings.openai_api_key)

    if not pine_ok:
        raw = load_knowledge_entries()
        filtered = filter_entries_by_issue_type(raw, issue_type)
        if not filtered:
            _log_rag_observability(
                query_hash=qh,
                issue_type=issue_type,
                top_k=top_k,
                pool_size=0,
                top_scores=[],
                grounding_label="no_match",
                embedding_used=False,
                confidence=0.0,
                n_retrieved=0,
            )
            return RagPipelineOut(
                retrieved_laws=[],
                confidence_score=0.0,
                embedding_used=False,
                grounding_label="no_match",
            )

        embedding_used = bool(settings.openai_api_key)
        scored = []

        if embedding_used:
            texts = [query] + [str(e.get("content") or "") for e in filtered]
            embs = embed_texts(texts)
            if len(embs) == len(texts):
                q_emb = embs[0]
                for i, e in enumerate(filtered):
                    sim = _cosine_similarity(q_emb, embs[i + 1])
                    scored.append((sim, e))
            else:
                embedding_used = False

        if not embedding_used:
            for e in filtered:
                scored.append((_keyword_relevance_score(query, e), e))
        pool_size = len(filtered)

    scored.sort(key=lambda x: -x[0])
    top = scored[:top_k]
    top_k_scores = [round(float(s), 4) for s, _ in top]

    retrieved: list[RetrievedLawOut] = []
    for score, e in top:
        if score <= 0.0:
            continue
        url = str(e.get("source_url") or "").strip()
        law_name = str(e.get("source_name") or "Official source")
        chunk_text = str(e.get("content") or "").strip()
        verified = score >= VERIFIED_RETRIEVAL_THRESHOLD and _is_official_source_url(url)
        retrieved.append(
            RetrievedLawOut(
                law=law_name,
                section=str(e.get("section") or ""),
                chunk=chunk_text,
                source_url=url,
                retrieval_score=round(score, 4),
                verified=verified,
            )
        )

    confidence = max((r["retrieval_score"] for r in retrieved), default=0.0)

    if not retrieved:
        _log_rag_observability(
            query_hash=qh,
            issue_type=issue_type,
            top_k=top_k,
            pool_size=pool_size,
            top_scores=top_k_scores,
            grounding_label="no_match",
            embedding_used=embedding_used,
            confidence=0.0,
            n_retrieved=0,
        )
        return RagPipelineOut(
            retrieved_laws=[],
            confidence_score=0.0,
            embedding_used=embedding_used,
            grounding_label="no_match",
        )

    if embedding_used and confidence >= 0.45:
        label: Literal["rag_retrieved", "general_not_case_specific", "no_match"] = "rag_retrieved"
    else:
        label = "general_not_case_specific"

    out = RagPipelineOut(
        retrieved_laws=retrieved,
        confidence_score=round(confidence, 4),
        embedding_used=embedding_used,
        grounding_label=label,
    )
    _log_rag_observability(
        query_hash=qh,
        issue_type=issue_type,
        top_k=top_k,
        pool_size=pool_size,
        top_scores=top_k_scores,
        grounding_label=label,
        embedding_used=embedding_used,
        confidence=out["confidence_score"],
        n_retrieved=len(retrieved),
    )
    return out
