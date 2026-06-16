import os
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
from src.admin.router import router as admin_router


def _start_inprocess_worker() -> None:
    """Spawn an RQ worker on a daemon thread.

    SimpleWorker (no fork) is required: the standard RQ Worker forks per job
    which is incompatible with asyncio/uvicorn in the same process.

    Python only allows signal.signal() calls from the main thread, so we
    subclass SimpleWorker and skip _install_signal_handlers entirely — the
    daemon thread exits automatically when the main process ends, so graceful
    shutdown via signals isn't needed here anyway.
    """
    from redis import Redis as SyncRedis
    from rq import Queue, SimpleWorker

    from src.config import settings

    class _ThreadSafeWorker(SimpleWorker):
        def _install_signal_handlers(self) -> None:
            pass  # cannot install signal handlers from a non-main thread

    def _run() -> None:
        conn = SyncRedis.from_url(settings.redis_url)
        worker = _ThreadSafeWorker(
            [Queue("default", connection=conn)], connection=conn
        )
        worker.work(with_scheduler=False)

    threading.Thread(target=_run, name="rq-inprocess", daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_sentry("api")
    if os.environ.get("RUN_WORKER_INPROCESS") == "1":
        _start_inprocess_worker()
    yield
    await close_redis()
    await close_ai_http_client()


app = FastAPI(
    title="Coachito API",
    version="0.0.0",
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)

# CORS — read from env so each deployment lists only its own FE origins.
# In dev, the Vite proxy handles same-origin so no entries are needed;
# in prod (Railway, Fly, etc.) where the FE is on a separate origin, set
# ALLOWED_ORIGINS to a comma-separated list of full URLs.
_allowed_origins = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
app.include_router(admin_router)             # /admin/* — platform admin dashboard


@app.get("/healthz")
async def health_check() -> JSONResponse:
    """Subsystem health probe — DB / Redis / S3 / SMTP.
    HTTP 200 when all green, 503 with the failure detail otherwise.
    """
    result = await collect_health()
    code = 503 if result["status"] == "fail" else 200
    return JSONResponse(content=result, status_code=code)


@app.get("/_debug/boom", include_in_schema=False)
async def debug_boom() -> None:
    """Deliberate-failure endpoint for Sentry verification.  Not exposed in
    OpenAPI; only meaningful when SENTRY_DSN is set."""
    raise RuntimeError("intentional Sentry probe")


# ── Static FE (single-container deploy) ──────────────────────────
# When STATIC_DIR points at a Vite build, FastAPI serves the SPA on the
# same origin as the API.  Hashed assets get a long cache; any other
# unmatched path falls back to index.html so React Router can take over.
# In dev compose, STATIC_DIR isn't set → these routes are inert and the
# FE is served by the separate `web` container.
_STATIC_DIR = Path(os.environ.get("STATIC_DIR", ""))
if _STATIC_DIR.is_dir() and (_STATIC_DIR / "index.html").exists():
    _ASSETS_DIR = _STATIC_DIR / "assets"
    if _ASSETS_DIR.is_dir():
        app.mount(
            "/assets", StaticFiles(directory=_ASSETS_DIR), name="assets"
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str) -> FileResponse:
        # Serve a top-level static file (favicon, manifest, sw.js, …) if
        # it actually exists; otherwise fall back to index.html so the
        # SPA router handles the path on the client.
        candidate = _STATIC_DIR / full_path if full_path else None
        if (
            candidate is not None
            and candidate.is_file()
            and _STATIC_DIR.resolve() in candidate.resolve().parents
        ):
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")
