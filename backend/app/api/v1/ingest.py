"""Upload → extract text (for pasting into the legal chat)."""

from __future__ import annotations

from fastapi import APIRouter, File, Header, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.generate_schemas import UsageInfoOut
from app.services.document_ingest import (
    INGEST_FILE_TOO_LARGE,
    DocumentIngestError,
    extract_text_from_bytes,
)
from app.services.usage_limit import UsageSnapshot, consume_request, http_rate_limit_headers

router = APIRouter()


class IngestDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    extracted_text: str
    filename: str
    format: str = Field(description="pdf | text")
    warning: str | None = None
    usage: UsageInfoOut


def _usage_from_snap(snap: UsageSnapshot) -> UsageInfoOut:
    return UsageInfoOut(
        used=snap.used,
        limit=snap.limit,
        remaining=snap.remaining,
        reset_at_utc=snap.reset_at_utc,
    )


@router.post("/ingest-document", response_model=IngestDocumentResponse)
async def ingest_document(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="PDF (text layer) or .txt / .md"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> IngestDocumentResponse:
    """Same daily usage policy as /generate; returns extracted text for the client to put in `user_input`."""
    client_ip = request.client.host if request.client else None
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    ok, usage_snap = consume_request(user_id=uid, client_ip=client_ip)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily request limit reached. Sign in for a higher limit, or try again tomorrow.",
                "error_code": "ingest_rate_limited",
            },
            headers=http_rate_limit_headers(usage_snap),
        )
    for hk, hv in http_rate_limit_headers(usage_snap).items():
        response.headers[hk] = hv

    data = await file.read()
    name = file.filename or "upload"
    try:
        text, fmt, warn = extract_text_from_bytes(name, data)
    except DocumentIngestError as e:
        status = 413 if e.code == INGEST_FILE_TOO_LARGE else 422
        raise HTTPException(
            status_code=status,
            detail={"message": str(e), "error_code": e.code},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"message": f"Could not read file: {e!s}", "error_code": "ingest_read_failed"},
        ) from e

    if len(text) > 120_000:
        text = text[:120_000] + "\n\n[… truncated for length …]"

    return IngestDocumentResponse(
        extracted_text=text,
        filename=name,
        format=fmt,
        warning=warn,
        usage=_usage_from_snap(usage_snap),
    )
