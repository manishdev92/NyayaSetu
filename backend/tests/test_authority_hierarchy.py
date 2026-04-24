from __future__ import annotations

from app.services.authority_hierarchy_service import build_authority_hierarchy


def test_criminal_police_hierarchy_police_forum_no_labour_leakage() -> None:
    steps = build_authority_hierarchy("criminal_police", "Varanasi")
    assert len(steps) >= 2
    blob = " ".join(f"{s['label']} {s['description']}" for s in steps).lower()
    assert "police" in blob or "fir" in blob
    assert "labour" not in blob
    assert "wage" not in blob
    assert "provident" not in blob


def test_salary_issue_labour_hierarchy_and_directory_varanasi() -> None:
    steps = build_authority_hierarchy("salary_issue", "Varanasi")
    assert steps
    blob = " ".join(f"{s['label']} {s['description']}" for s in steps).lower()
    assert "labour" in blob
    labour_rows = [s for s in steps if s.get("department_key") == "labour"]
    assert labour_rows
    first = labour_rows[0]
    assert first.get("verified") is True
    assert first.get("source") == "directory"
    assert first.get("office_name")
    assert "Labour" in str(first.get("office_name"))


def test_consumer_issue_not_criminal_police_template() -> None:
    criminal = build_authority_hierarchy("criminal_police", "Delhi")
    consumer = build_authority_hierarchy("consumer_issue", "Delhi")
    c_labels = " ".join(s["label"] for s in consumer).lower()
    cr_labels = " ".join(s["label"] for s in criminal).lower()
    assert "consumer" in c_labels or "e-daakhil" in " ".join(s["description"] for s in consumer).lower()
    assert "fir" not in c_labels
    assert "police station" not in c_labels
    assert "police" in cr_labels or "fir" in " ".join(s["description"] for s in criminal).lower()


def test_unknown_router_uses_general_template() -> None:
    steps = build_authority_hierarchy("totally_unknown_router_intent", None)
    assert steps
    joined = " ".join(s["description"] for s in steps).lower()
    assert ".gov.in" in joined or "official" in joined
