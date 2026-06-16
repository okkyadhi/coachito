"""GET / PATCH /users/me — trainee self-service profile.

Editable: display_name, avatar_url (must be in our bucket), preferred_locale,
notifications.  DOB and parent link are admin-owned and rejected by the
schema (extra=forbid).
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.config import settings as app_settings
from src.deps import get_current_user_id
from src.middleware.rls import db_with_rls, set_user_context
from src.uploads.s3 import head_object

from .me_schemas import (
    MeOut,
    MePatch,
    NotificationsOut,
    ParentLinkOut,
)

router = APIRouter(prefix="/users", tags=["users"])


def _avatar_key_from_url(url: str) -> str | None:
    prefix = (
        f"{app_settings.s3_public_endpoint.rstrip('/')}/"
        f"{app_settings.s3_bucket}/"
    )
    if not url.startswith(prefix):
        return None
    return url[len(prefix):]


async def _load_me(db: AsyncSession, *, user_id: UUID) -> MeOut:
    row = (
        await db.execute(
            text(
                """
                SELECT u.id, u.email, u.display_name, u.avatar_url,
                       u.preferred_locale, u.is_minor, u.date_of_birth,
                       u.primary_guardian_id, u.summary_style,
                       g.display_name AS guardian_name
                FROM users u
                LEFT JOIN users g ON g.id = u.primary_guardian_id
                WHERE u.id = :uid
                """
            ),
            {"uid": user_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    prefs = (
        await db.execute(
            text(
                "SELECT session_reminders, monthly_report "
                "FROM user_notification_prefs WHERE user_id = :uid"
            ),
            {"uid": user_id},
        )
    ).mappings().first()
    notifications = NotificationsOut(
        session_reminders=bool(prefs["session_reminders"]) if prefs else True,
        monthly_report=bool(prefs["monthly_report"]) if prefs else True,
    )
    return MeOut(
        id=str(row["id"]),
        email=row["email"],
        display_name=row["display_name"],
        avatar_url=row["avatar_url"],
        preferred_locale=row["preferred_locale"] if row["preferred_locale"] in ("en", "id") else "id",
        is_minor=bool(row["is_minor"]),
        date_of_birth=row["date_of_birth"],
        primary_guardian=(
            ParentLinkOut(
                id=str(row["primary_guardian_id"]),
                display_name=row["guardian_name"],
            )
            if row["primary_guardian_id"] is not None
            else None
        ),
        notifications=notifications,
        summary_style=(
            row["summary_style"]
            if row["summary_style"] in ("encouraging", "direct", "warm")
            else "encouraging"
        ),
    )


@router.get("/me", response_model=MeOut)
async def get_me(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> MeOut:
    return await _load_me(db, user_id=user_id)


@router.patch("/me", response_model=MeOut)
async def patch_me(
    body: MePatch,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> MeOut:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return await _load_me(db, user_id=user_id)

    user_changes: dict[str, Any] = {}
    if "display_name" in patch and patch["display_name"] is not None:
        user_changes["display_name"] = patch["display_name"].strip()
    if "preferred_locale" in patch and patch["preferred_locale"] is not None:
        user_changes["preferred_locale"] = patch["preferred_locale"]
    if "summary_style" in patch and patch["summary_style"] is not None:
        user_changes["summary_style"] = patch["summary_style"]
    if "avatar_url" in patch:
        url = patch["avatar_url"]
        if url is not None:
            key = _avatar_key_from_url(url)
            if key is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="avatar_url is not a recognized storage URL.",
                )
            head = await run_in_threadpool(head_object, key)
            if head is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded avatar could not be found in storage.",
                )
            ctype = head.get("ContentType", "")
            if ctype not in ("image/png", "image/jpeg", "image/webp"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Avatar must be PNG, JPEG, or WebP.",
                )
            size = int(head.get("ContentLength", 0))
            if size <= 0 or size > 2 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Avatar must be ≤ 2 MB.",
                )
        user_changes["avatar_url"] = url

    if user_changes:
        cols = ", ".join(f"{k} = :{k}" for k in user_changes)
        await db.execute(
            text(
                f"UPDATE users SET {cols}, updated_at = NOW() WHERE id = :uid"
            ),
            {**user_changes, "uid": user_id},
        )

    if "notifications" in patch and patch["notifications"] is not None:
        n = patch["notifications"]
        sr = n.get("session_reminders")
        mr = n.get("monthly_report")
        # Lazy upsert: create the row with defaults on first write, then patch
        # only the keys the caller actually sent.  Done in two statements so
        # the ON CONFLICT path doesn't clobber the unchanged field.
        await db.execute(
            text(
                """
                INSERT INTO user_notification_prefs (user_id, session_reminders, monthly_report)
                VALUES (:uid, TRUE, TRUE)
                ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {"uid": user_id},
        )
        updates: dict[str, Any] = {"uid": user_id}
        set_parts: list[str] = []
        if sr is not None:
            updates["sr"] = sr
            set_parts.append("session_reminders = :sr")
        if mr is not None:
            updates["mr"] = mr
            set_parts.append("monthly_report = :mr")
        if set_parts:
            set_parts.append("updated_at = NOW()")
            await db.execute(
                text(
                    "UPDATE user_notification_prefs "
                    f"SET {', '.join(set_parts)} WHERE user_id = :uid"
                ),
                updates,
            )

    await db.commit()
    # SET LOCAL GUCs die at commit; reseed before the post-commit read so the
    # user_notification_prefs RLS policy still sees this user as the caller.
    await set_user_context(db, user_id)
    return await _load_me(db, user_id=user_id)
