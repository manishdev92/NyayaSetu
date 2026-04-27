"""Signed-in chat threads + messages (`X-User-Id` = Clerk user id)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.chat_history_store import (
    append_message,
    create_thread,
    delete_thread,
    list_messages,
    list_threads,
    thread_exists_for_user,
    update_thread_title,
)

router = APIRouter()


def _require_user(x_user_id: str | None) -> str:
    uid = x_user_id.strip() if isinstance(x_user_id, str) and x_user_id.strip() else ""
    if not uid:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Sign in is required (send X-User-Id).",
                "error_code": "chat_history_user_required",
            },
        )
    return uid


class ThreadCreateIn(BaseModel):
    title: str | None = Field(default=None, max_length=500)


class ThreadPatchIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class MessageCreateIn(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., min_length=0, max_length=200_000)
    meta: dict[str, Any] | None = None


@router.get("/chat/threads")
def get_threads(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    uid = _require_user(x_user_id)
    return {"threads": list_threads(uid, limit=limit)}


@router.post("/chat/threads")
def post_thread(
    body: ThreadCreateIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    uid = _require_user(x_user_id)
    try:
        return create_thread(uid, title=body.title)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": str(e), "error_code": "chat_thread_invalid"},
        ) from e


@router.patch("/chat/threads/{thread_id}")
def patch_thread(
    thread_id: str,
    body: ThreadPatchIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, bool]:
    uid = _require_user(x_user_id)
    ok = update_thread_title(uid, thread_id, body.title)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"message": "Thread not found.", "error_code": "chat_thread_not_found"},
        )
    return {"ok": True}


@router.delete("/chat/threads/{thread_id}")
def remove_thread(
    thread_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, bool]:
    uid = _require_user(x_user_id)
    ok = delete_thread(uid, thread_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"message": "Thread not found.", "error_code": "chat_thread_not_found"},
        )
    return {"deleted": True}


@router.get("/chat/threads/{thread_id}/messages")
def get_messages(
    thread_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    limit: int = 500,
) -> dict[str, list[dict[str, Any]]]:
    uid = _require_user(x_user_id)
    if not thread_exists_for_user(uid, thread_id):
        raise HTTPException(
            status_code=404,
            detail={"message": "Thread not found.", "error_code": "chat_thread_not_found"},
        )
    return {"messages": list_messages(uid, thread_id, limit=limit)}


@router.post("/chat/threads/{thread_id}/messages")
def post_message(
    thread_id: str,
    body: MessageCreateIn,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    uid = _require_user(x_user_id)
    r = body.role.strip().lower()
    if r not in ("user", "assistant"):
        raise HTTPException(
            status_code=400,
            detail={"message": "role must be user or assistant", "error_code": "chat_message_bad_role"},
        )
    try:
        return append_message(uid, thread_id, role=r, content=body.content, meta=body.meta)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"message": "Thread not found.", "error_code": "chat_thread_not_found"},
        ) from None
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": str(e), "error_code": "chat_message_invalid"},
        ) from e
