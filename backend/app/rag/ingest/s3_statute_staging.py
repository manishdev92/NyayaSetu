"""
Download statute-shaped Markdown (`.md`) from an S3 prefix into a temp directory for
`LocalMarkdownDirectorySource` / `ingest_statutes`.

Uses the default boto3 credential chain (env vars, shared credentials, instance role, OIDC on GitHub Actions).
"""

from __future__ import annotations

import contextlib
import logging
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MAX_OBJECTS = 2_000
_MAX_OBJECT_BYTES = 8 * 1024 * 1024


def parse_s3_uri(raw: str) -> tuple[str, str]:
    """
    `s3://my-bucket/acts/ipc` -> (`my-bucket`, `acts/ipc`).
    Prefer a folder path like `s3://b/ingest/v1/` (trailing slash) in documentation.
    """
    s = (raw or "").strip()
    if not s.lower().startswith("s3://"):
        raise ValueError("expected s3://bucket/optional/prefix")
    without = s[5:].lstrip("/")
    if not without:
        raise ValueError("expected s3://bucket/...")
    if "/" not in without:
        return without, ""
    i = without.find("/")
    return without[:i], without[i + 1 :].lstrip("/")


def _list_prefix_for_api(prefix: str) -> str | None:
    """`Prefix` for ListObjectsV2. Single-file `foo.md` is valid; else treat as folder (trailing /)."""
    p = (prefix or "").strip()
    if not p:
        return None
    if p.lower().endswith(".md"):
        return p
    if not p.endswith("/"):
        return f"{p.rstrip('/')}/"
    return p


def _key_to_dest_path(key: str, list_prefix: str, dest: Path) -> Path:
    """Map S3 key to a path under `dest` (keep subfolders when key extends the list prefix)."""
    lp = list_prefix or ""
    if lp and not lp.endswith("/") and not lp.lower().endswith(".md"):
        lp = f"{lp.rstrip('/')}/"
    if lp and lp.lower().endswith(".md") and key == lp:
        return dest / Path(key).name
    if lp and key.startswith(lp):
        rel = key[len(lp) :].lstrip("/")
        if rel:
            return dest / rel
    return dest / Path(key).name


def _client() -> Any:
    import boto3

    return boto3.client("s3")


def download_s3_prefix_markdown(bucket: str, prefix: str, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    c = _client()
    n_written = 0
    n_seen = 0
    list_pfx = _list_prefix_for_api(prefix) or ""
    op_args: dict[str, Any] = {"Bucket": bucket}
    if list_pfx:
        op_args["Prefix"] = list_pfx

    paginator = c.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        PaginationConfig={"PageSize": 500},
        **op_args,
    ):
        for obj in page.get("Contents") or []:
            n_seen += 1
            if n_seen > _MAX_OBJECTS:
                raise RuntimeError(
                    f"S3 list exceeded _MAX_OBJECTS={_MAX_OBJECTS}; use a narrower --s3-uri prefix.",
                )
            key = (obj.get("Key") or "").strip()
            if not key or key.endswith("/"):
                continue
            if not key.lower().endswith(".md"):
                continue
            if int(obj.get("Size") or 0) > _MAX_OBJECT_BYTES:
                logger.warning("skip s3://%s/%s (S3 size over cap)", bucket, key)
                continue
            out = _key_to_dest_path(key, list_pfx, dest)
            if out.exists():
                out = out.with_name(f"dup_{n_written}_{out.name}")
            out.parent.mkdir(parents=True, exist_ok=True)
            body = c.get_object(Bucket=bucket, Key=key)["Body"].read()
            if len(body) > _MAX_OBJECT_BYTES:
                logger.warning("skip s3://%s/%s (read over cap)", bucket, key)
                continue
            out.write_bytes(body)
            n_written += 1
    return n_written


@contextlib.contextmanager
def staged_s3_prefix_for_ingest(s3_uri: str) -> Iterator[Path]:
    bucket, raw_prefix = parse_s3_uri(s3_uri)
    if (raw_prefix or "").strip() == "":
        raise ValueError(
            f"refuse s3://{bucket} with no object prefix (too broad); use e.g. s3://{bucket}/ingest/v1/"
        )
    with tempfile.TemporaryDirectory(prefix="nyaya-s3-ingest-") as td:
        root = Path(td)
        n = download_s3_prefix_markdown(bucket, raw_prefix, root)
        if n == 0:
            raise RuntimeError(
                f"No .md objects at s3://{bucket}/{(raw_prefix or '')!r} — check prefix, suffix, and IAM permissions.",
            )
        logger.info("staged %d markdown file(s) from s3://%s/…", n, bucket)
        yield root
