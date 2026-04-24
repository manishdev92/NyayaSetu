"""Document text extraction and ingest API shape."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.document_ingest import INGEST_IMAGE_NO_OCR, DocumentIngestError, extract_text_from_bytes


def test_extract_plain_text() -> None:
    raw = b"Hello, this is a salary dispute.\nSecond line."
    t, fmt, w = extract_text_from_bytes("note.txt", raw)
    assert fmt == "text"
    assert "salary" in t
    assert w is None


def test_reject_image_extension() -> None:
    with pytest.raises(DocumentIngestError, match="OCR") as ex:
        extract_text_from_bytes("x.png", b"\x89PNG\r\n\x1a\nfake")
    assert ex.value.code == INGEST_IMAGE_NO_OCR


def test_client_ingest_txt() -> None:
    client = TestClient(app)
    r = client.post(
        "/ingest-document",
        files={"file": ("sample.txt", io.BytesIO(b"My legal issue: unpaid rent."), "text/plain")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["format"] == "text"
    assert "unpaid" in body["extracted_text"]
    u = body.get("usage")
    assert isinstance(u, dict) and u.get("limit", 0) > 0
    assert "reset_at_utc" in u


def test_client_ingest_png_returns_error_code() -> None:
    client = TestClient(app)
    r = client.post(
        "/ingest-document",
        files={"file": ("scan.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    assert r.status_code == 422
    err = r.json()["detail"]
    assert err["error_code"] == "ingest_image_no_ocr"
    assert "message" in err and "OCR" in err["message"]


def test_client_ingest_png_with_openai_ocr_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ingest_ocr_provider", "openai", raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-fake", raising=False)

    def fake_run(_b: bytes, _ext: str) -> tuple[str, str | None]:
        return ("Section 9: Termination clause applies.", None)

    monkeypatch.setattr("app.services.document_ocr.run_image_ocr", fake_run)
    client = TestClient(app)
    r = client.post(
        "/ingest-document",
        files={"file": ("clause.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["format"] == "image"
    assert "Termination" in body["extracted_text"]


def test_client_ingest_too_large_returns_413() -> None:
    client = TestClient(app)
    r = client.post(
        "/ingest-document",
        files={"file": ("huge.txt", io.BytesIO(b"x" * 2_200_000), "text/plain")},
    )
    assert r.status_code == 413
    err = r.json()["detail"]
    assert err["error_code"] == "ingest_file_too_large"


def test_extract_pdf_path_with_stub_pages(monkeypatch) -> None:
    """NS-S2-03: exercise PDF branch without a binary fixture (pypdf is stubbed)."""

    class Pg:
        def __init__(self, t: str) -> None:
            self._t = t

        def extract_text(self) -> str:
            return self._t

    class FakeReader:
        def __init__(self, _b: bytes) -> None:
            self.pages = [Pg("  Salary not paid  ")]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)
    t, fmt, w = extract_text_from_bytes("x.pdf", b"%PDF-1.4\n")
    assert fmt == "pdf" and "Salary" in t and w is None


def test_pdf_empty_text_uses_raster_ocr_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    class Pg:
        def extract_text(self) -> str:
            return ""

    class FakeReader:
        def __init__(self, _b: bytes) -> None:
            self.pages = [Pg()]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)
    monkeypatch.setattr(settings, "ingest_ocr_provider", "openai", raising=False)
    monkeypatch.setattr(settings, "ingest_ocr_pdf_max_pages", 2, raising=False)

    def fake_raster(_data: bytes, *, max_pages: int) -> tuple[str, str | None]:
        assert max_pages == 2
        return ("Scanned page line one", None)

    monkeypatch.setattr("app.services.document_ocr.ocr_pdf_raster_pages", fake_raster)
    t, fmt, w = extract_text_from_bytes("scan.pdf", b"%PDF-1.4\n")
    assert fmt == "pdf" and "Scanned" in t and w is None
