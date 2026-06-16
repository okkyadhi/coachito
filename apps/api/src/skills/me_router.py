"""Trainee-self skills endpoints (Progress tab).

GET /skills/me/overview              → category averages over the 4 pillars
GET /skills/me/category/:code        → per-skill latest scores + descriptors
GET /skills/me/category/:code/blockers → next-tier blockers filtered to this category

All routes are self-scoped: the trainee can only see their own data. RLS on
`athletes` + `assessments` enforces this even if SQL forgot to filter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.service import recompute_tier
from src.deps import get_current_user_id, get_current_workspace_id
from src.middleware.rls import db_with_rls
from src.sports.service import resolve_sport_id

from .me_schemas import (
    CategoryBlockersOut,
    CategoryBreakdownOut,
    CategoryCode,
    CategoryScoreOut,
    FocusSuggestionOut,
    OverallProgressOut,
    RecentGainOut,
    SkillScoreOut,
    SkillsOverviewOut,
    TierBlockerEntryOut,
    TierBriefLiteOut,
    TierBriefOut,
    TierProgressOut,
)
from .me_service import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    all_skills_for_workspace,
    descriptors_for_skills,
    find_my_athlete_id,
    latest_note_for_skill,
    latest_per_skill,
    recent_gains as fetch_recent_gains,
)

router = APIRouter(prefix="/skills/me", tags=["skills", "trainees"])


def _no_workspace() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No active workspace.",
    )


def _no_trainee() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No trainee profile linked to this account.",
    )


def _validate_category(code: str) -> CategoryCode:
    if code not in CATEGORY_ORDER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown category: {code}",
        )
    return cast(CategoryCode, code)


_PRIVATE_30S = "private, max-age=30"
_PRIVATE_20S = "private, max-age=20"


@router.get("/overview", response_model=SkillsOverviewOut)
async def get_overview(
    response: Response,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> SkillsOverviewOut:
    if workspace_id is None:
        raise _no_workspace()
    resolved_sport_id = await resolve_sport_id(
        db, workspace_id=workspace_id, sport_id=sport_id
    )
    athlete_id = await find_my_athlete_id(db, user_id=user_id, workspace_id=workspace_id)
    if athlete_id is None:
        raise _no_trainee()

    all_skills = await all_skills_for_workspace(
        db, workspace_id=workspace_id, sport_id=resolved_sport_id
    )
    latest = await latest_per_skill(db, athlete_id=athlete_id, sport_id=resolved_sport_id)
    latest_by_skill = {r["skill_id"]: r for r in latest}
    cat_by_skill = {s["id"]: s["category"] for s in all_skills}

    # ── Category averages + overall ───────────────────────────────
    buckets: dict[str, list[int]] = {c: [] for c in CATEGORY_ORDER}
    totals: dict[str, int] = {c: 0 for c in CATEGORY_ORDER}
    for s in all_skills:
        totals[s["category"]] = totals.get(s["category"], 0) + 1
    all_scores: list[int] = []
    for sid, row in latest_by_skill.items():
        lvl = int(row["level"])
        cat = cat_by_skill.get(sid)
        if cat in buckets:
            buckets[cat].append(lvl)
        all_scores.append(lvl)

    updated_at = None
    for row in latest:
        if updated_at is None or (row["recorded_at"] and row["recorded_at"] > updated_at):
            updated_at = row["recorded_at"]

    categories = [
        CategoryScoreOut(
            code=cast(CategoryCode, c),
            label_en=CATEGORY_LABELS[c]["en"],
            label_id=CATEGORY_LABELS[c]["id"],
            average=(round(sum(vals) / len(vals), 1) if vals else None),
            assessed_count=len(vals),
            total_count=totals[c],
        )
        for c, vals in buckets.items()
    ]

    overall = OverallProgressOut(
        average=(round(sum(all_scores) / len(all_scores), 1) if all_scores else None),
        assessed_count=len(all_scores),
        total_count=sum(totals.values()),
        last_assessed_at=updated_at,
    )

    # ── Tier progress + blockers ──────────────────────────────────
    levels = {sid: int(row["level"]) for sid, row in latest_by_skill.items()}
    tier_info = await recompute_tier(
        db,
        workspace_id=workspace_id,
        athlete_id=athlete_id,
        levels=levels,
        sport_id=resolved_sport_id,
    )
    next_tier = tier_info["next_tier"]
    current_tier = tier_info["current_tier"]

    # Compute total blockers across categories from next tier's requirements.
    blockers_total = 0
    blocker_rows: list[dict[str, Any]] = []
    if next_tier is not None:
        req_rows = (
            await db.execute(
                text(
                    """
                    SELECT tr.skill_id, tr.min_level,
                           s.code,
                           s.category::text AS category,
                           s.name_en, s.name_id
                    FROM tier_requirements tr
                    JOIN skills s ON s.id = tr.skill_id
                    WHERE tr.tier_id = :tid
                    """
                ),
                {"tid": next_tier.id},
            )
        ).mappings().all()
        for r in req_rows:
            cur = levels.get(r["skill_id"], 0)
            if cur < r["min_level"]:
                blockers_total += 1
                blocker_rows.append({
                    "skill_id": r["skill_id"],
                    "skill_code": r["code"],
                    "category": r["category"],
                    "name_en": r["name_en"],
                    "name_id": r["name_id"],
                    "current_level": cur,
                    "required_level": int(r["min_level"]),
                })

    tier: TierProgressOut | None
    if current_tier is None and next_tier is None:
        tier = None
    else:
        met = tier_info.get("met_count") or 0
        total_reqs = tier_info.get("total_requirements") or 0
        progress = (met / total_reqs) if total_reqs > 0 else (1.0 if next_tier is None else 0.0)
        tier = TierProgressOut(
            current=(
                TierBriefOut(
                    code=current_tier.code,
                    label_en=current_tier.name_game_en,
                    label_id=current_tier.name_game_id,
                ) if current_tier is not None else None
            ),
            next=(
                TierBriefOut(
                    code=next_tier.code,
                    label_en=next_tier.name_game_en,
                    label_id=next_tier.name_game_id,
                ) if next_tier is not None else None
            ),
            blockers_remaining_count=blockers_total,
            progress_to_next=round(progress, 3),
        )

    # ── Recent gains (last 14 days, capped at 4) ──────────────────
    gain_rows = await fetch_recent_gains(db, athlete_id=athlete_id, sport_id=resolved_sport_id)
    recent: list[RecentGainOut] = [
        RecentGainOut(
            skill_code=g["code"],
            label_en=g["name_en"],
            label_id=g["name_id"],
            from_level=int(g["from_level"] or 0),
            to_level=int(g["to_level"]),
            at=g["at"],
        )
        for g in gain_rows
    ]

    # ── Focus suggestion ──────────────────────────────────────────
    focus = await _compute_focus(
        db,
        athlete_id=athlete_id,
        all_skills=all_skills,
        latest_by_skill=latest_by_skill,
        blockers=blocker_rows,
    )

    response.headers["Cache-Control"] = _PRIVATE_20S
    return SkillsOverviewOut(
        categories=categories,
        overall=overall,
        tier=tier,
        recent_gains=recent,
        focus_suggestion=focus,
        updated_at=updated_at,
    )


async def _compute_focus(
    db: AsyncSession,
    *,
    athlete_id: UUID,
    all_skills: list[dict[str, Any]],
    latest_by_skill: dict[UUID, dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> FocusSuggestionOut | None:
    """Pick one skill to spotlight: prefer the lowest-scored blocker
    (tie-break by oldest last-assessed), else the oldest unassessed skill,
    else the lowest-scored skill overall.  None only when at top tier with
    every skill maxed."""
    # 1. Blocker for next tier.
    _MIN_DT = datetime.min.replace(tzinfo=UTC)
    if blockers:
        ranked = sorted(
            blockers,
            key=lambda b: (
                b["current_level"],
                # oldest last-assessed first (None == never assessed → very old)
                latest_by_skill.get(b["skill_id"], {}).get("recorded_at") or _MIN_DT,
            ),
        )
        b = ranked[0]
        note_en, note_id = await latest_note_for_skill(
            db, athlete_id=athlete_id, skill_id=b["skill_id"]
        )
        return FocusSuggestionOut(
            skill_code=b["skill_code"],
            label_en=b["name_en"],
            label_id=b["name_id"],
            current_level=b["current_level"] or None,
            required_level=b["required_level"],
            category=cast(CategoryCode, b["category"]),
            latest_note_en=note_en,
            latest_note_id=note_id,
            reason="blocker_for_next_tier",
        )

    # 2. Oldest unassessed (= never assessed).
    unassessed = [s for s in all_skills if s["id"] not in latest_by_skill]
    if unassessed:
        s = sorted(unassessed, key=lambda x: x.get("display_order", 0))[0]
        return FocusSuggestionOut(
            skill_code=s["code"],
            label_en=s["name_en"],
            label_id=s["name_id"],
            current_level=None,
            required_level=None,
            category=cast(CategoryCode, s["category"]),
            latest_note_en=None,
            latest_note_id=None,
            reason="oldest_unassessed",
        )

    # 3. Lowest-scored skill overall.
    if latest_by_skill:
        ranked = sorted(
            all_skills,
            key=lambda s: int(latest_by_skill[s["id"]]["level"])
            if s["id"] in latest_by_skill else 99,
        )
        s = ranked[0]
        if s["id"] in latest_by_skill:
            level = int(latest_by_skill[s["id"]]["level"])
            if level >= 5:
                return None
            note_en, note_id = await latest_note_for_skill(
                db, athlete_id=athlete_id, skill_id=s["id"]
            )
            return FocusSuggestionOut(
                skill_code=s["code"],
                label_en=s["name_en"],
                label_id=s["name_id"],
                current_level=level,
                required_level=None,
                category=cast(CategoryCode, s["category"]),
                latest_note_en=note_en,
                latest_note_id=note_id,
                reason="lowest_score",
            )

    return None


@router.get("/category/{category_code}", response_model=CategoryBreakdownOut)
async def get_category_breakdown(
    category_code: str,
    response: Response,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> CategoryBreakdownOut:
    if workspace_id is None:
        raise _no_workspace()
    resolved_sport_id = await resolve_sport_id(
        db, workspace_id=workspace_id, sport_id=sport_id
    )
    cat = _validate_category(category_code)

    athlete_id = await find_my_athlete_id(db, user_id=user_id, workspace_id=workspace_id)
    if athlete_id is None:
        raise _no_trainee()

    all_skills = [
        s for s in await all_skills_for_workspace(
            db, workspace_id=workspace_id, sport_id=resolved_sport_id
        )
        if s["category"] == cat
    ]
    latest = await latest_per_skill(db, athlete_id=athlete_id, sport_id=resolved_sport_id)
    latest_by_skill: dict[UUID, dict] = {r["skill_id"]: r for r in latest}

    scored: dict[UUID, int] = {
        s["id"]: int(latest_by_skill[s["id"]]["level"])
        for s in all_skills
        if s["id"] in latest_by_skill
    }
    descriptors = await descriptors_for_skills(
        db, workspace_id=workspace_id, skill_levels=scored
    )

    skills: list[SkillScoreOut] = []
    updated_at = None
    for s in all_skills:
        sid = s["id"]
        row = latest_by_skill.get(sid)
        desc = descriptors.get(sid, {})
        if row is not None:
            if updated_at is None or (
                row["recorded_at"] and row["recorded_at"] > updated_at
            ):
                updated_at = row["recorded_at"]
        skills.append(
            SkillScoreOut(
                code=s["code"],
                label_en=s["name_en"],
                label_id=s["name_id"],
                label_short_en=s.get("short_label_en"),
                label_short_id=s.get("short_label_id"),
                latest_score=int(row["level"]) if row else None,
                latest_descriptor_en=desc.get("en"),
                latest_descriptor_id=desc.get("id"),
                last_assessed_at=row["recorded_at"] if row else None,
            )
        )

    response.headers["Cache-Control"] = _PRIVATE_30S
    return CategoryBreakdownOut(category=cat, skills=skills, updated_at=updated_at)


@router.get("/category/{category_code}/blockers", response_model=CategoryBlockersOut)
async def get_category_blockers(
    category_code: str,
    response: Response,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    workspace_id: Annotated[UUID | None, Depends(get_current_workspace_id)],
    db: Annotated[AsyncSession, Depends(db_with_rls)],
    sport_id: UUID | None = Query(default=None),
) -> CategoryBlockersOut:
    if workspace_id is None:
        raise _no_workspace()
    resolved_sport_id = await resolve_sport_id(
        db, workspace_id=workspace_id, sport_id=sport_id
    )
    cat = _validate_category(category_code)

    athlete_id = await find_my_athlete_id(db, user_id=user_id, workspace_id=workspace_id)
    if athlete_id is None:
        raise _no_trainee()

    latest = await latest_per_skill(db, athlete_id=athlete_id, sport_id=resolved_sport_id)
    levels = {r["skill_id"]: int(r["level"]) for r in latest}
    tier_info = await recompute_tier(
        db,
        workspace_id=workspace_id,
        athlete_id=athlete_id,
        levels=levels,
        sport_id=resolved_sport_id,
    )
    next_tier = tier_info["next_tier"]
    if next_tier is None:
        response.headers["Cache-Control"] = _PRIVATE_30S
        return CategoryBlockersOut(
            next_tier=None, blockers_in_category=[], blockers_total_count=0
        )

    req_rows = (
        await db.execute(
            text(
                """
                SELECT tr.skill_id, tr.min_level,
                       s.code,
                       s.category::text AS category
                FROM tier_requirements tr
                JOIN skills s ON s.id = tr.skill_id
                WHERE tr.tier_id = :tid
                """
            ),
            {"tid": next_tier.id},
        )
    ).mappings().all()

    blockers_total = 0
    in_cat: list[TierBlockerEntryOut] = []
    for r in req_rows:
        cur = levels.get(r["skill_id"], 0)
        if cur < r["min_level"]:
            blockers_total += 1
            if r["category"] == cat:
                in_cat.append(
                    TierBlockerEntryOut(
                        skill_code=r["code"],
                        required_level=int(r["min_level"]),
                        current_level=cur,
                    )
                )

    response.headers["Cache-Control"] = _PRIVATE_30S
    return CategoryBlockersOut(
        next_tier=TierBriefLiteOut(
            code=next_tier.code,
            label_en=next_tier.name_game_en,
            label_id=next_tier.name_game_id,
        ),
        blockers_in_category=in_cat,
        blockers_total_count=blockers_total,
    )


__all__ = ["router"]

# Silence unused-name warning in some linters when a single-symbol export is used.
_ = Literal  # type: ignore[misc]
