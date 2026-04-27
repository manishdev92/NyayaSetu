"""P8-02 — lightweight thumbs feedback capture for post-response UX analytics."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.response_feedback_store import submit_response_feedback, summarize_feedback

router = APIRouter()


class ResponseFeedbackIn(BaseModel):
    helpful: bool
    client_mode: str = Field(..., min_length=1, max_length=24)
    task_type: str = Field(..., min_length=1, max_length=40)
    locale: str | None = Field(default=None, max_length=16)
    generation_mode: str | None = Field(default=None, max_length=80)


@router.post("/feedback/response")
def post_response_feedback(
    body: ResponseFeedbackIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, bool | str]:
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else None
    try:
        row = submit_response_feedback(
            clerk_user_id=uid,
            helpful=body.helpful,
            client_mode=body.client_mode,
            task_type=body.task_type,
            locale=body.locale,
            generation_mode=body.generation_mode,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": str(e), "error_code": "feedback_invalid_payload"},
        ) from e
    return {"ok": True, "id": str(row["id"])}


@router.get("/feedback/summary")
def get_feedback_summary(days: int = 30) -> dict[str, object]:
    return summarize_feedback(days=days)

