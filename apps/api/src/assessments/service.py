"""Assessment v2 — parent/child shape, draft + publish + edit lifecycle.

Key invariants:
  - One assessment per session (UNIQUE on session_id).
  - Drafts don't affect tier; only published/edited do.
  - Tier recalc fires on publish + edit (when scores changed).
  - Audit row written to ``assessment_edits`` on every PATCH to a
    non-draft assessment.

All public operations run inside the caller's AsyncSession transaction.
RLS is applied via ``db_with_rls``; the explicit ``workspace_id`` filter
is defense in depth.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.athletes.schemas import TierBrief
from src.sports.service import (
    SportNotQualifiedError,
    coach_qualified_for_sport,
    resolve_sport_id,
    upsert_athlete_sport_tier,
)

from .schemas import (
    AssessmentDraftIn,
    AssessmentEditIn,
    AssessmentOut,
    CategoryAverageOut,
    GainOut,
    ScoreOut,
    SkillBriefOut,
    TierSliceOut,
)

# ── Exceptions ──────────────────────────────────────────────────


class AthleteNotFoundError(Exception):
    pass


class AssessmentNotFoundError(Exception):
    pass


class InvalidSkillError(Exception):
    pass


class StatusConflictError(Exception):
    """Operation incompatible with the current status (e.g. publish a published
    assessment, discard a non-draft, edit a draft via PATCH)."""


class ValidationFailedError(Exception):
    """Used on publish — surfaces validation messages back to the caller."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


# ── Save / update draft ─────────────────────────────────────────


