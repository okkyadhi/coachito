"""GET /skills (list) and GET /skills/{code}/descriptors (5-level rubric)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import SportError, resolve_sport_id

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillOut(BaseModel):
    id: str
    code: str
    category: str
    name_en: str
    name_id: str
    display_order: int


class SkillsListOut(BaseModel):
    skills: list[SkillOut]


class DescriptorOut(BaseModel):
    level: int
    description_en: str
    description_id: str


class DescriptorsOut(BaseModel):
    skill_code: str
    descriptors: list[DescriptorOut]


@router.get("", response_model=SkillsListOut)
async def list_skills(
    _: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> SkillsListOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )
    try:
        sid = await resolve_sport_id(
            db, workspace_id=workspace_id, sport_id=sport_id
        )
    except SportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    rows = (
        await db.execute(
            text(
                """
                SELECT id, code, category, name_en, name_id, display_order
                FROM skills
                WHERE sport_id = :sid
                  AND (workspace_id = :wid OR workspace_id IS NULL)
                  AND is_enabled = TRUE
                ORDER BY display_order ASC
                """
            ),
            {"wid": workspace_id, "sid": sid},
        )
    ).mappings().all()
    return SkillsListOut(
        skills=[
            SkillOut(
                id=str(r["id"]),
                code=r["code"],
                category=r["category"],
                name_en=r["name_en"],
                name_id=r["name_id"],
                display_order=r["display_order"],
            )
            for r in rows
        ]
    )


@router.get("/{code}/descriptors", response_model=DescriptorsOut)
async def get_descriptors(
    code: str,
    _: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> DescriptorsOut:
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active workspace.",
        )
    rows = (
        await db.execute(
            text(
                """
                SELECT d.level, d.description_en, d.description_id
                FROM skill_level_descriptors d
                JOIN skills s ON s.id = d.skill_id
                WHERE s.code = :code
                  AND (s.workspace_id = :wid OR s.workspace_id IS NULL)
                  AND (d.workspace_id = :wid OR d.workspace_id IS NULL)
                ORDER BY d.level ASC
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No descriptors for skill {code}.",
        )
    return DescriptorsOut(
        skill_code=code,
        descriptors=[
            DescriptorOut(
                level=r["level"],
                description_en=r["description_en"],
                description_id=r["description_id"],
            )
            for r in rows
        ],
    )
