"""P8-01 — Saved cases for `/dashboard` (SQLite; Clerk user via `X-User-Id`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.dashboard_cases_store import (
    create_case,
    delete_case,
    list_cases,
)

router = APIRouter()


def _require_user(x_user_id: str | None) -> str:
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else ""
    if not uid:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Sign in is required (send X-User-Id).",
                "error_code": "dashboard_user_required",
            },
        )
    return uid


class CaseCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=4000)
    result: dict[str, Any] | None = None


@router.get("/dashboard/cases")
def get_dashboard_cases(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    uid = _require_user(x_user_id)
    return {"cases": list_cases(uid, limit=limit)}


@router.post("/dashboard/cases")
def post_dashboard_case(
    body: CaseCreateIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    uid = _require_user(x_user_id)
    try:
        row = create_case(
            clerk_user_id=uid,
            title=body.title,
            summary=body.summary,
            result=body.result,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": str(e), "error_code": "dashboard_case_invalid"},
        ) from e
    return row


@router.delete("/dashboard/cases/{case_id}")
def delete_dashboard_case(
    case_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, bool]:
    uid = _require_user(x_user_id)
    ok = delete_case(uid, case_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"message": "Case not found.", "error_code": "dashboard_case_not_found"},
        )
    return {"deleted": True}
