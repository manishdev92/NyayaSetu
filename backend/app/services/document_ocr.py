"""
Image OCR for document ingest (P3-01).

Providers:
- **openai** — multimodal chat (same API key as generation); good default for dev.
- **textract** — AWS Textract `DetectDocumentText` (IAM role on ECS/Lambda; set `AWS_REGION` or `AWS_DEFAULT_REGION`).
- **tesseract** — local `tesseract` binary + `pytesseract` (install `tesseract-ocr` in the image).

Set `INGEST_OCR_PROVIDER=none` (default) to reject images as before.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

from app.config import settings
from app.services.document_ingest import (
    INGEST_OCR_FAILED,
    INGEST_OCR_NOT_CONFIGURED,
    DocumentIngestError,
)

logger = logging.getLogger(__name__)


def _prepare_rgb_jpeg(image_bytes: bytes) -> bytes:
    from PIL import Image, UnidentifiedImageError

    try:
        im = Image.open(io.BytesIO(image_bytes))
    except UnidentifiedImageError as e:
        raise DocumentIngestError(
            INGEST_OCR_FAILED,
            f"Could not open image (unsupported or corrupt file): {e!s}",
        ) from e
    if getattr(im, "n_frames", 1) > 1:
        try:
            im.seek(0)
        except EOFError:
            pass
    try:
        im = im.convert("RGB")
    except OSError as e:
        raise DocumentIngestError(
            INGEST_OCR_FAILED,
            f"Could not decode image pixels: {e!s}",
        ) from e
    edge = int(settings.ingest_ocr_max_long_edge_px)
    im.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()


def _ocr_openai(jpeg_bytes: bytes) -> str:
    if not settings.openai_api_key.strip():
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            "INGEST_OCR_PROVIDER=openai requires OPENAI_API_KEY.",
        )
    from openai import OpenAI

    b64 = base64.standard_b64encode(jpeg_bytes).decode("ascii")
    model = (settings.ingest_ocr_openai_model or settings.openai_model or "gpt-4o-mini").strip()
    client = OpenAI(api_key=settings.openai_api_key.strip())
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You transcribe document and notice images into plain text only. "
                        "Preserve obvious line breaks. No preamble or commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all visible text from this image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ],
                },
            ],
            max_tokens=int(settings.ingest_ocr_openai_max_tokens),
        )
    except Exception as e:
        logger.warning("openai_ocr_failed: %s", e)
        raise DocumentIngestError(
            INGEST_OCR_FAILED,
            f"OpenAI OCR failed: {e!s}",
        ) from e
    choice = resp.choices[0] if resp.choices else None
    raw = (choice.message.content if choice and choice.message else None) or ""
    return str(raw).strip()


def _ocr_textract(jpeg_bytes: bytes) -> str:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as e:
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            "INGEST_OCR_PROVIDER=textract requires boto3 (install backend requirements).",
        ) from e

    region = settings.aws_region.strip() or None
    try:
        client = boto3.client("textract", region_name=region)
        resp: dict[str, Any] = client.detect_document_text(Document={"Bytes": jpeg_bytes})
    except (BotoCoreError, ClientError) as e:
        logger.warning("textract_ocr_failed: %s", e)
        raise DocumentIngestError(
            INGEST_OCR_FAILED,
            f"AWS Textract failed: {e!s}",
        ) from e
    lines: list[str] = []
    for block in resp.get("Blocks") or []:
        if block.get("BlockType") == "LINE" and block.get("Text"):
            lines.append(str(block["Text"]).strip())
    return "\n".join(lines).strip()


def _ocr_tesseract(jpeg_bytes: bytes) -> str:
    import shutil

    if not shutil.which("tesseract"):
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            "INGEST_OCR_PROVIDER=tesseract requires the `tesseract` binary on PATH (e.g. apt install tesseract-ocr).",
        )
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            "INGEST_OCR_PROVIDER=tesseract requires pytesseract and Pillow.",
        ) from e

    im = Image.open(io.BytesIO(jpeg_bytes))
    lang = (settings.ingest_ocr_tesseract_lang or "eng").strip() or "eng"
    try:
        text = pytesseract.image_to_string(im, lang=lang)
    except pytesseract.TesseractNotFoundError as e:
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            "Tesseract executable not found. Install tesseract-ocr and ensure it is on PATH.",
        ) from e
    except Exception as e:
        logger.warning("tesseract_ocr_failed: %s", e)
        raise DocumentIngestError(
            INGEST_OCR_FAILED,
            f"Tesseract OCR failed: {e!s}",
        ) from e
    return (text or "").strip()


def ocr_pdf_raster_pages(pdf_bytes: bytes, *, max_pages: int) -> tuple[str, str | None]:
    """
    When a PDF has no text layer, rasterize the first `max_pages` pages and run `run_image_ocr` per page (P3-03).
    Requires PyMuPDF (`pymupdf`).
    """
    try:
        import fitz  # type: ignore[import-untyped]
    except ImportError as e:
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            "Scanned-PDF OCR requires pymupdf (install backend requirements).",
        ) from e

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = min(len(doc), max(1, max_pages))
    parts: list[str] = []
    warns: list[str] = []
    mat = fitz.Matrix(2.0, 2.0)
    try:
        for i in range(n):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png = pix.tobytes("png")
            text, w = run_image_ocr(png, ".png")
            text = (text or "").strip()
            if text:
                parts.append(text)
            if w:
                warns.append(w)
    finally:
        doc.close()

    merged = "\n\n".join(parts).strip()
    warn: str | None = "; ".join(warns) if warns else None
    return merged, warn


def run_image_ocr(image_bytes: bytes, ext: str) -> tuple[str, str | None]:
    """
    Run configured OCR on raw image bytes. Returns (text, optional_warning).
    Raises DocumentIngestError for configuration or hard failures.
    """
    prov = (settings.ingest_ocr_provider or "none").strip().lower()
    if prov not in ("openai", "textract", "tesseract"):
        raise DocumentIngestError(
            INGEST_OCR_NOT_CONFIGURED,
            f"Unknown INGEST_OCR_PROVIDER={prov!r}.",
        )

    jpeg = _prepare_rgb_jpeg(image_bytes)
    _ = ext  # reserved for future mime-specific paths

    if prov == "openai":
        text = _ocr_openai(jpeg)
    elif prov == "textract":
        text = _ocr_textract(jpeg)
    else:
        text = _ocr_tesseract(jpeg)

    warn: str | None = None
    if text and len(text) > 115_000:
        text = text[:115_000] + "\n\n[… truncated …]"
        warn = "OCR text was truncated to fit chat limits."
    return text, warn
