"""Render a real PDF to ``/tmp/sample.pdf`` so a human can review the layout
against docs/08.

Picks the most recently active workspace + trainee that has at least one
assessment.  Falls back to whatever's around so a fresh seed environment
still produces something openable.

Usage::

    docker compose -f infra/docker-compose.yml exec api python -m scripts.test_pdf_smoke
    docker compose -f infra/docker-compose.yml cp coachito-api-1:/tmp/sample.pdf ./sample.pdf
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import asyncpg

from src.invites.og_landing import _superuser_dsn
from src.reports.cron import prior_month_range
from src.reports.template import build_report_context, render_report_pdf


async def _pick_target() -> dict[str, Any] | None:
    conn = await asyncpg.connect(_superuser_dsn())
    try:
        # Prefer a trainee with assessments in the prior month.
        ps, pe = prior_month_range()
        row = await conn.fetchrow(
            """
            SELECT a.id::text AS athlete_id, a.workspace_id::text AS workspace_id
            FROM assessments asm
            JOIN athletes a ON a.id = asm.athlete_id
            WHERE asm.recorded_at::date BETWEEN $1 AND $2
              AND a.archived_at IS NULL
            ORDER BY asm.recorded_at DESC LIMIT 1
            """,
            ps,
            pe,
        )
        if row:
            return {**dict(row), "period_start": ps, "period_end": pe}

        # Fall back: any athlete + any 30-day window ending today.
        row = await conn.fetchrow(
            """
            SELECT a.id::text AS athlete_id, a.workspace_id::text AS workspace_id
            FROM athletes a WHERE a.archived_at IS NULL
            ORDER BY a.created_at DESC LIMIT 1
            """
        )
        if not row:
            return None
        end = datetime.now(UTC).date()
        start = date(end.year, end.month, 1)
        return {**dict(row), "period_start": start, "period_end": end}
    finally:
        await conn.close()


async def _main() -> int:
    target = await _pick_target()
    if target is None:
        print("No athlete in DB — seed one and try again.")
        return 1

    ctx = await build_report_context(
        workspace_id=target["workspace_id"],
        athlete_id=target["athlete_id"],
        period_start=target["period_start"],
        period_end=target["period_end"],
    )
    pdf = render_report_pdf(ctx)
    out = Path("/tmp/sample.pdf")
    out.write_bytes(pdf)
    print(
        f"Wrote {out} ({len(pdf):,} bytes) for trainee={target['athlete_id']} "
        f"workspace={target['workspace_id']} period={target['period_start']} → {target['period_end']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
