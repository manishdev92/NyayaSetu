"""P4: statute ingest helpers (sources, chunking, pipeline to Pinecone)."""

from app.rag.ingest.types import IngestChunk, NormalizedDocument

__all__ = [
    "IngestChunk",
    "NormalizedDocument",
]
