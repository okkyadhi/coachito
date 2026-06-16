"""POST /uploads/logo/sign — returns a presigned POST policy.

The FE pickup is:
  1. POST /uploads/logo/sign with desired Content-Type + size → policy.
  2. POST FormData(fields..., file) to the returned URL directly.
  3. PATCH /workspaces/me with the returned ``public_url`` as ``logo_url``.

Step 3 triggers a server-side HEAD to confirm the object actually exists at
the size/type we signed for — defence against a malicious client persisting a
URL that points at someone else's bucket.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.deps import get_current_user_id, get_current_workspace_id

from .s3 import presign_put

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Whitelist mirrors the FE accept= attribute.
ALLOWED_CONTENT_TYPES: set[str] = {"image/png", "image/jpeg", "image/webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB per spec
PRESIGN_TTL_SECONDS = 600


class LogoSignIn(BaseModel):
    content_type: Literal["image/png", "image/jpeg", "image/webp"]
    content_length: int = Field(gt=0, le=MAX_LOGO_BYTES)


class LogoSignOut(BaseModel):
    url: str
    fields: dict[str, str]
    public_url: str
    key: str
    expires_at: datetime


@router.post("/logo/sign", response_model=LogoSignOut)
async def sign_logo_upload(
    body: LogoSignIn,
    _user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
) -> LogoSignOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active workspace."
        )
    if body.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type.",
        )

    # Path layout: workspaces/<id>/logo/<uuid>.<ext>.  UUID avoids cache
    # bleed-over when a workspace replaces its logo.
    ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }[body.content_type]
    key = f"workspaces/{workspace_id}/logo/{uuid4()}.{ext}"

    policy = await run_in_threadpool(
        presign_put,
        key=key,
        content_type=body.content_type,
        max_bytes=MAX_LOGO_BYTES,
        expires_in=PRESIGN_TTL_SECONDS,
    )

    return LogoSignOut(
        url=policy["url"],
        fields=policy["fields"],
        public_url=policy["public_url"],
        key=policy["key"],
        expires_at=datetime.now(UTC) + timedelta(seconds=PRESIGN_TTL_SECONDS),
    )
