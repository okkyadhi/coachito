"""End-to-end happy-path test — coach signs up, invites a trainee, the
trainee claims, the coach schedules a session, scores skills, publishes the
assessment, generates a report, and the trainee sees the report and
receives an email.  Single deliberately-long test that reads top-to-bottom
like a user story; each step is a freestanding assertion against a real
ASGI request.

The intent isn't to replace the focused unit tests (those still cover
edge cases) — it's an integration smoke that fails fast when any of the
modules talk past each other.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import asyncpg
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src import deps as deps_module
from src.assessments import draft_router as draft_module
from src.config import settings
from src.db import session as session_module
from src.main import app
from src.reports.jobs import generate_report_pdf_async

from ._test_helpers import SUPERUSER_DSN, create_workspace, sign_in


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
async def redis() -> Redis:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def client(redis: Redis) -> AsyncClient:
    app.dependency_overrides[deps_module.get_redis] = lambda: redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(deps_module.get_redis, None)
    await session_module.engine.dispose()


@pytest.fixture
async def captured_magic_links(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    cap: list[dict[str, str]] = []

    async def fake_send(*, email: str, link: str) -> None:
        cap.append({"email": email, "link": link})

    monkeypatch.setattr("src.auth.router.send_magic_link_email", fake_send)
    return cap


@pytest.fixture
def captured_report_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture every aiosmtplib.send invoked by the report-ready job."""
    cap: list[dict[str, Any]] = []

    async def fake_send(msg: Any, **kwargs: Any) -> None:
        cap.append({
            "to": msg["To"],
            "subject": msg["Subject"],
        })

    monkeypatch.setattr("src.reports.emails.aiosmtplib.send", fake_send)
    return cap


@pytest.fixture(autouse=True)
def _ai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # The draft-summary call path imports the Gemini client at module load;
    # set a sentinel key so RuntimeError isn't raised before the call hits
    # the stubbed http client (we don't call /draft-summary in this test
    # but the import shouldn't 503 by accident).
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")


@pytest.fixture(autouse=True)
async def _ai_http_stub() -> None:
    """Defang the AI HTTP client so tests never reach Google."""
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "stub"}]}}]},
        )
    app.dependency_overrides[draft_module.get_http_client] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(_handler),
    )
    yield
    app.dependency_overrides.pop(draft_module.get_http_client, None)


@pytest.fixture(autouse=True)
async def _cleanup() -> None:
    yield
    conn = await asyncpg.connect(SUPERUSER_DSN)
    try:
        await conn.execute(
            "DELETE FROM reports WHERE workspace_id IN ("
            "  SELECT id FROM workspaces WHERE owner_user_id IN ("
            "    SELECT id FROM users WHERE email LIKE 'test-e2e-%@example.com'))"
        )
        await conn.execute(
            "DELETE FROM workspaces WHERE owner_user_id IN ("
            "  SELECT id FROM users WHERE email LIKE 'test-e2e-%@example.com')"
        )
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test-e2e-%@example.com'"
        )
    finally:
        await conn.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── The story ────────────────────────────────────────────────────


