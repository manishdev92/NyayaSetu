"""
Extract plain text from uploaded files for the legal pipeline (PDF text layer, .txt, optional image OCR).
Image OCR is off by default; set `INGEST_OCR_PROVIDER` (see `document_ocr.py`, `docs/OCR_AND_AWS.md`).
"""

from __future__ import annotations

import io
from pathlib import Path

from app.config import settings


# Stable client/i18n keys; keep in sync with `docs/ROADMAP_TRACKER.md` (P1-02).
INGEST_FILE_TOO_LARGE = "ingest_file_too_large"
INGEST_IMAGE_NO_OCR = "ingest_image_no_ocr"
INGEST_UNSUPPORTED_TYPE = "ingest_unsupported_type"
INGEST_OCR_FAILED = "ingest_ocr_failed"
INGEST_OCR_NOT_CONFIGURED = "ingest_ocr_not_configured"

IMAGE_FILE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".jfif",
    ".webp",
    ".gif",
    ".heic",
    ".bmp",
    ".tiff",
    ".tif",
)


class DocumentIngestError(ValueError):
    """User-facing extract failure with a machine-readable `code` for the API layer."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _ext(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def extract_text_from_bytes(
    filename: str | None,
    data: bytes,
    *,
    max_bytes: int | None = None,
    max_pages: int | None = None,
) -> tuple[str, str, str | None]:
    """
    Returns (text, format_slug, warning_or_none).
    """
    cap = max_bytes if max_bytes is not None else settings.max_upload_bytes
    if len(data) > cap:
        raise DocumentIngestError(
            INGEST_FILE_TOO_LARGE,
            f"File exceeds maximum size of {cap // 1_000_000} MB",
        )

    ext = _ext(filename)
    if ext in (".txt", ".md", ".text"):
        text = data.decode("utf-8", errors="replace").strip()
        return (text, "text", None if text else "Empty file")

    if ext == ".pdf":
        return _extract_pdf(data, max_pages=max_pages or settings.max_pdf_pages_extract)

    if ext in IMAGE_FILE_EXTENSIONS:
        prov = (settings.ingest_ocr_provider or "none").strip().lower()
        if prov in ("openai", "textract", "tesseract"):
            from app.services.document_ocr import run_image_ocr

            text, warn = run_image_ocr(data, ext)
            text = text.strip()
            if not text:
                w = warn or (
                    "OCR produced no readable text. Try a clearer photo, a brighter scan, or paste the text."
                )
                return ("", "image", w)
            return (text, "image", warn)
        raise DocumentIngestError(
            INGEST_IMAGE_NO_OCR,
            "Image files are not read with OCR in this version. Please describe the issue in text, "
            "or upload a PDF that has a selectable text layer (not a photo scan), or paste the text.",
        )

    if not ext and _looks_like_pdf(data):
        return _extract_pdf(data, max_pages=max_pages or settings.max_pdf_pages_extract)

    raise DocumentIngestError(
        INGEST_UNSUPPORTED_TYPE,
        f"Unsupported file type {ext!r}. Use .pdf (text-based), .txt, or .md.",
    )


def _looks_like_pdf(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == b"%PDF"


def _extract_pdf(
    data: bytes,
    *,
    max_pages: int,
) -> tuple[str, str, str | None]:
    from pypdf import PdfReader  # type: ignore[import-untyped]

    reader = PdfReader(io.BytesIO(data))
    n = min(len(reader.pages), max(1, max_pages))
    parts: list[str] = []
    for i in range(n):
        t = reader.pages[i].extract_text() or ""
        t = t.strip()
        if t:
            parts.append(t)
    text = "\n\n".join(parts).strip()
    if not text:
        prov = (settings.ingest_ocr_provider or "none").strip().lower()
        max_ocr = int(getattr(settings, "ingest_ocr_pdf_max_pages", 3))
        if prov in ("openai", "textract", "tesseract") and max_ocr > 0:
            from app.services.document_ocr import ocr_pdf_raster_pages

            try:
                ocr_text, ocr_warn = ocr_pdf_raster_pages(data, max_pages=max_ocr)
            except DocumentIngestError:
                raise
            except Exception as e:
                return (
                    "",
                    "pdf",
                    "No extractable text (often a scanned image PDF). Raster OCR failed: "
                    f"{e!s}. Add a description or use a PDF with a text layer.",
                )
            ocr_text = ocr_text.strip()
            if ocr_text:
                return (ocr_text, "pdf", ocr_warn)
        # Keep in sync with `ingestWarningNoTextPdf` + `INGEST_SERVER_WARN_NO_TEXT_PDF` in `frontend/lib/i18n.ts` (P3-02 / P5-01).
        return (
            "",
            "pdf",
            "No extractable text (often a scanned image PDF). Add a text description or use a PDF with a text layer.",
        )
    return (text, "pdf", None)
