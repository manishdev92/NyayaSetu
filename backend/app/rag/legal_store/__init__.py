"""
NyayaSetu legal store facade — curated statutes/procedures only.

Implementation data remains under `app.rag.legal_knowledge_base`; ingestion must
enforce `legal_store.policy` host rules.
"""

from app.rag.legal_knowledge_base.retriever import load_knowledge_entries

from app.rag.legal_store.policy import (
    ALLOWED_LEGAL_HOST_SUFFIXES,
    FORBIDDEN_HOST_HINTS,
    is_allowed_legal_source_url,
)

__all__ = [
    "load_knowledge_entries",
    "ALLOWED_LEGAL_HOST_SUFFIXES",
    "FORBIDDEN_HOST_HINTS",
    "is_allowed_legal_source_url",
]