async def upsert_draft(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    coach_id: UUID,
    payload: AssessmentDraftIn,
) -> AssessmentOut:
    """Find-or-create the assessment row for (session) and replace its
    scores + summary + notes.  Always lands in or stays at ``draft``.

    If the assessment is already published/edited, this raises
    ``StatusConflictError`` — the caller should PATCH instead.
    """
    # 1. Athlete sanity (RLS already filters; explicit 404 here).
    athlete = (
        await db.execute(
            text(
                "SELECT id FROM athletes "
                "WHERE id = :aid AND workspace_id = :wid AND archived_at IS NULL"
            ),
            {"aid": payload.athlete_id, "wid": workspace_id},
        )
    ).first()
    if athlete is None:
        raise AthleteNotFoundError(str(payload.athlete_id))

    # 1b. Resolve the sport for this assessment (defaults to the workspace's
    # single active sport).  Denormalized onto the assessment + session rows.
    sport_id = await resolve_sport_id(
        db, workspace_id=workspace_id, sport_id=payload.sport_id
    )
    # 1c. The coach must be qualified for this sport (doc §3.4).
    if not await coach_qualified_for_sport(
        db, workspace_id=workspace_id, user_id=coach_id, sport_id=sport_id
    ):
        raise SportNotQualifiedError(
            "You're not qualified to assess this sport in this workspace."
        )

    # 2. Resolve session — explicit, or auto-create.
    session_id = await _resolve_session_id(
        db,
        workspace_id=workspace_id,
        sport_id=sport_id,
        athlete_id=payload.athlete_id,
        coach_id=coach_id,
        explicit_session_id=payload.session_id,
        scheduled_at=payload.session_scheduled_at,
        duration_min=payload.session_duration_min,
        court=payload.session_court,
        focus=payload.session_focus,
        summary=payload.summary,
    )

    # 3. Validate skill ids belong to the workspace's curriculum (if any).
    if payload.scores:
        await _validate_skills(
            db, workspace_id=workspace_id, skill_ids=[s.skill_id for s in payload.scores]
        )

    # 4. Find existing parent for this session, or insert one.
    existing = (
        await db.execute(
            text("SELECT id, status, coach_id FROM assessments WHERE session_id = :sid"),
            {"sid": session_id},
        )
    ).first()

    if existing is not None:
        if existing[1] not in ("draft",):
            raise StatusConflictError(
                f"Assessment for this session is {existing[1]} — use PATCH to edit."
            )
        if existing[2] != coach_id:
            raise StatusConflictError(
                "Another coach is drafting this assessment."
            )
        assessment_id = existing[0]
        await db.execute(
            text(
                """
                UPDATE assessments
                   SET summary        = :summary,
                       internal_notes = :notes,
                       saved_at       = NOW(),
                       updated_at     = NOW()
                 WHERE id = :id
                """
            ),
            {
                "id": assessment_id,
                "summary": payload.summary,
                "notes": payload.internal_notes,
            },
        )
    else:
        assessment_id = uuid4()
        await db.execute(
            text(
                """
                INSERT INTO assessments (
                    id, workspace_id, sport_id, session_id, athlete_id, coach_id,
                    status, summary, internal_notes
                ) VALUES (
                    :id, :wid, :sportid, :sid, :aid, :cid, 'draft', :summary, :notes
                )
                """
            ),
            {
                "id": assessment_id,
                "wid": workspace_id,
                "sportid": sport_id,
                "sid": session_id,
                "aid": payload.athlete_id,
                "cid": coach_id,
                "summary": payload.summary,
                "notes": payload.internal_notes,
            },
        )

    # 5. Upsert scores (one per skill).  We don't delete missing skills —
    # the FE supplies a complete list each save.  Cleaner: replace via
    # DELETE-not-in + insert+update.
    if payload.scores:
        skill_placeholders = ", ".join(
            f":sk{i}" for i in range(len(payload.scores))
        )
        params: dict[str, Any] = {
            f"sk{i}": s.skill_id for i, s in enumerate(payload.scores)
        }
        params["aid_assessment"] = assessment_id
        # Remove rows for skills no longer in the payload.
        await db.execute(
            text(
                f"DELETE FROM assessment_scores "
                f"WHERE assessment_id = :aid_assessment "
                f"  AND skill_id NOT IN ({skill_placeholders})"
            ),
            params,
        )
        # Upsert each score row.
        for s in payload.scores:
            await db.execute(
                text(
                    """
                    INSERT INTO assessment_scores (
                        assessment_id, skill_id, level, note
                    ) VALUES (:aid, :sk, :lv, :note)
                    ON CONFLICT (assessment_id, skill_id) DO UPDATE
                       SET level      = EXCLUDED.level,
                           note       = EXCLUDED.note,
                           updated_at = NOW()
                    """
                ),
                {
                    "aid": assessment_id,
                    "sk": s.skill_id,
                    "lv": s.level,
                    "note": s.note,
                },
            )
    else:
        # Empty scores → wipe everything.
        await db.execute(
            text(
                "DELETE FROM assessment_scores WHERE assessment_id = :aid"
            ),
            {"aid": assessment_id},
        )

    await db.flush()
    return await load_assessment(db, assessment_id=assessment_id)


# ── Publish ─────────────────────────────────────────────────────


