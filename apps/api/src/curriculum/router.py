"""Curriculum API — skills enable/disable, tier renaming, coach feedback inbox.

Override-row pattern (for skill enable/disable):

The ``skills`` table already supports per-workspace shadowing — a row with
the same ``(sport_id, code)`` but ``workspace_id`` set takes precedence over
the platform row.  We use ``INSERT … ON CONFLICT DO UPDATE`` to upsert the
override atomically.

The list query is a LEFT JOIN platform→override so the FE sees one row per
platform skill with the *effective* ``is_enabled`` from the override (if any)
and a boolean flag indicating override presence.  This is the correct way to
read curriculum even when overrides exist — the existing ``GET /skills`` is
naive and will be migrated to this pattern in a follow-up.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.service import write_audit_log
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import SportError, resolve_sport_id

from .permissions import (
    require_curriculum_admin,
    require_feedback_sender,
    require_workspace_member,
)
from .schemas import (
    CurriculumSkillsOut,
    CurriculumTiersOut,
    FeedbackInboxOut,
    FeedbackNoteIn,
    FeedbackNoteOut,
    SkillEnabledIn,
    SkillImpactOut,
    SkillRowOut,
    TierContextOut,
    TierNamesPatch,
    TierOut,
    TierRequirementOut,
)

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


# ── GET /curriculum/skills ──────────────────────────────────────────


@router.get("/skills", response_model=CurriculumSkillsOut)
async def list_curriculum_skills(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> CurriculumSkillsOut:
    """Merged platform+override view: one row per platform skill, with the
    workspace's effective enable state.  Sport-scoped — defaults to the
    workspace's single active sport when ``sport_id`` is omitted."""
    await require_workspace_member(db, user_id, workspace_id)
    try:
        sid = await resolve_sport_id(
            db, workspace_id=workspace_id, sport_id=sport_id
        )
    except SportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    # The audit-log subquery exposes "when was this skill last touched by
    # admin?" within a 7-day window.  Used by the FE to badge recently
    # changed skills so coaches notice curriculum drift between visits.
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    s.id, s.code, s.category, s.name_en, s.name_id,
                    s.description_en, s.description_id, s.display_order,
                    COALESCE(o.is_enabled, s.is_enabled) AS is_enabled,
                    (o.id IS NOT NULL) AS is_override,
                    ch.last_changed_at
                FROM skills s
                LEFT JOIN skills o
                    ON o.sport_id = s.sport_id
                   AND o.code = s.code
                   AND o.workspace_id = :wid
                LEFT JOIN (
                    SELECT entity_id, MAX(created_at) AS last_changed_at
                    FROM audit_log
                    WHERE workspace_id = :wid
                      AND entity_type = 'skill'
                      AND action LIKE 'curriculum.%'
                      AND created_at > NOW() - INTERVAL '7 days'
                    GROUP BY entity_id
                ) ch ON ch.entity_id = s.id
                WHERE s.sport_id = :sid
                  AND s.workspace_id IS NULL
                ORDER BY s.display_order ASC, s.code ASC
                """
            ),
            {"wid": workspace_id, "sid": sid},
        )
    ).mappings().all()
    return CurriculumSkillsOut(
        skills=[
            SkillRowOut(
                id=str(r["id"]),
                code=r["code"],
                category=r["category"],
                name_en=r["name_en"],
                name_id=r["name_id"],
                description_en=r["description_en"],
                description_id=r["description_id"],
                display_order=r["display_order"],
                is_enabled=bool(r["is_enabled"]),
                is_override=bool(r["is_override"]),
                last_changed_at=r["last_changed_at"],
            )
            for r in rows
        ]
    )


# ── PATCH /curriculum/skills/{code} ─────────────────────────────────


@router.patch("/skills/{code}", response_model=SkillRowOut)
async def patch_skill_enabled(
    code: str,
    body: SkillEnabledIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SkillRowOut:
    await require_curriculum_admin(db, user_id, workspace_id)

    # Look up the platform row to copy its metadata into the override.
    platform = (
        await db.execute(
            text(
                """
                SELECT id, sport_id, curriculum_id, category,
                       name_en, name_id, description_en, description_id,
                       display_order, is_enabled
                FROM skills
                WHERE code = :code
                  AND workspace_id IS NULL
                  AND sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)
                LIMIT 1
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().first()
    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {code} not found.",
        )

    # If the new value matches the platform default, drop the override row
    # rather than create one — keeps the data model tidy ("reset to platform").
    if body.is_enabled == bool(platform["is_enabled"]):
        await db.execute(
            text(
                """
                DELETE FROM skills
                WHERE code = :code
                  AND workspace_id = :wid
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    else:
        # Upsert override row.  ON CONFLICT on the full unique constraint
        # (sport_id, workspace_id, code) makes this atomic under concurrent
        # toggles.
        await db.execute(
            text(
                """
                INSERT INTO skills (
                    sport_id, curriculum_id, workspace_id, code, category,
                    name_en, name_id, description_en, description_id,
                    display_order, is_enabled
                )
                VALUES (
                    :sport_id, :curriculum_id, :wid, :code, :category,
                    :name_en, :name_id, :description_en, :description_id,
                    :display_order, :is_enabled
                )
                ON CONFLICT (sport_id, workspace_id, code) DO UPDATE
                    SET is_enabled = EXCLUDED.is_enabled
                """
            ),
            {
                "sport_id": platform["sport_id"],
                "curriculum_id": platform["curriculum_id"],
                "wid": workspace_id,
                "code": code,
                "category": platform["category"],
                "name_en": platform["name_en"],
                "name_id": platform["name_id"],
                "description_en": platform["description_en"],
                "description_id": platform["description_id"],
                "display_order": platform["display_order"],
                "is_enabled": body.is_enabled,
            },
        )

    await write_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="curriculum.skill_toggled",
        entity_type="skill",
        entity_id=platform["id"],
        metadata={"code": code, "is_enabled": body.is_enabled},
    )

    # IMPORTANT: read inside the same transaction.  `SET LOCAL` GUCs (the RLS
    # context set by db_with_rls) are bound to the transaction — committing
    # first would clear `app.current_workspace_id`, making the LEFT JOIN
    # invisible to the workspace override row and the merged view would
    # return the old platform default.  Read merged row → commit → return.
    out = await _load_skill_row(db, workspace_id, code)
    await db.commit()
    return out


async def _load_skill_row(
    db: AsyncSession, workspace_id: UUID | None, code: str
) -> SkillRowOut:
    r = (
        await db.execute(
            text(
                """
                SELECT
                    s.id, s.code, s.category, s.name_en, s.name_id,
                    s.description_en, s.description_id, s.display_order,
                    COALESCE(o.is_enabled, s.is_enabled) AS is_enabled,
                    (o.id IS NOT NULL) AS is_override,
                    ch.last_changed_at
                FROM skills s
                LEFT JOIN skills o
                    ON o.sport_id = s.sport_id
                   AND o.code = s.code
                   AND o.workspace_id = :wid
                LEFT JOIN (
                    SELECT entity_id, MAX(created_at) AS last_changed_at
                    FROM audit_log
                    WHERE workspace_id = :wid
                      AND entity_type = 'skill'
                      AND action LIKE 'curriculum.%'
                      AND created_at > NOW() - INTERVAL '7 days'
                    GROUP BY entity_id
                ) ch ON ch.entity_id = s.id
                WHERE s.code = :code
                  AND s.workspace_id IS NULL
                  AND s.sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)
                LIMIT 1
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill {code} not found."
        )
    return SkillRowOut(
        id=str(r["id"]),
        code=r["code"],
        category=r["category"],
        name_en=r["name_en"],
        name_id=r["name_id"],
        description_en=r["description_en"],
        description_id=r["description_id"],
        display_order=r["display_order"],
        is_enabled=bool(r["is_enabled"]),
        is_override=bool(r["is_override"]),
        last_changed_at=r["last_changed_at"],
    )


