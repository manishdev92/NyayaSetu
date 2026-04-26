"""
Sprint P4-3: ingest statute-shaped Markdown into Pinecone (local dir or S3 prefix).

  python -m app.rag.jobs.ingest_statutes --path ./my_acts --dry-run
  python -m app.rag.jobs.ingest_statutes --s3-uri s3://bucket/ingest/v1/ --dry-run

Requires OPENAI_API_KEY, PINECONE_*; S3 path needs AWS creds (env / ~/.aws / role).
Files use `---` frontmatter (`act_id`, `source_url` recommended).
See `docs/CORPUS_V1_BOUNDARY.md` and `tests/fixtures/ingest_statutes/`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.rag.ingest.pipeline import iter_ingest_entries
from app.rag.ingest.sources.local_markdown import LocalMarkdownDirectorySource
from app.rag.pinecone_legal_index import upsert_knowledge_entries


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest statute Markdown into Pinecone (local dir or s3:// prefix).")
    p.add_argument(
        "--path",
        type=str,
        default="",
        help="Directory containing *.md (with frontmatter). Ignored if --s3-uri is set.",
    )
    p.add_argument(
        "--s3-uri",
        type=str,
        default="",
        help="S3 location of *.md, e.g. s3://my-bucket/ingest/v1/ (requires AWS credentials; not the whole bucket).",
    )
    p.add_argument("--dry-run", action="store_true", help="Print JSON summary; no embed / upsert")
    p.add_argument(
        "--max-chunk-chars",
        type=int,
        default=3_000,
        help="Max chars per chunk before sliding window (P4-2; token proxy).",
    )
    p.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Overlap when sliding long sections.",
    )
    p.add_argument("--no-recurse", action="store_true", help="Only top-level .md, no subfolders")
    p.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Pinecone upsert batch size (embed batch).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse()
    s3_uri = (getattr(args, "s3_uri", None) or "").strip()
    root = (args.path or "").strip()
    if s3_uri and root:
        print("error: use either --s3-uri or --path, not both", file=sys.stderr)
        return 2
    if not s3_uri and not root:
        print("error: --path or --s3-uri is required", file=sys.stderr)
        return 2
    if s3_uri:
        from app.rag.ingest.s3_statute_staging import staged_s3_prefix_for_ingest

        try:
            with staged_s3_prefix_for_ingest(s3_uri) as tmp_root:
                return _ingest_from_root(
                    tmp_root,
                    no_recurse=bool(args.no_recurse),
                    args=args,
                    s3_source=s3_uri,
                )
        except (OSError, ValueError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    rp = Path(root)
    if not rp.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    return _ingest_from_root(
        rp,
        no_recurse=bool(args.no_recurse),
        args=args,
        s3_source=None,
    )


def _ingest_from_root(
    rp: Path,
    *,
    no_recurse: bool,
    args: argparse.Namespace,
    s3_source: str | None,
) -> int:
    source = LocalMarkdownDirectorySource(rp, recursive=not no_recurse)
    n_md = len(source.discover_markdown_files())
    rows: list[dict[str, Any]] = list(
        iter_ingest_entries(
            source,
            max_chunk_chars=int(args.max_chunk_chars),
            overlap_chars=int(args.overlap),
        )
    )
    summary: dict[str, Any] = {
        "n_chunks": len(rows),
        "n_markdown_files": n_md,
    }
    if s3_source:
        summary["s3_uri"] = s3_source
    if bool(args.dry_run):
        sample = rows[0] if rows else None
        summary["sample_id"] = sample.get("id") if isinstance(sample, dict) else None
        summary["sample_source_version"] = (sample or {}).get("source_version")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if sample:
            print("---\n" + (sample or {}).get("content", "")[:1_200])
        return 0
    n = upsert_knowledge_entries(rows, batch_size=max(1, int(args.batch_size)))
    print(json.dumps({"upserted_vectors": n, **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
