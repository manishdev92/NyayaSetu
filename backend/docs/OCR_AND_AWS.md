# Image OCR for ingest (P3-01)

Uploads of **PNG, JPEG, WebP, GIF,** etc. are rejected unless OCR is enabled.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `INGEST_OCR_PROVIDER` | `none` | `none` \| `openai` \| `textract` \| `tesseract` |
| `INGEST_OCR_MAX_LONG_EDGE_PX` | `2000` | Downscale longest side before OCR (cost / memory cap). |
| `INGEST_OCR_OPENAI_MODEL` | `gpt-4o-mini` | Vision-capable OpenAI model when `openai` provider is used. |
| `INGEST_OCR_OPENAI_MAX_TOKENS` | `2048` | Max completion tokens for OpenAI OCR. |
| `INGEST_OCR_TESSERACT_LANG` | `eng` | Tesseract `-l` argument (e.g. `eng+hin` if traineddata installed). |
| `INGEST_OCR_PDF_MAX_PAGES` | `3` | When a PDF has **no text layer**, rasterize up to this many pages and OCR each (0 = skip raster OCR). Capped at 20. Requires **`pymupdf`** (see `requirements.txt`). |
| `OPENAI_API_KEY` | — | Required when `INGEST_OCR_PROVIDER=openai`. |
| `AWS_REGION` or `AWS_DEFAULT_REGION` | — | Optional; passed to boto3 for Textract. You can set `AWS_REGION` in `.env` (see `app.config` field `aws_region`). |

`GET /config` includes **`ingest_ocr_provider`** and **`ingest_ocr_ready`** (heuristic: OpenAI key present for `openai`; `textract` always “ready” at config time; `tesseract` checks for `tesseract` on `PATH`).

## AWS (Textract on ECS / Lambda)

1. Enable **`INGEST_OCR_PROVIDER=textract`** on the API service.
2. Attach an IAM policy allowing **`textract:DetectDocumentText`** (resource `*` is usual for this API).
3. Use a **task role** (ECS) or **execution role** appropriate to your pattern; prefer **task role** for runtime credentials (no static keys in the container).
4. Set **`AWS_REGION`** (e.g. `ap-south-1`) to match where you run Textract.
5. **Costs:** Textract charges per page/sync call; image ingest maps to one synchronous document call per upload.

For high volume, consider **asynchronous** Textract APIs + S3 — not implemented in this repo slice.

## OpenAI (simplest for dev)

`INGEST_OCR_PROVIDER=openai` with a valid **`OPENAI_API_KEY`**. Images are resized/JPEG-compressed server-side, then sent as a data URL to the chat completions API.

## Tesseract (self-hosted / custom AMI)

1. Install **`tesseract-ocr`** (and optional language packs) in the image or host.
2. `INGEST_OCR_PROVIDER=tesseract`
3. Docker example (add to your Dockerfile when using this provider):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
```

## Scanned PDFs (P3-03)

**Image uploads** use OCR when `INGEST_OCR_PROVIDER` is not `none`. **PDFs** still use **pypdf** text extraction first; if every page is empty **and** OCR is enabled **and** `INGEST_OCR_PDF_MAX_PAGES` is greater than 0, the API **rasterizes** up to that many pages with **PyMuPDF** and runs the same OCR path as images (`document_ocr.ocr_pdf_raster_pages`). For very large or sensitive PDFs, keep the page cap low or use `0` to disable raster OCR.