# ── GET /curriculum/skills/{code}/impact ────────────────────────────


@router.get("/skills/{code}/impact", response_model=SkillImpactOut)
async def get_skill_impact(
    code: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> SkillImpactOut:
    """Preflight for the disable-confirmation sheet.

    "Active" means any assessment that isn't withdrawn — covers drafts the
    coach is in the middle of, published reports the trainee is reading,
    and edited republishes.  Disabling mid-stream affects all of these.
    """
    await require_workspace_member(db, user_id, workspace_id)
    r = (
        await db.execute(
            text(
                """
                SELECT
                    COUNT(DISTINCT a.athlete_id) AS trainee_count,
                    COUNT(DISTINCT a.id)        AS assessment_count
                FROM assessment_scores sc
                JOIN assessments a ON a.id = sc.assessment_id
                JOIN skills s      ON s.id = sc.skill_id
                WHERE s.code = :code
                  AND a.workspace_id = :wid
                  AND a.status IN ('draft','published','edited')
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().first()
    in_tier = (
        await db.execute(
            text(
                """
                SELECT 1
                FROM tier_requirements tr
                JOIN skills s ON s.id = tr.skill_id
                JOIN tiers t  ON t.id = tr.tier_id
                WHERE s.code = :code
                  AND (t.workspace_id = :wid OR t.workspace_id IS NULL)
                  AND t.sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)
                LIMIT 1
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).first()
    return SkillImpactOut(
        trainee_count=int(r["trainee_count"]) if r else 0,
        assessment_count=int(r["assessment_count"]) if r else 0,
        in_tier_requirements=in_tier is not None,
    )


# ── GET /curriculum/skills/{code}/tier-context ──────────────────────


@router.get("/skills/{code}/tier-context", response_model=TierContextOut)
async def get_skill_tier_context(
    code: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TierContextOut:
    """Which tiers require this skill, at what level — for the skill detail
    screen.  Tier names are resolved server-side to the *effective* name per
    the workspace's current ``tier_style`` so the FE doesn't need to know
    the setting.
    """
    ws = await require_workspace_member(db, user_id, workspace_id)
    # Pick the effective-name column based on workspace tier_style.  CASE
    # inline so the result-shape stays consistent.
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    t.code AS tier_code,
                    t.display_order AS tier_display_order,
                    CASE :style
                        WHEN 'game'   THEN COALESCE(o.name_game_en,   t.name_game_en)
                        WHEN 'skill'  THEN COALESCE(o.name_skill_en,  t.name_skill_en)
                        WHEN 'custom' THEN COALESCE(o.name_custom_en, t.name_custom_en, t.name_skill_en)
                        ELSE t.name_skill_en
                    END AS tier_name,
                    tr.min_level
                FROM tier_requirements tr
                JOIN skills s ON s.id = tr.skill_id
                JOIN tiers  t ON t.id = tr.tier_id
                LEFT JOIN tiers o
                    ON o.sport_id = t.sport_id
                   AND o.code = t.code
                   AND o.workspace_id = :wid
                WHERE s.code = :code
                  AND s.workspace_id IS NULL
                  AND s.sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)
                ORDER BY t.display_order ASC
                """
            ),
            {"code": code, "wid": workspace_id, "style": ws.tier_style},
        )
    ).mappings().all()
    return TierContextOut(
        skill_code=code,
        requirements=[
            TierRequirementOut(
                tier_code=r["tier_code"],
                tier_display_order=r["tier_display_order"],
                tier_name=r["tier_name"],
                min_level=r["min_level"],
            )
            for r in rows
        ],
    )


# ── GET /curriculum/tiers ───────────────────────────────────────────


@router.get("/tiers", response_model=CurriculumTiersOut)
async def list_curriculum_tiers(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> CurriculumTiersOut:
    """Merged platform+override view, same shape as skills.  Sport-scoped."""
    await require_workspace_member(db, user_id, workspace_id)
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
                SELECT
                    t.id, t.code, t.display_order,
                    t.name_game_en, t.name_game_id,
                    t.name_skill_en, t.name_skill_id,
                    COALESCE(o.name_custom_en, t.name_custom_en) AS name_custom_en,
                    COALESCE(o.name_custom_id, t.name_custom_id) AS name_custom_id,
                    COALESCE(o.color_hex, t.color_hex) AS color_hex,
                    COALESCE(o.icon_name, t.icon_name) AS icon_name,
                    (o.id IS NOT NULL) AS is_override
                FROM tiers t
                LEFT JOIN tiers o
                    ON o.sport_id = t.sport_id
                   AND o.code = t.code
                   AND o.workspace_id = :wid
                WHERE t.sport_id = :sid
                  AND t.workspace_id IS NULL
                ORDER BY t.display_order ASC
                """
            ),
            {"wid": workspace_id, "sid": sid},
        )
    ).mappings().all()
    return CurriculumTiersOut(
        tiers=[
            TierOut(
                id=str(r["id"]),
                code=r["code"],
                display_order=r["display_order"],
                name_game_en=r["name_game_en"],
                name_game_id=r["name_game_id"],
                name_skill_en=r["name_skill_en"],
                name_skill_id=r["name_skill_id"],
                name_custom_en=r["name_custom_en"],
                name_custom_id=r["name_custom_id"],
                color_hex=r["color_hex"],
                icon_name=r["icon_name"],
                is_override=bool(r["is_override"]),
            )
            for r in rows
        ]
    )