async def publish(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    coach_id: UUID,
    assessment_id: UUID,
    force_empty: bool,
) -> AssessmentOut:
    row = (
        await db.execute(
            text(
                """
                SELECT id, status, coach_id, athlete_id, session_id, summary
                FROM assessments WHERE id = :id
                """
            ),
            {"id": assessment_id},
        )
    ).first()
    if row is None:
        raise AssessmentNotFoundError(str(assessment_id))

    _, status, owner, athlete_id, session_id, summary = row
    if owner != coach_id:
        raise StatusConflictError("Only the drafting coach can publish.")
    if status != "draft":
        raise StatusConflictError(
            f"Cannot publish a {status} assessment.",
        )

    # Validation per §4.
    errors: list[str] = []
    score_count = int(
        await db.scalar(
            text(
                "SELECT count(*) FROM assessment_scores WHERE assessment_id = :id"
            ),
            {"id": assessment_id},
        )
        or 0
    )
    summary_chars = len(summary or "")
    if not force_empty and score_count == 0 and summary_chars <= 10:
        errors.append(
            "Add at least one score or a session summary before publishing."
        )
    # Trainee must still be active (we soft-archive elsewhere; double-check).
    archived = await db.scalar(
        text("SELECT archived_at FROM athletes WHERE id = :id"),
        {"id": athlete_id},
    )
    if archived is not None:
        errors.append("This trainee has been archived.")

    if errors:
        raise ValidationFailedError(errors)

    # Capture the trainee's tier BEFORE this publish — used by the FE to
    # detect a "tier-up" and trigger a celebration when the new tier is
    # higher than the previous one.
    prev_tier_row = (
        await db.execute(
            text(
                """
                SELECT t.id, t.code, t.name_game_en, t.name_game_id
                FROM athletes a
                LEFT JOIN tiers t ON t.id = a.current_tier_id
                WHERE a.id = :aid
                """
            ),
            {"aid": athlete_id},
        )
    ).first()
    previous_tier: TierBrief | None = None
    if prev_tier_row and prev_tier_row[0] is not None:
        previous_tier = TierBrief(
            id=str(prev_tier_row[0]),
            code=prev_tier_row[1],
            name_game_en=prev_tier_row[2],
            name_game_id=prev_tier_row[3],
        )

    # Flip to published.
    await db.execute(
        text(
            """
            UPDATE assessments
               SET status       = 'published',
                   published_at = NOW(),
                   updated_at   = NOW()
             WHERE id = :id
            """
        ),
        {"id": assessment_id},
    )
    # Session also flips to completed.
    await db.execute(
        text(
            """
            UPDATE sessions
               SET status       = 'completed',
                   completed_at = COALESCE(completed_at, NOW()),
                   updated_at   = NOW()
             WHERE id = :sid AND status <> 'completed'
            """
        ),
        {"sid": session_id},
    )

    # Tier recalc using new latest-levels, scoped to this assessment's sport.
    a_sport_id = await db.scalar(
        text("SELECT sport_id FROM assessments WHERE id = :id"),
        {"id": assessment_id},
    )
    levels = await _latest_published_levels(db, athlete_id=athlete_id)
    tier_info = await recompute_tier(
        db,
        workspace_id=workspace_id,
        athlete_id=athlete_id,
        sport_id=a_sport_id,
        levels=levels,
    )

    out = await load_assessment(db, assessment_id=assessment_id)
    out.tier = await _build_tier_slice(
        db, workspace_id=workspace_id, athlete_id=athlete_id, tier_info=tier_info
    )
    out.previous_tier = previous_tier
    return out


# ── Edit (PATCH) ────────────────────────────────────────────────


