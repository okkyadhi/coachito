"""RQ-decorated PDF generation.

The worker is sync (rq), so the job wraps the asyncpg + Jinja + WeasyPrint
work in ``asyncio.run`` and persists the result.  We bypass RLS because the
worker has no JWT context — that's fine, the job is system-level and the
inputs are validated by the enqueuing endpoint.

Storage strategy: when S3 credentials are configured (S3_ENDPOINT differs
from the MinIO dev default), the PDF is uploaded to object storage and
pdf_url is set to the public URL.  Otherwise (Railway without S3), the
bytes are stored in the ``pdf_bytes`` column and pdf_url is set to the
authenticated API path ``/reports/{id}/pdf``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from typing import Any

import asyncpg

from src.config import settings
from src.invites.og_landing import _superuser_dsn
from src.reports.emails import maybe_send_report_ready_email
from src.reports.template import build_report_context, render_report_pdf

log = logging.getLogger(__name__)


def generate_report_pdf(report_id: str) -> dict[str, Any]:
    """RQ entry point.  Wrapped so failures are surfaced via the row's
    ``status='failed'`` + ``error_message`` rather than a silent retry."""
    return asyncio.run(_run(report_id))


async def generate_report_pdf_async(report_id: str) -> dict[str, Any]:
    """Async variant for callers already inside an event loop (tests, the
    monthly cron when invoked from a FastAPI route)."""
    return await _run(report_id)


async def _run(report_id: str) -> dict[str, Any]:
    dsn = _superuser_dsn()
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(dsn)
        report = await conn.fetchrow(
            """
            SELECT workspace_id::text, athlete_id::text,
                   session_id::text AS session_id,
                   period_start, period_end, generation_type
            FROM reports WHERE id = $1
            """,
            report_id,
        )
        if report is None:
            await conn.close()
            return {"status": "failed", "error": "report row not found"}

        await conn.execute(
            "UPDATE reports SET status = 'generating' WHERE id = $1",
            report_id,
        )
    except Exception as early_exc:
        log.exception("report_setup_failed", extra={"report_id": report_id})
        if conn is not None:
            try:
                await conn.close()
            except Exception:
                pass
        # Best-effort: open a fresh connection to mark the row as failed so the
        # UI doesn't poll forever.
        try:
            fallback = await asyncpg.connect(dsn)
            await fallback.execute(
                "UPDATE reports SET status = 'failed', error_message = $2 WHERE id = $1",
                report_id,
                f"Setup error: {str(early_exc)[:480]}",
            )
            await fallback.close()
        except Exception:
            log.exception("report_fallback_mark_failed", extra={"report_id": report_id})
        raise early_exc

    try:
        log.info("report_build_context_start", extra={"report_id": report_id})
        ctx = await asyncio.wait_for(
            build_report_context(
                workspace_id=report["workspace_id"],
                athlete_id=report["athlete_id"],
                period_start=report["period_start"],
                period_end=report["period_end"],
                session_id=report["session_id"],
            ),
            timeout=30,
        )
        log.info("report_render_start", extra={"report_id": report_id})
        # render_report_pdf is synchronous (WeasyPrint); run in a thread so the
        # asyncio timeout can fire even if WeasyPrint hangs.
        pdf_bytes = await asyncio.wait_for(
            asyncio.to_thread(render_report_pdf, ctx),
            timeout=90,
        )
        log.info("report_upload_start", extra={"report_id": report_id, "bytes": len(pdf_bytes)})

        # S3 is optional: use it when the endpoint has been overridden from the
        # MinIO dev default, otherwise store bytes directly in the DB and serve
        # via the authenticated /reports/{id}/pdf endpoint.
        _use_s3 = settings.s3_endpoint != "http://minio:9000" and settings.s3_access_key != "minioadmin"
        if _use_s3:
            from src.uploads.s3 import put_object
            key = (
                f"workspaces/{report['workspace_id']}/reports/"
                f"{report['athlete_id']}-{report['period_start'].strftime('%Y-%m')}-"
                f"{report_id[:8]}.pdf"
            )
            pdf_url = await asyncio.wait_for(
                asyncio.to_thread(put_object, key=key, body=pdf_bytes, content_type="application/pdf"),
                timeout=30,
            )
            await conn.execute(
                """
                UPDATE reports
                   SET status = 'completed',
                       pdf_url = $2,
                       pdf_size_bytes = $3,
                       generated_at = $4
                 WHERE id = $1
                """,
                report_id,
                pdf_url,
                len(pdf_bytes),
                datetime.now(UTC),
            )
        else:
            # No S3 — persist bytes in the reports row.
            # The GET /reports/{id}/pdf endpoint serves them with Bearer auth.
            pdf_url = f"/reports/{report_id}/pdf"
            await conn.execute(
                """
                UPDATE reports
                   SET status = 'completed',
                       pdf_bytes = $2,
                       pdf_url = $3,
                       pdf_size_bytes = $4,
                       generated_at = $5
                 WHERE id = $1
                """,
                report_id,
                pdf_bytes,
                pdf_url,
                len(pdf_bytes),
                datetime.now(UTC),
            )

        log.info("report_generated", extra={"report_id": report_id, "bytes": len(pdf_bytes)})

        # Best-effort: notify the trainee by email if they have an account
        # + pref turned on.  Failures here are logged but never fail the
        # job — the PDF is already persisted and visible in-app.
        try:
            await maybe_send_report_ready_email(report_id=report_id)
        except Exception:
            log.exception(
                "report_email_dispatch_failed",
                extra={"report_id": report_id},
            )

        return {"status": "completed", "pdf_url": pdf_url, "bytes": len(pdf_bytes)}
    except Exception as e:  # pragma: no cover - hard failure path
        log.exception("report_generation_failed", extra={"report_id": report_id})
        await conn.execute(
            """
            UPDATE reports SET status = 'failed', error_message = $2 WHERE id = $1
            """,
            report_id,
            str(e)[:500],
        )
        return {"status": "failed", "error": str(e)}
    finally:
        await conn.close()


# ── Synchronous helper for tests + the smoke script ──────────────


def generate_report_bytes_sync(
    *,
    workspace_id: str,
    athlete_id: str,
    period_start: date,
    period_end: date,
) -> bytes:
    """Build the PDF without going through the DB-backed reports row.  Used
    by tests + ``scripts/test_pdf_smoke``."""
    return asyncio.run(
        _build_bytes(
            workspace_id=workspace_id,
            athlete_id=athlete_id,
            period_start=period_start,
            period_end=period_end,
        )
    )


async def _build_bytes(
    *,
    workspace_id: str,
    athlete_id: str,
    period_start: date,
    period_end: date,
) -> bytes:
    ctx = await build_report_context(
        workspace_id=workspace_id,
        athlete_id=athlete_id,
        period_start=period_start,
        period_end=period_end,
    )
    return render_report_pdf(ctx)


# Silence "imported but unused" for settings — kept for future env-driven
# tuning (e.g. queue name / retry policy).
_ = settings
