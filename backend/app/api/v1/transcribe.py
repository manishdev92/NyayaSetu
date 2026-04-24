"""Speech → text via OpenAI Whisper (for pasting into legal chat)."""

from __future__ import annotations

import io
import re
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, Response, UploadFile
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.generate_schemas import UsageInfoOut
from app.config import settings
from app.services.usage_limit import UsageSnapshot, consume_request, http_rate_limit_headers

router = APIRouter()

# Align with practical browser clips; Whisper supports up to ~25 MB
MAX_AUDIO_BYTES = 8_000_000


class TranscribeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    usage: UsageInfoOut


def _usage_from_snap(snap: UsageSnapshot) -> UsageInfoOut:
    return UsageInfoOut(
        used=snap.used,
        limit=snap.limit,
        remaining=snap.remaining,
        reset_at_utc=snap.reset_at_utc,
    )


def _normalize_response_language(raw: str | None) -> str:
    s = (raw or "en").strip().lower().replace("-", "_")
    if s in ("hi", "hin"):
        return "hi"
    if s == "hi_latn":
        return "hi_latn"
    return "en"


def _whisper_language_param(response_language: str) -> str | None:
    """Optional ISO-639-1 hint; None lets Whisper auto-detect."""
    rl = _normalize_response_language(response_language)
    if rl in ("hi", "hi_latn"):
        return "hi"
    if rl == "en":
        return "en"
    return None


def _safe_filename(name: str | None) -> str:
    base = (name or "recording").strip() or "recording"
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)[:120]
    if not base.lower().endswith((".webm", ".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".oga", ".ogg", ".flac")):
        return f"{base}.webm"
    return base


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="Short voice clip (e.g. webm/opus from MediaRecorder)"),
    response_language: str = Form(default="en"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> TranscribeResponse:
    """
    Transcribe audio to plain text for the chat box. Uses the same daily usage counter as /generate and /ingest-document.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "OPENAI_API_KEY is not configured on the API.",
                "error_code": "transcribe_openai_unconfigured",
            },
        )

    client_ip = request.client.host if request.client else None
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    ok, usage_snap = consume_request(user_id=uid, client_ip=client_ip)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily request limit reached. Sign in for a higher limit, or try again tomorrow.",
                "error_code": "transcribe_rate_limited",
            },
            headers=http_rate_limit_headers(usage_snap),
        )
    for hk, hv in http_rate_limit_headers(usage_snap).items():
        response.headers[hk] = hv

    data = await file.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "message": f"Audio exceeds maximum size ({MAX_AUDIO_BYTES // 1_000_000} MB).",
                "error_code": "transcribe_file_too_large",
            },
        )
    if len(data) < 256:
        raise HTTPException(
            status_code=422,
            detail={"message": "Audio clip is too short to transcribe.", "error_code": "transcribe_audio_empty"},
        )

    fname = _safe_filename(file.filename)
    lang_hint = _whisper_language_param(response_language)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        bio = io.BytesIO(data)
        bio.name = fname
        kwargs: dict[str, Any] = {
            "model": "whisper-1",
            "file": bio,
        }
        if lang_hint:
            kwargs["language"] = lang_hint
        tr = client.audio.transcriptions.create(**kwargs)
    except Exception as e:  # noqa: BLE001
        msg = str(e).strip() or "Transcription failed"
        raise HTTPException(
            status_code=502,
            detail={"message": msg, "error_code": "transcribe_upstream_error"},
        ) from e

    text = (getattr(tr, "text", None) or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail={"message": "No speech detected in the clip.", "error_code": "transcribe_no_text"},
        )

    return TranscribeResponse(text=text[:16_000], usage=_usage_from_snap(usage_snap))
