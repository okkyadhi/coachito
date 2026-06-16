"""Monthly auto-generation cron.

Enumerates every active trainee with at least one assessment in the prior
calendar month and enqueues a report job per (workspace, trainee).  Designed
to be run from system cron at 03:00 UTC on the 1st — the dry-run mode is
what the spec's "verify" step exercises.
"""

from __future__ import annotations

import asyncio
import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import asyncpg
from redis import Redis as SyncRedis
from rq import Queue

from src.config import settings
from src.invites.og_landing import _superuser_dsn


@dataclass
class CronCandidate:
    workspace_id: str
    workspace_name: str
    athlete_id: str
    trainee_name: str
    coach_id: str
    period_start: date
    period_end: date


def prior_month_range(today: date | None = None) -> tuple[date, date]:
    today = today or datetime.now(UTC).date()
    # First of the current month → previous month.
    first_this = today.replace(day=1)
    last_prev = first_this.replace(day=1)  # placeholder
    # Get last day of previous month by subtracting one day from first_this.
    last_prev = first_this.replace(day=1)
    # Compute previous month start + end without timedelta gymnastics:
    if first_this.month == 1:
        prev_year, prev_month = first_this.year - 1, 12
    else:
        prev_year, prev_month = first_this.year, first_this.month - 1
    start = date(prev_year, prev_month, 1)
    end = date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])
    return start, end


async def find_candidates(
    *, period_start: date, period_end: date
) -> list[CronCandidate]:
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                w.id::text   AS workspace_id,
                w.name       AS workspace_name,
                a.id::text   AS athlete_id,
                a.display_name AS trainee_name,
                COALESCE(
                    (SELECT s.coach_id::text FROM sessions s
                     WHERE s.athlete_id = a.id
                     ORDER BY s.scheduled_at DESC NULLS LAST LIMIT 1),
                    w.owner_user_id::text
                ) AS coach_id
            FROM assessments asm
            JOIN athletes a ON a.id = asm.athlete_id
            JOIN workspaces w ON w.id = a.workspace_id
            WHERE asm.status IN ('published','edited')
              AND COALESCE(asm.edited_at, asm.published_at)::date BETWEEN $1 AND $2
              AND a.archived_at IS NULL
              AND w.archived_at IS NULL
            ORDER BY w.name, a.display_name
            """,
            period_start,
            period_end,
        )
    finally:
        await conn.close()
    return [
        CronCandidate(
            workspace_id=r["workspace_id"],
            workspace_name=r["workspace_name"],
            athlete_id=r["athlete_id"],
            trainee_name=r["trainee_name"],
            coach_id=r["coach_id"],
            period_start=period_start,
            period_end=period_end,
        )
        for r in rows
    ]


async def enqueue_for_candidates(
    candidates: list[CronCandidate], *, dry_run: bool
) -> list[dict[str, Any]]:
    """Inserts a `reports` row per candidate and enqueues the generation job.
    With ``dry_run=True`` only returns what would have happened."""
    results: list[dict[str, Any]] = []
    if dry_run:
        return [
            {
                "workspace": c.workspace_name,
                "trainee": c.trainee_name,
                "period": f"{c.period_start} → {c.period_end}",
                "dry_run": True,
            }
            for c in candidates
        ]

    conn = await asyncpg.connect(_superuser_dsn())
    queue = Queue("default", connection=SyncRedis.from_url(settings.redis_url))
    try:
        for c in candidates:
            report_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO reports (
                    id, workspace_id, athlete_id, coach_id,
                    period_start, period_end, status, generation_type
                )
                VALUES ($1, $2, $3, $4, $5, $6, 'pending', 'auto')
                """,
                report_id,
                c.workspace_id,
                c.athlete_id,
                c.coach_id,
                c.period_start,
                c.period_end,
            )
            job = queue.enqueue(
                "src.reports.jobs.generate_report_pdf", report_id, job_timeout=120
            )
            results.append(
                {
                    "workspace": c.workspace_name,
                    "trainee": c.trainee_name,
                    "report_id": report_id,
                    "job_id": job.id,
                }
            )
    finally:
        await conn.close()
    return results


def run_monthly(*, dry_run: bool = False) -> list[dict[str, Any]]:
    """Entry point for both the system cron and the smoke script."""
    period_start, period_end = prior_month_range()
    candidates = asyncio.run(
        find_candidates(period_start=period_start, period_end=period_end)
    )
    return asyncio.run(enqueue_for_candidates(candidates, dry_run=dry_run))


async def run_monthly_async(*, dry_run: bool = False) -> list[dict[str, Any]]:
    """Async variant for callers inside an existing event loop (tests)."""
    period_start, period_end = prior_month_range()
    candidates = await find_candidates(
        period_start=period_start, period_end=period_end
    )
    return await enqueue_for_candidates(candidates, dry_run=dry_run)
