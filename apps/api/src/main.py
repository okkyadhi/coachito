from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.middleware.request_id import RequestIdMiddleware
from src.observability.health import collect as collect_health
from src.observability.sentry import init_sentry

from src.assessments.draft_router import (
    close_http_client as close_ai_http_client,
)
from src.assessments.draft_router import router as assessments_draft_router
from src.assessments.router import router as assessments_router
from src.curriculum.router import router as curriculum_router
from src.feedback.router import (
    assessment_feedback_router,
    feedback_router,
)
from src.athletes.me import router as trainee_me_router
from src.athletes.profile import router as trainee_profile_router
from src.athletes.router import router as athletes_router
from src.coaches.router import router as coaches_router
from src.match_maker.router import router as match_maker_router
from src.trainees.coaches_router import router as trainee_coaches_router
from src.trainees.reports_router import router as trainee_reports_router
from src.auth.router import router as auth_router
from src.deps import close_redis
from src.invites.router import invites_router
from src.invites.router import public_router as invites_public_router
from src.invites.router import trainees_router as invites_trainees_router
from src.reports.router import router as reports_router
from src.sports.router import router as sports_router
from src.sessions.router import router as sessions_router
from src.skills.me_router import router as skills_me_router
from src.skills.router import router as skills_router
from src.uploads.avatar import router as uploads_avatar_router
from src.uploads.router import router as uploads_router
from src.users.me_router import router as users_me_router
from src.workspaces.members import router as workspaces_members_router
from src.workspaces.public import router as workspaces_public_router
from src.workspaces.router import router as workspaces_router
from src.workspaces.settings import router as workspaces_settings_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_sentry("api")
    yield
    await close_redis()
    await close_ai_http_client()


app = FastAPI(
    title="Coachito API",
    version="0.0.0",
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)

app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(workspaces_settings_router)  # PATCH /workspaces/me
app.include_router(workspaces_members_router)  # GET/POST/PATCH/DELETE coach members
app.include_router(workspaces_public_router)   # GET /workspaces/public/{slug}
app.include_router(uploads_router)             # POST /uploads/logo/sign
app.include_router(uploads_avatar_router)      # POST /uploads/avatar/sign
app.include_router(users_me_router)            # GET/PATCH /users/me
app.include_router(trainee_me_router)         # GET /trainees/me/home (must precede /trainees/{id})
app.include_router(trainee_coaches_router)    # GET /trainees/me/coaches
app.include_router(trainee_reports_router)    # GET /trainees/me/reports
app.include_router(coaches_router)            # GET /coaches/{id}
app.include_router(trainee_profile_router)    # GET /trainees/{id}/profile
app.include_router(athletes_router)
app.include_router(sessions_router)
app.include_router(assessments_router)
app.include_router(assessments_draft_router)   # POST /assessments/{id}/draft-summary
app.include_router(assessment_feedback_router)  # POST/GET /assessments/{id}/feedback
app.include_router(feedback_router)             # /feedback/{id} + /feedback/inbox
app.include_router(reports_router)
app.include_router(match_maker_router)   # /events + nested participants/teams (Phase 1)
app.include_router(sports_router)        # /workspaces/me/sports, /athletes|memberships/{id}/sports
app.include_router(skills_me_router)  # /skills/me/* (must precede /skills)
app.include_router(skills_router)
app.include_router(curriculum_router)  # /curriculum/skills, /tiers, /feedback
app.include_router(invites_trainees_router)  # POST /trainees/{id}/invite
app.include_router(invites_router)           # POST /invites/{token}/claim
app.include_router(invites_public_router)    # GET  /i/{token}


@app.get("/healthz")
async def health_check() -> JSONResponse:
    """Subsystem health probe — DB / Redis / S3 / SMTP.
    HTTP 200 when all green, 503 with the failure detail otherwise.
    """
    result = await collect_health()
    code = 200 if result["status"] == "ok" else 503
    return JSONResponse(content=result, status_code=code)


@app.get("/_debug/boom", include_in_schema=False)
async def debug_boom() -> None:
    """Deliberate-failure endpoint for Sentry verification.  Not exposed in
    OpenAPI; only meaningful when SENTRY_DSN is set."""
    raise RuntimeError("intentional Sentry probe")