async def edit_assessment(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    coach_id: UUID,
    assessment_id: UUID,
    patch: AssessmentEditIn,
) -> AssessmentOut:
    row = (
        await db.execute(
            text(
                """
                SELECT id, status, coach_id, athlete_id, summary, internal_notes
                FROM assessments WHERE id = :id
                """
            ),
            {"id": assessment_id},
        )
    ).first()
    if row is None:
        raise AssessmentNotFoundError(str(assessment_id))

    aid, status, owner, athlete_id, current_summary, current_notes = row
    if owner != coach_id:
        raise StatusConflictError("Only the assessment's coach can edit.")
    if status not in ("published", "edited"):
        raise StatusConflictError(
            f"Cannot PATCH a {status} assessment — use POST to update drafts."
        )

    # Snapshot current scores for diffing.
    score_rows = (
        await db.execute(
            text(
                "SELECT skill_id, level, note FROM assessment_scores "
                "WHERE assessment_id = :id"
            ),
            {"id": aid},
        )
    ).all()
    current_scores: dict[UUID, tuple[int, str | None]] = {
        r[0]: (r[1], r[2]) for r in score_rows
    }

    changes: dict[str, Any] = {}

    # Summary diff.
    if patch.summary is not None and patch.summary != (current_summary or ""):
        changes["summary"] = {"from": current_summary, "to": patch.summary}
        await db.execute(
            text(
                "UPDATE assessments SET summary = :s, updated_at = NOW() "
                "WHERE id = :id"
            ),
            {"s": patch.summary, "id": aid},
        )

    # Internal notes diff.
    if (
        patch.internal_notes is not None
        and patch.internal_notes != (current_notes or "")
    ):
        changes["internal_notes"] = {
            "from": current_notes,
            "to": patch.internal_notes,
        }
        await db.execute(
            text(
                "UPDATE assessments SET internal_notes = :n, updated_at = NOW() "
                "WHERE id = :id"
            ),
            {"n": patch.internal_notes, "id": aid},
        )

    # Scores diff (only if the caller sent a `scores` array).
    scores_changed = False
    if patch.scores is not None:
        await _validate_skills(
            db, workspace_id=workspace_id, skill_ids=[s.skill_id for s in patch.scores]
        )
        new_map: dict[UUID, tuple[int, str | None]] = {
            s.skill_id: (s.level, s.note) for s in patch.scores
        }
        diffs: list[dict[str, Any]] = []
        # Removed skills.
        for old_sid, (old_level, _) in current_scores.items():
            if old_sid not in new_map:
                diffs.append(
                    {"skill_id": str(old_sid), "from": old_level, "to": None}
                )
                await db.execute(
                    text(
                        "DELETE FROM assessment_scores "
                        "WHERE assessment_id = :aid AND skill_id = :sk"
                    ),
                    {"aid": aid, "sk": old_sid},
                )
        # Inserted / updated.
        for sid, (new_level, new_note) in new_map.items():
            old = current_scores.get(sid)
            if old is None or old[0] != new_level or (old[1] or None) != (new_note or None):
                diffs.append(
                    {
                        "skill_id": str(sid),
                        "from": old[0] if old else None,
                        "to": new_level,
                    }
                )
                await db.execute(
                    text(
                        """
                        INSERT INTO assessment_scores (
                            assessment_id, skill_id, level, note
                        ) VALUES (:aid, :sk, :lv, :note)
                        ON CONFLICT (assessment_id, skill_id) DO UPDATE
                           SET level      = EXCLUDED.level,
                               note       = EXCLUDED.note,
                               updated_at = NOW()
                        """
                    ),
                    {"aid": aid, "sk": sid, "lv": new_level, "note": new_note},
                )
        if diffs:
            changes["scores"] = diffs
            scores_changed = True

    if not changes:
        # Idempotent no-op.
        return await load_assessment(db, assessment_id=aid)

    # Flip to edited.
    await db.execute(
        text(
            """
            UPDATE assessments
               SET status     = 'edited',
                   edited_at  = NOW(),
                   updated_at = NOW()
             WHERE id = :id
            """
        ),
        {"id": aid},
    )

    # Write audit row.
    import json
    await db.execute(
        text(
            """
            INSERT INTO assessment_edits (
                assessment_id, edited_by_id, changes_jsonb, reason
            ) VALUES (:aid, :uid, CAST(:changes AS JSONB), :reason)
            """
        ),
        {
            "aid": aid,
            "uid": coach_id,
            "changes": json.dumps(changes),
            "reason": patch.reason,
        },
    )

    # Recalc tier when scores changed.
    out = await load_assessment(db, assessment_id=aid)
    if scores_changed:
        a_sport_id = await db.scalar(
            text("SELECT sport_id FROM assessments WHERE id = :id"), {"id": aid}
        )
        levels = await _latest_published_levels(db, athlete_id=athlete_id)
        tier_info = await recompute_tier(
            db,
            workspace_id=workspace_id,
            athlete_id=athlete_id,
            sport_id=a_sport_id,
            levels=levels,
        )
        out.tier = await _build_tier_slice(
            db, workspace_id=workspace_id, athlete_id=athlete_id, tier_info=tier_info
        )
    return out


# ── Discard draft ───────────────────────────────────────────────


async def discard_draft(
    db: AsyncSession, *, coach_id: UUID, assessment_id: UUID
) -> None:
    row = (
        await db.execute(
            text(
                "SELECT status, coach_id FROM assessments WHERE id = :id"
            ),
            {"id": assessment_id},
        )
    ).first()
    if row is None:
        raise AssessmentNotFoundError(str(assessment_id))
    if row[1] != coach_id:
        raise StatusConflictError("Only the drafting coach can discard.")
    if row[0] != "draft":
        raise StatusConflictError("Only drafts can be discarded.")
    await db.execute(
        text("DELETE FROM assessments WHERE id = :id"), {"id": assessment_id}
    )


