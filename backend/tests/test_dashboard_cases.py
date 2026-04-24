"""P8-01 — `/dashboard/cases` CRUD backed by SQLite."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.dashboard_cases_store import reset_dashboard_cases_store_for_tests


@pytest.fixture(autouse=True)
def _cases_db(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    db = tmp_path / f"cases_{uuid.uuid4().hex}.sqlite"
    monkeypatch.setattr(settings, "cases_db_path", str(db), raising=False)
    reset_dashboard_cases_store_for_tests()
    yield
    reset_dashboard_cases_store_for_tests()


def test_dashboard_cases_requires_user() -> None:
    r = TestClient(app).get("/dashboard/cases")
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "dashboard_user_required"


def test_create_list_delete_case() -> None:
    c = TestClient(app)
    uid = "clerk_dashboard_test_1"
    r = c.post(
        "/dashboard/cases",
        json={"title": " Rent dispute ", "summary": "Landlord locked flat.", "result": {"document": "draft"}},
        headers={"X-User-Id": uid},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "Rent dispute"
    cid = body["id"]
    lr = c.get("/dashboard/cases", headers={"X-User-Id": uid})
    assert lr.status_code == 200
    cases = lr.json()["cases"]
    assert len(cases) == 1
    assert cases[0]["id"] == cid
    dr = c.delete(f"/dashboard/cases/{cid}", headers={"X-User-Id": uid})
    assert dr.status_code == 200
    lr2 = c.get("/dashboard/cases", headers={"X-User-Id": uid})
    assert lr2.json()["cases"] == []