async def test_happy_path_coach_assesses_publishes_reports_trainee_sees(
    client: AsyncClient,
    captured_magic_links: list[dict[str, str]],
    captured_report_emails: list[dict[str, Any]],
) -> None:
    """Single integration story.  If any of the modules drift on each
    other's contract, this fails — that's the value over per-module unit
    tests."""

    # ── Step 1: Coach signs up via magic link, creates a club workspace ──
    coach = await sign_in(
        client, "test-e2e-coach@example.com", captured_magic_links,
    )
    coach_user_id = coach["user"]["id"]
    ws_payload = await create_workspace(
        client, coach["access_token"], name="Senayan Padel E2E",
    )
    coach_token = ws_payload["tokens"]["access_token"]
    workspace_id = ws_payload["workspace"]["id"]

    # The post-create token carries the workspace context.
    assert ws_payload["workspace"]["name"] == "Senayan Padel E2E"
    assert ws_payload["workspace"]["type"] == "club"

    # ── Step 2: Coach invites a trainee.  The single POST /trainees call
    #          creates the athlete + an invite token.                   ──
    create_resp = await client.post(
        "/trainees",
        json={"name": "Andi Pratama", "phone_e164": "+62811222333444"},
        headers=_auth(coach_token),
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    athlete_id = created["trainee"]["id"]
    invite_code = created["invite"]["code"]
    assert created["trainee"]["display_name"] == "Andi Pratama"

    # ── Step 3: Trainee signs up via magic link + claims the invite ──
    trainee = await sign_in(
        client, "test-e2e-andi@example.com", captured_magic_links,
    )
    claim_resp = await client.post(
        f"/invites/{invite_code}/claim",
        headers=_auth(trainee["access_token"]),
    )
    assert claim_resp.status_code == 200, claim_resp.text
    trainee_tokens = claim_resp.json()
    trainee_token = trainee_tokens["access_token"]
    assert trainee_tokens["user"]["role"] == "trainee"

    # /trainees/me/home should now resolve (RLS lets the trainee read
    # exactly their own row).
    home = await client.get("/trainees/me/home", headers=_auth(trainee_token))
    assert home.status_code == 200, home.text
    assert home.json()["trainee_first_name"] == "Andi"
    assert home.json()["has_assessment"] is False  # nothing yet

    # ── Step 4: Coach schedules a session for tomorrow ──
    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0,
    )
    session_resp = await client.post(
        "/sessions",
        json={
            "athlete_id": athlete_id,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_min": 60,
            "court": "Court 1",
            "focuses": ["drilling", "technique_focus"],
        },
        headers=_auth(coach_token),
    )
    assert session_resp.status_code == 201, session_resp.text
    session = session_resp.json()
    session_id = session["id"]
    assert session["focuses"] == ["drilling", "technique_focus"]

    # ── Step 5: Coach scores a few skills against that session ──
    skills_resp = await client.get("/skills", headers=_auth(coach_token))
    assert skills_resp.status_code == 200
    skill_by_code = {s["code"]: s["id"] for s in skills_resp.json()["skills"]}
    fh_id = skill_by_code["PADEL_TECH_FH"]
    bh_id = skill_by_code["PADEL_TECH_BH"]
    bandeja_id = skill_by_code["PADEL_TECH_BANDEJA"]

    save_resp = await client.post(
        "/assessments",
        json={
            "athlete_id": athlete_id,
            "session_id": session_id,
            "summary": "Solid groundstrokes today; bandeja still rushing.",
            "scores": [
                {"skill_id": fh_id, "level": 4},
                {"skill_id": bh_id, "level": 3},
                {"skill_id": bandeja_id, "level": 2,
                 "note": "Hold height, slow the swing."},
            ],
        },
        headers=_auth(coach_token),
    )
    assert save_resp.status_code == 200, save_resp.text
    assessment = save_resp.json()
    assessment_id = assessment["id"]
    assert assessment["status"] == "draft"
    assert len(assessment["scores"]) == 3

    # ── Step 6: Coach publishes the assessment.  Tier recalc fires; the
    #          trainee should see has_assessment=true on /home next.    ──
    publish_resp = await client.post(
        f"/assessments/{assessment_id}/publish",
        json={"force_empty": False},
        headers=_auth(coach_token),
    )
    assert publish_resp.status_code == 200, publish_resp.text
    published = publish_resp.json()
    assert published["status"] == "published"
    assert published["published_at"] is not None

    # ── Step 7: Trainee re-fetches /home — assessment-derived data flows ──
    home2 = (
        await client.get("/trainees/me/home", headers=_auth(trainee_token))
    ).json()
    assert home2["has_assessment"] is True
    technical = next(
        c for c in home2["category_averages"] if c["category"] == "technical"
    )
    # FH=4, BH=3, Bandeja=2 → mean 3.0 (rounded to 1 dp).
    assert technical["skills_rated"] == 3
    assert technical["average"] == 3.0

    # /skills/me/overview also reflects the new state.
    skills_overview = (
        await client.get("/skills/me/overview", headers=_auth(trainee_token))
    ).json()
    assert skills_overview["overall"]["assessed_count"] == 3
    assert skills_overview["overall"]["average"] == 3.0
    # focus_suggestion should point at the lowest-scored blocker — Bandeja
    # (level 2) is the lowest skill scored, but tier blocker takes priority.
    assert skills_overview["focus_suggestion"] is not None

    # ── Step 8: Coach generates a per-session report ──────────────────
    report_create = await client.post(
        "/reports",
        json={"athlete_id": athlete_id, "session_id": session_id},
        headers=_auth(coach_token),
    )
    assert report_create.status_code == 202, report_create.text
    report_id = report_create.json()["report"]["id"]
    assert report_create.json()["report"]["status"] == "pending"

    # Invoke the worker directly (faster + deterministic in tests).
    result = await generate_report_pdf_async(report_id)
    assert result["status"] == "completed", result
    assert result["bytes"] > 1000  # real PDF

    # ── Step 9: Report-ready email should have fired ──────────────────
    assert len(captured_report_emails) == 1, captured_report_emails
    assert captured_report_emails[0]["to"] == "test-e2e-andi@example.com"
    assert "Coachito" in captured_report_emails[0]["subject"]

    # ── Step 10: Trainee sees the report in /trainees/me/reports ──────
    trainee_reports = await client.get(
        "/trainees/me/reports", headers=_auth(trainee_token),
    )
    assert trainee_reports.status_code == 200, trainee_reports.text
    rows = trainee_reports.json()["reports"]
    assert len(rows) == 1
    assert rows[0]["id"] == report_id
    assert rows[0]["pdf_url"].endswith(".pdf")
    assert rows[0]["coach_display_name"]  # not empty

    # ── Step 11: Coach completes the session (records keep flowing) ──
    complete_resp = await client.post(
        f"/sessions/{session_id}/complete",
        headers=_auth(coach_token),
    )
    assert complete_resp.status_code == 200, complete_resp.text
    assert complete_resp.json()["status"] == "completed"

    # ── Step 12: Locality privacy — a second trainee in the same
    #            workspace must NOT see the first trainee's report.    ──
    other_create = await client.post(
        "/trainees",
        json={"name": "Budi Santoso", "phone_e164": "+62811222333555"},
        headers=_auth(coach_token),
    )
    other_invite = other_create.json()["invite"]["code"]
    other = await sign_in(
        client, "test-e2e-budi@example.com", captured_magic_links,
    )
    other_claim = await client.post(
        f"/invites/{other_invite}/claim",
        headers=_auth(other["access_token"]),
    )
    other_token = other_claim.json()["access_token"]

    other_reports = await client.get(
        "/trainees/me/reports", headers=_auth(other_token),
    )
    assert other_reports.status_code == 200
    assert other_reports.json()["reports"] == []

    # Budi's home should also be empty of Andi's data.
    other_home = (
        await client.get("/trainees/me/home", headers=_auth(other_token))
    ).json()
    assert other_home["has_assessment"] is False

    # And the email fixture shows only ONE report email — Andi's.
    assert [e["to"] for e in captured_report_emails] == [
        "test-e2e-andi@example.com"
    ]

    # ── Step 13: Trainee can turn off report emails; next report skips ──
    pref_off = await client.patch(
        "/users/me",
        json={"notifications": {"monthly_report": False}},
        headers=_auth(trainee_token),
    )
    assert pref_off.status_code == 200

    # Generate another report; the email path should stay silent.
    another = await client.post(
        "/reports",
        json={
            "athlete_id": athlete_id,
            "period_start": (date.today() - timedelta(days=30)).isoformat(),
            "period_end": date.today().isoformat(),
        },
        headers=_auth(coach_token),
    )
    assert another.status_code == 202
    await generate_report_pdf_async(another.json()["report"]["id"])
    # Still exactly the one email captured earlier.
    assert len(captured_report_emails) == 1