# ── Reads ───────────────────────────────────────────────────────


async def load_assessment(
    db: AsyncSession, *, assessment_id: UUID
) -> AssessmentOut:
    row = (
        await db.execute(
            text(
                """
                SELECT a.id, a.workspace_id, a.session_id, a.athlete_id,
                       a.coach_id, u.display_name AS coach_name,
                       a.status, a.summary, a.internal_notes,
                       a.saved_at, a.published_at, a.edited_at,
                       a.trainee_viewed_at,
                       s.scheduled_at, s.duration_min,
                       s.court, s.focus::text AS focus
                FROM assessments a
                JOIN users u    ON u.id = a.coach_id
                JOIN sessions s ON s.id = a.session_id
                WHERE a.id = :id
                """
            ),
            {"id": assessment_id},
        )
    ).first()
    if row is None:
        raise AssessmentNotFoundError(str(assessment_id))

    score_rows = (
        await db.execute(
            text(
                """
                SELECT skill_id, level, note, updated_at
                FROM assessment_scores
                WHERE assessment_id = :id
                ORDER BY updated_at ASC
                """
            ),
            {"id": assessment_id},
        )
    ).all()

    feedback_counts = (
        await db.execute(
            text(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE read_at IS NULL) AS unread
                FROM feedbacks
                WHERE assessment_id = :id AND withdrawn_at IS NULL
                """
            ),
            {"id": assessment_id},
        )
    ).first()

    return AssessmentOut(
        id=str(row[0]),
        workspace_id=str(row[1]),
        session_id=str(row[2]),
        athlete_id=str(row[3]),
        coach_id=str(row[4]),
        coach_display_name=row[5],
        status=row[6],
        summary=row[7],
        internal_notes=row[8],
        saved_at=row[9],
        published_at=row[10],
        edited_at=row[11],
        trainee_viewed_at=row[12],
        session_scheduled_at=row[13],
        session_duration_min=row[14],
        session_court=row[15],
        session_focus=row[16],
        scores=[
            ScoreOut(
                skill_id=str(s[0]),
                level=s[1],
                note=s[2],
                updated_at=s[3],
            )
            for s in score_rows
        ],
        feedback_count=int(feedback_counts[0] or 0) if feedback_counts else 0,
        unread_feedback_count=(
            int(feedback_counts[1] or 0) if feedback_counts else 0
        ),
    )


async def load_by_session(
    db: AsyncSession, *, session_id: UUID
) -> AssessmentOut | None:
    row = (
        await db.execute(
            text("SELECT id FROM assessments WHERE session_id = :sid"),
            {"sid": session_id},
        )
    ).first()
    if row is None:
        return None
    return await load_assessment(db, assessment_id=row[0])


# ── Tier recalc ─────────────────────────────────────────────────


async def _latest_published_levels(
    db: AsyncSession, *, athlete_id: UUID
) -> dict[UUID, int]:
    """Latest level per skill across published/edited assessments only.
    Drafts are intentionally excluded."""
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (s.skill_id) s.skill_id, s.level
                FROM assessment_scores s
                JOIN assessments a ON a.id = s.assessment_id
                WHERE a.athlete_id = :aid
                  AND a.status IN ('published','edited')
                ORDER BY s.skill_id,
                         COALESCE(a.edited_at, a.published_at) DESC NULLS LAST,
                         s.updated_at DESC
                """
            ),
            {"aid": athlete_id},
        )
    ).all()
    return {r[0]: r[1] for r in rows}


