"""RAG pipeline observability (NS-S5-01): PII-safe log line with query hash and scores."""

import json
import logging
import re

import pytest

from app.ai import rag_pipeline as rp


def test_query_hash_pii_safe_deterministic() -> None:
    a = "My name is Jane Doe, phone 9999"
    assert rp._query_hash(a) == rp._query_hash(a)
    assert len(rp._query_hash(a)) == 20
    assert re.match(r"^[0-9a-f]{20}$", rp._query_hash(a))
    assert rp._query_hash(a) != rp._query_hash("different")

    msg = f"x {rp._query_hash(a)} y"
    assert "Jane" not in msg and "9999" not in msg and "Doe" not in msg


def test_rag_log_empty_pool_no_pii_in_message(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rp, "load_knowledge_entries", lambda: [{"domain": "civil"}])
    monkeypatch.setattr(rp, "filter_entries_by_issue_type", lambda raw, it: [])

    secret = "SECRET_USER_NAME_98765_not_in_logs"
    with caplog.at_level(logging.INFO, logger="app.ai.rag_pipeline"):
        out = rp.run_strict_rag_pipeline(secret, "police", top_k=3)
    assert out["grounding_label"] == "no_match"
    combined = " ".join(r.getMessage() for r in caplog.records)
    assert "SECRET_USER_NAME" not in combined
    assert "98765" not in combined
    m = re.search(r"rag_pipeline (\{.+\})\s*$", next(r for r in caplog.messages if "rag_pipeline {" in r))
    assert m, "expected JSON after rag_pipeline"
    p = json.loads(m.group(1))
    assert p["query_hash"] == rp._query_hash(secret)
    assert p["grounding_label"] == "no_match"
    assert p["pool_size"] == 0
    assert p["top_scores"] == []


def test_rag_log_full_path_has_grounding_and_top_scores(
    caplog: pytest.LogCaptureFixture,
) -> None:
    q = "civil_court_petition_filing_abcdef_unique_string"
    with caplog.at_level(logging.INFO, logger="app.ai.rag_pipeline"):
        r = rp.run_strict_rag_pipeline(q, "general", top_k=2)
    line = next((x for x in caplog.messages if "rag_pipeline {" in x and "query_hash" in x), "")
    m = re.search(r"rag_pipeline (\{.+\})\s*$", line)
    assert m
    p = json.loads(m.group(1))
    assert p["grounding_label"] == r["grounding_label"]
    assert p["issue_type"] == "general"
    assert p["query_hash"] == rp._query_hash(q)
    assert p["n_retrieved"] == len(r["retrieved_laws"])
    assert p["grounding_label"] in ("rag_retrieved", "general_not_case_specific", "no_match")
    assert "top_scores" in p
    if p["n_retrieved"] == 0:
        return
    # Log top-k window matches pipeline ranking length (≤ top_k)
    assert len(p["top_scores"]) <= 2
    assert "abcdef" not in line
