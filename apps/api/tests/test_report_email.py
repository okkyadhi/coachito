"""maybe_send_report_ready_email — pref toggle + missing-link guards."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import asyncpg
import pytest

from src.reports.emails import maybe_send_report_ready_email

from ._test_helpers import SUPERUSER_DSN


@pytest.fixture
async def conn() -> asyncpg.Connection:  # type: ignore[type-arg]
    c = await asyncpg.connect(SUPERUSER_DSN)
    yield c
    await c.close()


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture every aiosmtplib.send call so tests can assert."""
    captured: list[dict[str, Any]] = []

    async def fake_send(msg: Any, **kwargs: Any) -> None:
        captured.append({
            "to": msg["To"],
            "subject": msg["Subject"],
            "from": msg["From"],
        })

    monkeypatch.setattr("src.reports.emails.aiosmtplib.send", fake_send)
    return captured


@pytest.fixture(autouse=True)
async def _cleanup(conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    yield
    await conn.execute(
        "DELETE FROM reports WHERE coach_id IN ("
        "  SELECT id FROM users WHERE email LIKE 'test-remail-%@example.com')"
    )
    await conn.execute(
        "DELETE FROM user_notification_prefs WHERE user_id IN ("
        "  SELECT id FROM users WHERE email LIKE 'test-remail-%@example.com')"
    )
    await conn.execute(
        "DELETE FROM athletes WHERE workspace_id IN ("
        "  SELECT id FROM workspaces WHERE owner_user_id IN ("
        "    SELECT id FROM users WHERE email LIKE 'test-remail-%@example.com'))"
    )
    await conn.execute(
        "DELETE FROM workspaces WHERE owner_user_id IN ("
        "  SELECT id FROM users WHERE email LIKE 'test-remail-%@example.com')"
    )
    await conn.execute(
        "DELETE FROM users WHERE email LIKE 'test-remail-%@example.com'"
    )


async def _scaffold(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    *,
    coach_email: str,
    trainee_email: str | None,
    monthly_pref: bool | None = None,
) -> dict[str, str]:
    """Returns ids needed by the tests.  ``trainee_email`` None creates an
    unclaimed athlete (no user link).  ``monthly_pref`` None leaves the
    prefs row absent (column default = TRUE)."""
    coach_id = await conn.fetchval(
        "INSERT INTO users (email, display_name, preferred_locale) "
        "VALUES ($1, 'Coach', 'en') RETURNING id",
        coach_email,
    )
    trainee_id: str | None = None
    if trainee_email is not None:
        trainee_id = await conn.fetchval(
            "INSERT INTO users (email, display_name, preferred_locale) "
            "VALUES ($1, $2, 'en') RETURNING id",
            trainee_email,
            "Andi Pratama",
        )
        if monthly_pref is not None:
            await conn.execute(
                """
                INSERT INTO user_notification_prefs (user_id, monthly_report)
                VALUES ($1, $2)
                """,
                trainee_id,
                monthly_pref,
            )

    sport_id = await conn.fetchval(
        "SELECT id FROM sports WHERE code = 'padel' LIMIT 1"
    )
    workspace_id = await conn.fetchval(
        """
        INSERT INTO workspaces (
            sport_id, type, name, brand_color, primary_locale,
            plan, trial_ends_at, owner_user_id
        ) VALUES ($1, 'club', 'Email Test Club', '#C66B47', 'en',
                  'free_trial', NOW() + INTERVAL '30 days', $2)
        RETURNING id
        """,
        sport_id,
        coach_id,
    )
    athlete_id = await conn.fetchval(
        """
        INSERT INTO athletes (workspace_id, display_name, joined_at,
                              created_by_id, user_id)
        VALUES ($1, 'Andi Pratama', CURRENT_DATE, $2, $3)
        RETURNING id
        """,
        workspace_id,
        coach_id,
        trainee_id,
    )

    today = date.today()
    period_start = (today.replace(day=1) - timedelta(days=28))
    report_id = await conn.fetchval(
        """
        INSERT INTO reports (
            workspace_id, athlete_id, coach_id,
            period_start, period_end, status, pdf_url, generated_at,
            generation_type
        ) VALUES ($1, $2, $3, $4, $5, 'completed',
                  'http://minio:9000/coachito-dev/test.pdf', $6, 'manual')
        RETURNING id::text
        """,
        workspace_id,
        athlete_id,
        coach_id,
        period_start,
        today,
        datetime.now(UTC),
    )
    return {"report_id": report_id, "trainee_email": trainee_email or ""}


async def test_sends_when_pref_default(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    sent: list[dict[str, Any]],
) -> None:
    """No prefs row → COALESCE default TRUE → email goes out."""
    s = await _scaffold(
        conn,
        coach_email="test-remail-c1@example.com",
        trainee_email="test-remail-andi1@example.com",
        monthly_pref=None,
    )
    ok = await maybe_send_report_ready_email(report_id=s["report_id"])
    assert ok is True
    assert len(sent) == 1
    assert sent[0]["to"] == "test-remail-andi1@example.com"
    assert "Coachito" in sent[0]["subject"]


async def test_sends_when_pref_explicitly_on(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    sent: list[dict[str, Any]],
) -> None:
    s = await _scaffold(
        conn,
        coach_email="test-remail-c2@example.com",
        trainee_email="test-remail-andi2@example.com",
        monthly_pref=True,
    )
    ok = await maybe_send_report_ready_email(report_id=s["report_id"])
    assert ok is True
    assert len(sent) == 1


async def test_skips_when_pref_off(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    sent: list[dict[str, Any]],
) -> None:
    s = await _scaffold(
        conn,
        coach_email="test-remail-c3@example.com",
        trainee_email="test-remail-andi3@example.com",
        monthly_pref=False,
    )
    ok = await maybe_send_report_ready_email(report_id=s["report_id"])
    assert ok is False
    assert sent == []


async def test_skips_when_trainee_has_no_user_account(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    sent: list[dict[str, Any]],
) -> None:
    """Parent-only / un-claimed trainees: athletes.user_id is NULL."""
    s = await _scaffold(
        conn,
        coach_email="test-remail-c4@example.com",
        trainee_email=None,
    )
    ok = await maybe_send_report_ready_email(report_id=s["report_id"])
    assert ok is False
    assert sent == []