async def recompute_tier(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    athlete_id: UUID,
    sport_id: UUID | None = None,
    levels: Mapping[UUID, int] | None = None,
) -> dict[str, Any]:
    if levels is None:
        levels = await _latest_published_levels(db, athlete_id=athlete_id)
    if sport_id is None:
        sport_id = await resolve_sport_id(db, workspace_id=workspace_id)

    rows = (
        await db.execute(
            text(
                """
                SELECT t.id          AS tier_id,
                       t.code        AS tier_code,
                       t.display_order,
                       t.name_game_en,
                       t.name_game_id,
                       tr.skill_id,
                       tr.min_level
                FROM tiers t
                JOIN tier_requirements tr ON tr.tier_id = t.id
                WHERE t.sport_id = :sid
                  AND (t.workspace_id = :wid OR t.workspace_id IS NULL)
                ORDER BY t.display_order ASC
                """
            ),
            {"wid": workspace_id, "sid": sport_id},
        )
    ).mappings().all()

    by_tier: dict[UUID, dict[str, Any]] = {}
    for r in rows:
        tid = r["tier_id"]
        bucket = by_tier.setdefault(
            tid,
            {
                "tier_id": tid,
                "tier_code": r["tier_code"],
                "display_order": r["display_order"],
                "name_game_en": r["name_game_en"],
                "name_game_id": r["name_game_id"],
                "reqs": [],
            },
        )
        bucket["reqs"].append((r["skill_id"], r["min_level"]))

    beginner_row = (
        await db.execute(
            text(
                """
                SELECT id, code, display_order, name_game_en, name_game_id
                FROM tiers
                WHERE sport_id = :sid
                  AND (workspace_id = :wid OR workspace_id IS NULL)
                  AND display_order = 1
                LIMIT 1
                """
            ),
            {"wid": workspace_id, "sid": sport_id},
        )
    ).mappings().first()

    tiers_ordered = sorted(by_tier.values(), key=lambda b: b["display_order"])
    current = None
    met_count_for_next = 0
    total_for_next = 0
    next_tier_data = None

    for tier in tiers_ordered:
        met = sum(1 for sid, mn in tier["reqs"] if levels.get(sid, 0) >= mn)
        total = len(tier["reqs"])
        if met == total and total > 0:
            current = tier
        else:
            next_tier_data = tier
            met_count_for_next = met
            total_for_next = total
            break

    if current is None and beginner_row is not None:
        current_brief = TierBrief(
            id=str(beginner_row["id"]),
            code=beginner_row["code"],
            name_game_en=beginner_row["name_game_en"],
            name_game_id=beginner_row["name_game_id"],
        )
        if next_tier_data is None and tiers_ordered:
            next_tier_data = tiers_ordered[0]
            met_count_for_next = sum(
                1 for sid, mn in next_tier_data["reqs"] if levels.get(sid, 0) >= mn
            )
            total_for_next = len(next_tier_data["reqs"])
    elif current is not None:
        current_brief = TierBrief(
            id=str(current["tier_id"]),
            code=current["tier_code"],
            name_game_en=current["name_game_en"],
            name_game_id=current["name_game_id"],
        )
    else:
        current_brief = None

    next_brief = (
        TierBrief(
            id=str(next_tier_data["tier_id"]),
            code=next_tier_data["tier_code"],
            name_game_en=next_tier_data["name_game_en"],
            name_game_id=next_tier_data["name_game_id"],
        )
        if next_tier_data is not None
        else None
    )

    cache_id: UUID | None = None
    if current is not None:
        cache_id = current["tier_id"]
    elif beginner_row is not None:
        cache_id = beginner_row["id"]

    await db.execute(
        text(
            "UPDATE athletes SET current_tier_id = :tid, updated_at = NOW() "
            "WHERE id = :aid AND workspace_id = :wid"
        ),
        {"tid": cache_id, "aid": athlete_id, "wid": workspace_id},
    )
    # Per-sport tier cache (multi-sport): keep alongside the legacy
    # ``athletes.current_tier_id`` so a multi-sport athlete carries one tier
    # per sport.
    await upsert_athlete_sport_tier(
        db,
        workspace_id=workspace_id,
        athlete_id=athlete_id,
        sport_id=sport_id,
        tier_id=cache_id,
    )

    return {
        "current_tier": current_brief,
        "next_tier": next_brief,
        "met_count": met_count_for_next,
        "total_requirements": total_for_next,
    }