# ── PATCH /curriculum/tiers/{code} ──────────────────────────────────


@router.patch("/tiers/{code}", response_model=TierOut)
async def patch_tier_names(
    code: str,
    body: TierNamesPatch,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> TierOut:
    """Override the *custom* tier name for this workspace.

    Game/Skill names stay platform-locked — switching tier_style on the
    workspace is the way to pick a different naming scheme.
    """
    await require_curriculum_admin(db, user_id, workspace_id)

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        # Nothing to do — just return the current row.
        return await _load_tier_row(db, workspace_id, code)

    platform = (
        await db.execute(
            text(
                """
                SELECT id, sport_id, curriculum_id, code, display_order,
                       name_game_en, name_game_id, name_skill_en, name_skill_id,
                       name_custom_en, name_custom_id, color_hex, icon_name
                FROM tiers
                WHERE code = :code
                  AND workspace_id IS NULL
                  AND sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)
                LIMIT 1
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().first()
    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier {code} not found.",
        )

    # Upsert the override row.  Custom name fields come from the patch where
    # provided, otherwise from the existing override (if any) or NULL.
    existing = (
        await db.execute(
            text(
                """
                SELECT name_custom_en, name_custom_id
                FROM tiers
                WHERE code = :code AND workspace_id = :wid
                LIMIT 1
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().first()

    name_custom_en = patch.get(
        "name_custom_en",
        existing["name_custom_en"] if existing else platform["name_custom_en"],
    )
    name_custom_id = patch.get(
        "name_custom_id",
        existing["name_custom_id"] if existing else platform["name_custom_id"],
    )

    await db.execute(
        text(
            """
            INSERT INTO tiers (
                sport_id, curriculum_id, workspace_id, code, display_order,
                name_game_en, name_game_id, name_skill_en, name_skill_id,
                name_custom_en, name_custom_id, color_hex, icon_name
            )
            VALUES (
                :sport_id, :curriculum_id, :wid, :code, :display_order,
                :name_game_en, :name_game_id, :name_skill_en, :name_skill_id,
                :name_custom_en, :name_custom_id, :color_hex, :icon_name
            )
            ON CONFLICT (curriculum_id, workspace_id, code) DO UPDATE
                SET name_custom_en = EXCLUDED.name_custom_en,
                    name_custom_id = EXCLUDED.name_custom_id
            """
        ),
        {
            "sport_id": platform["sport_id"],
            "curriculum_id": platform["curriculum_id"],
            "wid": workspace_id,
            "code": code,
            "display_order": platform["display_order"],
            "name_game_en": platform["name_game_en"],
            "name_game_id": platform["name_game_id"],
            "name_skill_en": platform["name_skill_en"],
            "name_skill_id": platform["name_skill_id"],
            "name_custom_en": name_custom_en,
            "name_custom_id": name_custom_id,
            "color_hex": platform["color_hex"],
            "icon_name": platform["icon_name"],
        },
    )

    await write_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="curriculum.tier_renamed",
        entity_type="tier",
        entity_id=platform["id"],
        metadata={"code": code, "changes": patch},
    )

    # Same constraint as patch_skill_enabled: SET LOCAL RLS GUCs die at commit.
    out = await _load_tier_row(db, workspace_id, code)
    await db.commit()
    return out


async def _load_tier_row(
    db: AsyncSession, workspace_id: UUID | None, code: str
) -> TierOut:
    r = (
        await db.execute(
            text(
                """
                SELECT
                    t.id, t.code, t.display_order,
                    t.name_game_en, t.name_game_id,
                    t.name_skill_en, t.name_skill_id,
                    COALESCE(o.name_custom_en, t.name_custom_en) AS name_custom_en,
                    COALESCE(o.name_custom_id, t.name_custom_id) AS name_custom_id,
                    COALESCE(o.color_hex, t.color_hex) AS color_hex,
                    COALESCE(o.icon_name, t.icon_name) AS icon_name,
                    (o.id IS NOT NULL) AS is_override
                FROM tiers t
                LEFT JOIN tiers o
                    ON o.sport_id = t.sport_id
                   AND o.code = t.code
                   AND o.workspace_id = :wid
                WHERE t.code = :code
                  AND t.workspace_id IS NULL
                  AND t.sport_id = (SELECT sport_id FROM workspaces WHERE id = :wid)
                LIMIT 1
                """
            ),
            {"code": code, "wid": workspace_id},
        )
    ).mappings().first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tier {code} not found."
        )
    return TierOut(
        id=str(r["id"]),
        code=r["code"],
        display_order=r["display_order"],
        name_game_en=r["name_game_en"],
        name_game_id=r["name_game_id"],
        name_skill_en=r["name_skill_en"],
        name_skill_id=r["name_skill_id"],
        name_custom_en=r["name_custom_en"],
        name_custom_id=r["name_custom_id"],
        color_hex=r["color_hex"],
        icon_name=r["icon_name"],
        is_override=bool(r["is_override"]),
    )


# ── POST /curriculum/feedback ───────────────────────────────────────


@router.post(
    "/feedback",
    response_model=FeedbackNoteOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_feedback_note(
    body: FeedbackNoteIn,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackNoteOut:
    await require_feedback_sender(db, user_id, workspace_id)

    skill_uuid: UUID | None = UUID(body.skill_id) if body.skill_id else None

    new_id = await db.scalar(
        text(
            """
            INSERT INTO coach_feedback_notes
                (workspace_id, author_user_id, subject_skill_id, body)
            VALUES (:wid, :uid, :skill_id, :body)
            RETURNING id
            """
        ),
        {
            "wid": workspace_id,
            "uid": user_id,
            "skill_id": skill_uuid,
            "body": body.body,
        },
    )
    out = await _load_note(db, new_id)
    await db.commit()
    return out


# ── GET /curriculum/feedback ────────────────────────────────────────


@router.get("/feedback", response_model=FeedbackInboxOut)
async def feedback_inbox(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackInboxOut:
    """Admin/owner inbox.  Non-admin members get 403 so the UI affordance
    can be cleanly gated."""
    await require_curriculum_admin(db, user_id, workspace_id)
    rows = (
        await db.execute(
            text(
                """
                SELECT n.id, n.body, n.created_at, n.read_at,
                       u.display_name AS author_name,
                       s.code AS skill_code, s.name_en AS skill_name_en
                FROM coach_feedback_notes n
                JOIN users u ON u.id = n.author_user_id
                LEFT JOIN skills s ON s.id = n.subject_skill_id
                WHERE n.workspace_id = :wid
                ORDER BY (n.read_at IS NULL) DESC, n.created_at DESC
                LIMIT 200
                """
            ),
            {"wid": workspace_id},
        )
    ).mappings().all()
    notes = [
        FeedbackNoteOut(
            id=str(r["id"]),
            author_display_name=r["author_name"],
            skill_code=r["skill_code"],
            skill_name_en=r["skill_name_en"],
            body=r["body"],
            created_at=r["created_at"],
            read_at=r["read_at"],
        )
        for r in rows
    ]
    return FeedbackInboxOut(
        notes=notes,
        unread_count=sum(1 for n in notes if n.read_at is None),
    )


# ── GET /curriculum/feedback/mine ───────────────────────────────────


@router.get("/feedback/mine", response_model=FeedbackInboxOut)
async def my_feedback_history(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackInboxOut:
    """Notes the *caller* authored.  Closes the loop for coaches who can
    otherwise see their notes vanish into the admin's inbox.  Shows
    ``read_at`` so the coach knows whether the admin has seen it.
    """
    await require_workspace_member(db, user_id, workspace_id)
    rows = (
        await db.execute(
            text(
                """
                SELECT n.id, n.body, n.created_at, n.read_at,
                       u.display_name AS author_name,
                       s.code AS skill_code, s.name_en AS skill_name_en
                FROM coach_feedback_notes n
                JOIN users u ON u.id = n.author_user_id
                LEFT JOIN skills s ON s.id = n.subject_skill_id
                WHERE n.workspace_id = :wid
                  AND n.author_user_id = :uid
                ORDER BY n.created_at DESC
                LIMIT 100
                """
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    ).mappings().all()
    notes = [
        FeedbackNoteOut(
            id=str(r["id"]),
            author_display_name=r["author_name"],
            skill_code=r["skill_code"],
            skill_name_en=r["skill_name_en"],
            body=r["body"],
            created_at=r["created_at"],
            read_at=r["read_at"],
        )
        for r in rows
    ]
    # "Unread" here means the *admin* hasn't read it yet — same shape so the
    # FE can reuse the inbox component.
    return FeedbackInboxOut(
        notes=notes,
        unread_count=sum(1 for n in notes if n.read_at is None),
    )


# ── POST /curriculum/feedback/{id}/read ─────────────────────────────


@router.post("/feedback/{note_id}/read", response_model=FeedbackNoteOut)
async def mark_feedback_read(
    note_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
) -> FeedbackNoteOut:
    await require_curriculum_admin(db, user_id, workspace_id)
    # COALESCE keeps the first read timestamp — re-marking is a no-op.
    updated = await db.scalar(
        text(
            """
            UPDATE coach_feedback_notes
            SET read_at = COALESCE(read_at, NOW())
            WHERE id = :id
            RETURNING id
            """
        ),
        {"id": note_id},
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback note not found."
        )
    out = await _load_note(db, note_id)
    await db.commit()
    return out


async def _load_note(db: AsyncSession, note_id: UUID) -> FeedbackNoteOut:
    r = (
        await db.execute(
            text(
                """
                SELECT n.id, n.body, n.created_at, n.read_at,
                       u.display_name AS author_name,
                       s.code AS skill_code, s.name_en AS skill_name_en
                FROM coach_feedback_notes n
                JOIN users u ON u.id = n.author_user_id
                LEFT JOIN skills s ON s.id = n.subject_skill_id
                WHERE n.id = :id
                LIMIT 1
                """
            ),
            {"id": note_id},
        )
    ).mappings().first()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback note not found."
        )
    return FeedbackNoteOut(
        id=str(r["id"]),
        author_display_name=r["author_name"],
        skill_code=r["skill_code"],
        skill_name_en=r["skill_name_en"],
        body=r["body"],
        created_at=r["created_at"],
        read_at=r["read_at"],
    )
