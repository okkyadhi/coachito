"""POST /uploads/avatar/sign — presigned POST policy for user avatars.

Mirrors /uploads/logo/sign but keyed under users/<id>/avatar/ so a
workspace-less trainee can still upload their own picture.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.deps import get_current_user_id

from .s3 import presign_put

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_CONTENT_TYPES: set[str] = {"image/png", "image/jpeg", "image/webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB
PRESIGN_TTL_SECONDS = 600


class AvatarSignIn(BaseModel):
    content_type: Literal["image/png", "image/jpeg", "image/webp"]
    content_length: int = Field(gt=0, le=MAX_AVATAR_BYTES)


class AvatarSignOut(BaseModel):
    url: str
    fields: dict[str, str]
    public_url: str
    key: str
    expires_at: datetime


@router.post("/avatar/sign", response_model=AvatarSignOut)
async def sign_avatar_upload(
    body: AvatarSignIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> AvatarSignOut:
    if body.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type.",
        )
    ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }[body.content_type]
    key = f"users/{user_id}/avatar/{uuid4()}.{ext}"

    policy = await run_in_threadpool(
        presign_put,
        key=key,
        content_type=body.content_type,
        max_bytes=MAX_AVATAR_BYTES,
        expires_in=PRESIGN_TTL_SECONDS,
    )
    return AvatarSignOut(
        url=policy["url"],
        fields=policy["fields"],
        public_url=policy["public_url"],
        key=policy["key"],
        expires_at=datetime.now(UTC) + timedelta(seconds=PRESIGN_TTL_SECONDS),
    )