async def _build_tier_slice(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    athlete_id: UUID,
    tier_info: dict[str, Any],
) -> TierSliceOut:
    levels = await _latest_published_levels(db, athlete_id=athlete_id)
    category_averages = await _category_averages(
        db, workspace_id=workspace_id, levels=levels
    )
    # Gains: we don't know "previous" cheaply here — leave empty for now;
    # the FE re-fetches the trainee profile for the full history.
    return TierSliceOut(
        current_tier=tier_info["current_tier"],
        next_tier=tier_info["next_tier"],
        met_count=tier_info["met_count"],
        total_requirements=tier_info["total_requirements"],
        category_averages=category_averages,
        recent_gains=[],
    )


# ── Helpers ─────────────────────────────────────────────────────


async def _resolve_session_id(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    sport_id: UUID,
    athlete_id: UUID,
    coach_id: UUID,
    explicit_session_id: UUID | None,
    scheduled_at: datetime | None,
    duration_min: int | None,
    court: str | None,
    focus: str | None,
    summary: str | None,
) -> UUID:
    """Either return the given session_id or create a fresh session row.

    Unlike v1, we never auto-flip the session to ``completed`` here —
    completion happens on Publish.  This keeps drafts attached to scheduled
    sessions.
    """
    if explicit_session_id is not None:
        return explicit_session_id

    new_id = uuid4()
    await db.execute(
        text(
            """
            INSERT INTO sessions (
                id, workspace_id, sport_id, athlete_id, coach_id,
                scheduled_at, duration_min, court, focus,
                summary, status
            )
            VALUES (
                :id, :wid, :sportid, :aid, :cid,
                COALESCE(:scheduled_at, NOW()),
                COALESCE(:duration_min, 60),
                :court,
                COALESCE(CAST(:focus AS session_focus), CAST('general' AS session_focus)),
                :summary, 'scheduled'
            )
            """
        ),
        {
            "id": new_id,
            "wid": workspace_id,
            "sportid": sport_id,
            "aid": athlete_id,
            "cid": coach_id,
            "scheduled_at": scheduled_at,
            "duration_min": duration_min,
            "court": court,
            "focus": focus,
            "summary": summary,
        },
    )
    return new_id


async def _validate_skills(
    db: AsyncSession, *, workspace_id: UUID, skill_ids: list[UUID]
) -> None:
    if not skill_ids:
        return
    skill_ids = list(set(skill_ids))
    placeholders = ", ".join(f":sk{i}" for i in range(len(skill_ids)))
    params: dict[str, Any] = {f"sk{i}": sid for i, sid in enumerate(skill_ids)}
    params["wid"] = workspace_id
    rows = (
        await db.execute(
            text(
                f"SELECT id FROM skills "
                f"WHERE id IN ({placeholders}) "
                f"  AND (workspace_id = :wid OR workspace_id IS NULL) "
                f"  AND is_enabled = TRUE"
            ),
            params,
        )
    ).all()
    if len(rows) != len(skill_ids):
        raise InvalidSkillError()


async def _category_averages(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    levels: Mapping[UUID, int],
) -> list[CategoryAverageOut]:
    if not levels:
        return [
            CategoryAverageOut(category=c, average=0, skills_rated=0)
            for c in ("technical", "tactical", "physical", "mental")
        ]
    skill_ids = list(levels.keys())
    placeholders = ", ".join(f":s{i}" for i in range(len(skill_ids)))
    params: dict[str, Any] = {f"s{i}": sid for i, sid in enumerate(skill_ids)}
    params["wid"] = workspace_id
    cats = (
        await db.execute(
            text(
                f"SELECT id, category FROM skills "
                f"WHERE id IN ({placeholders}) "
                f"  AND (workspace_id = :wid OR workspace_id IS NULL)"
            ),
            params,
        )
    ).all()
    buckets: dict[str, list[int]] = {
        "technical": [],
        "tactical": [],
        "physical": [],
        "mental": [],
    }
    for sid, cat in cats:
        buckets.setdefault(cat, []).append(levels[sid])
    return [
        CategoryAverageOut(
            category=cat,
            average=round(sum(vals) / len(vals), 1) if vals else 0,
            skills_rated=len(vals),
        )
        for cat, vals in buckets.items()
    ]


# Re-export for the report template that joins through assessment_scores.
_ = SkillBriefOut
_ = GainOut
_ = Sequence
_ = UTC
