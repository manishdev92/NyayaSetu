"""P4-2 / P4-5: section chunker (no network)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from app.rag.ingest.chunker import _split_by_section_heads, chunk_statute_text
from app.rag.ingest.sources.local_markdown import (
    LocalMarkdownDirectorySource,
    parse_yaml_like_frontmatter,
)
from app.rag.ingest.pipeline import build_entries_for_document

pytestmark = pytest.mark.rag


def test_parse_frontmatter() -> None:
    raw = "---\nact_id: x-1\nsource_url: https://ex.example/\n---\n\nBody here.\n"
    fm, body = parse_yaml_like_frontmatter(raw)
    assert fm.get("act_id") == "x-1"
    assert "Body here" in body


def test_split_sections_fixture_style() -> None:
    t = (
        "Section 1. A.\nOne two.\n\n"
        "Section 2. B.\nThree four.\n"
    )
    blocks = _split_by_section_heads(t)
    assert len(blocks) == 2
    assert "Section 1" in (blocks[0][0] or "")


def test_chunk_respects_max_chars() -> None:
    long_body = "word " * 2_000
    t = f"Section 1.\n{long_body}\n"
    ch = chunk_statute_text(t, max_chunk_chars=400, overlap_chars=50)
    assert len(ch) >= 2
    assert all(len(c["text"]) <= 500 for c in ch)


def test_local_source_and_pipeline_metadata(tmp_path) -> None:
    p = tmp_path / "a.md"
    p.write_text(
        "---\n"
        "act_id: t-act\n"
        "source_url: https://www.indiacode.nic.in/x\n"
        "source_name: T\n"
        "source_version: 1.2.3\n"
        "---\n"
        "Section 1. Title.\nHello.\n",
        encoding="utf-8",
    )
    src = LocalMarkdownDirectorySource(tmp_path, recursive=False)
    docs = list(src.iter_documents())
    assert len(docs) == 1
    d = docs[0]
    rows = build_entries_for_document(
        d,
        ingested_at="2026-01-01T00:00:00Z",
        max_chunk_chars=2_000,
        overlap_chars=200,
    )
    assert len(rows) >= 1
    r0 = rows[0]
    assert r0["act_id"] == "t-act"
    assert r0.get("ingested_at") == "2026-01-01T00:00:00Z"
    assert r0.get("source_version") == "1.2.3"
    assert len(r0.get("content_sha256") or "") == 64


def test_fixtures_sample_act_yields_entries() -> None:
    here = Path(__file__).resolve().parent / "fixtures" / "ingest_statutes"
    src = LocalMarkdownDirectorySource(here, recursive=False)
    docs = list(src.iter_documents())
    assert len(docs) == 1
    assert docs[0]["meta"].get("act_id") == "p4-fixture-test-act"
    rows = build_entries_for_document(
        docs[0],
        ingested_at="2026-01-01T00:00:00Z",
        max_chunk_chars=2_000,
        overlap_chars=200,
    )
    assert len(rows) >= 2


def test_ingest_statutes_cli_dry_run() -> None:
    root = Path(__file__).resolve().parent / "fixtures" / "ingest_statutes"
    backend = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "app.rag.jobs.ingest_statutes", "--path", str(root), "--dry-run"],
        cwd=str(backend),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "n_chunks" in r.stdout
