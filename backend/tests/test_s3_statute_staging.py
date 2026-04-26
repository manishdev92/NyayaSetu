"""S3 URI parsing and list-prefix safety for statute ingest (no network)."""

from __future__ import annotations

import pytest

from app.rag.ingest.s3_statute_staging import (
    _key_to_dest_path,
    _list_prefix_for_api,
    parse_s3_uri,
    staged_s3_prefix_for_ingest,
)


def test_parse_s3_uri() -> None:
    assert parse_s3_uri("s3://my-bucket/ingest/v1") == ("my-bucket", "ingest/v1")
    assert parse_s3_uri("  s3://B/a/b/c/  ") == ("B", "a/b/c/")
    assert parse_s3_uri("S3://x/onlykey.md") == ("x", "onlykey.md")
    with pytest.raises(ValueError):
        parse_s3_uri("https://x/")


def test_list_prefix_for_api() -> None:
    assert _list_prefix_for_api("") is None
    assert _list_prefix_for_api("acts") == "acts/"
    assert _list_prefix_for_api("acts/") == "acts/"
    assert _list_prefix_for_api("a.md") == "a.md"


def test_key_to_dest_path() -> None:
    d = __import__("pathlib").Path("/tmp")
    p = _key_to_dest_path("ingest/v1/foo.md", "ingest/v1/", d)
    assert p == d / "foo.md"
    p2 = _key_to_dest_path("x.md", "x.md", d)
    assert p2.name == "x.md"


def test_staged_refuses_whole_bucket_prefix() -> None:
    with pytest.raises(ValueError, match="no object prefix"):
        with staged_s3_prefix_for_ingest("s3://some-bucket"):
            pass  # pragma: no cover
