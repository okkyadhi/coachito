import os
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

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
from src.trainees.notifications_router import router as trainee_notifications_router
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
from src.upgrade_requests.router import router as upgrade_requests_router


# Detect static dir early — needed both for the SPA middleware and the
# file-serving routes registered at the bottom.
_STATIC_DIR = Path(os.environ.get("STATIC_DIR", ""))
_SPA_ACTIVE = _STATIC_DIR.is_dir() and (_STATIC_DIR / "index.html").exists()


class _ApiPrefixMiddleware:
    """Strip a leading ``/api`` from incoming request paths.

    The FE's default ``BASE_URL`` is ``/api`` (see apps/web/src/lib/api.ts),
    but routers here are mounted without that prefix.  In single-container
    production the unprefixed and prefixed paths are the same backend, so
    requests to ``/api/reports`` would fall through to the SPA fallback and
    silently return ``index.html`` (HTTP 200 HTML — the symptom: list calls
    appearing to succeed but returning no data).

    Rewriting the path here keeps the FE host-agnostic: whether it was built
    with ``VITE_API_BASE_URL=""`` (allinone) or left to default to ``/api``,
    the same backend serves both.  We never strip ``/api`` from paths that
    are explicitly meant to land on the SPA (none start with ``/api`` today).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path: str = scope.get("path", "")
            if path == "/api" or path.startswith("/api/"):
                stripped = path[4:] or "/"
                scope = dict(scope)
                scope["path"] = stripped
                raw_path = scope.get("raw_path")
                if isinstance(raw_path, (bytes, bytearray)):
                    scope["raw_path"] = bytes(raw_path)[4:] or b"/"
        await self.app(scope, receive, send)


class _SPABrowserMiddleware:
    """In single-container prod the browser hard-refreshing a SPA route (e.g.
    /reports) sends GET /reports with no Authorization header.  FastAPI
    matches the API route first and returns 401 before the SPA JS even loads.

    This middleware intercepts GET requests that look like browser navigations
    (Accept: text/html, no Bearer token) and serves index.html directly so the
    SPA loads and handles auth and routing client-side.

    API calls always carry Authorization: Bearer, so they are unaffected.
    """

    _SKIP = ("/healthz", "/_debug/", "/assets/")

    def __init__(self, app: ASGIApp, index_html: str) -> None:
        self.app = app
        self._index = index_html

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "GET":
            path: str = scope.get("path", "")
            if not any(path.startswith(p) for p in self._SKIP):
                hdr: dict[bytes, bytes] = dict(scope["headers"])
                accept = hdr.get(b"accept", b"").decode("latin-1")
                auth = hdr.get(b"authorization", b"").decode("latin-1")
                # Browser navigation sends Accept: text/html but never an
                # Authorization header — serve the SPA shell so React Router
                # takes over client-side.
                if "text/html" in accept and not auth:
                    from starlette.responses import FileResponse as _FR
                    await _FR(self._index)(scope, receive, send)
                    return
        await self.app(scope, receive, send)


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

    class _NoopDeathPenalty:
        """Replaces UnixSignalDeathPenalty (SIGALRM) which only works in the
        main thread.  Job-level timeouts are handled instead via asyncio.wait_for
        inside the job function itself."""
        def __init__(self, timeout: int, exception: type, job_id: str | None = None) -> None:
            pass
        def __enter__(self) -> "_NoopDeathPenalty":
            return self
        def __exit__(self, *_: object) -> bool:
            return False
        def cancel(self) -> None:
            pass
        def handle_death_penalty(self, *_: object) -> None:
            pass

    class _ThreadSafeWorker(SimpleWorker):
        death_penalty_class = _NoopDeathPenalty

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

# SPA browser-navigation fallback — must be added AFTER CORS so it is the
# outermost wrapper and intercepts before FastAPI's route matching.
if _SPA_ACTIVE:
    app.add_middleware(
        _SPABrowserMiddleware,
        index_html=str(_STATIC_DIR / "index.html"),
    )

# /api path rewrite — registered last so it runs first.  Production FE built
# with the default BASE_URL ("/api") calls "/api/reports"; the routers are
# mounted bare ("/reports"), so without this shim every API request would
# fall through to the SPA fallback and silently return index.html.
app.add_middleware(_ApiPrefixMiddleware)

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
app.include_router(trainee_notifications_router)  # GET /trainees/me/notifications
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
app.include_router(upgrade_requests_router)  # POST /me/upgrade-requests + /admin/upgrade-requests


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
#
# Browser hard-refresh of SPA routes (e.g. /reports) is handled by
# _SPABrowserMiddleware above — it intercepts before route matching so
# the API endpoint never sees the unauthenticated browser GET.
if _SPA_ACTIVE:
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
