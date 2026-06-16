---
name: Sessions + Trainees endpoints + dev seed (BE step 6)
description: GET /sessions/today, GET /trainees, tier caching, demo data, FE bootstrap
type: project
---

**Pair 3 step 6 done.** 36/36 tests green (13 new). FE Today screen now reads real data from the BE.

**Endpoints**
- `GET /sessions/today` ([sessions/router.py](apps/api/src/sessions/router.py)) — coach-scoped (`s.coach_id = JWT.sub`), today's calendar day, sorted ASC by scheduled_at. Each row joins the athlete + their cached `current_tier_id` + a subquery for `last_assessed_at` (MAX of assessments).
- `GET /trainees` ([athletes/router.py](apps/api/src/athletes/router.py)) — `?q=` ILIKE substring (uses the pg_trgm GIN index from migration 0003), `?limit=` 1–100 default 25, `?cursor=` opaque base64-encoded offset. Default sort: most recently assessed first, with NULLs last.

**Schema changes**
- *Migration 0011* — `athletes.current_tier_id UUID NULL REFERENCES tiers(id)`. Cached per-athlete tier so list/today queries don't recompute it. Tier-write will happen in the assessment-create endpoint (future step); for now `dev_seed_demo.py` populates it.
- *Migration 0012* — `sessions.court VARCHAR(50) NULL`. The data-model originally omitted it; the coach-today screen renders it in "Up next" so adding it now.

**Critical auth-flow fix (also in this step)**
The magic-link consume, Google sign-in, and refresh endpoints all call `get_primary_workspace_id` which reads from `workspace_memberships` — a table with FORCE ROW LEVEL SECURITY and a policy keyed off `current_user_id()`. Before this step those endpoints didn't set the GUC, so the membership rows were invisible *to the very query trying to look them up*, and every existing-user sign-in returned `wsid: null`. Fix: [`set_user_context(db, user_id)`](apps/api/src/middleware/rls.py) sets `app.current_user_id` after we identify the user but before we read their memberships. Called from all three auth flows.

**Tier caching pattern**
- `current_tier_id` is denormalized; tier-write logic must update it whenever a new assessment lands. The recomputation function (lives in [scripts/dev_seed_demo.py:_compute_tier_id](apps/api/scripts/dev_seed_demo.py) for now) walks tiers descending by display_order, returns the first one whose every requirement is met by `MAX(assessments.level) per skill`.
- BEGINNER has zero requirements, so it always matches as the floor.
- TODO: lift `_compute_tier_id` into a shared `tiers/service.py` once we have the assessment-create endpoint.

**Dev seed**
`docker compose exec api python -m scripts.dev_seed_demo` (re-runnable; resets athletes/sessions/assessments deterministically). Creates `demo@racademy.dev` as Coach Novia of "Senayan Padel Club" with 8 Indonesian-named trainees, 5 scheduled today (08:00 / 09:30 / 11:00 / 15:00 / 17:30), 50 assessments. Sign in with that email to land in the demo workspace.

**FE wiring**
- [today-api.ts](apps/web/src/features/today/today-api.ts) — replaced the mock with `api.get('/sessions/today')`, kept the TS shape stable so `CoachTodayScreen.tsx` doesn't change. `MOCK_EMPTY` flag is gone; empty workspaces naturally produce `[]` from the BE.
- [use-auth-bootstrap.ts](apps/web/src/features/auth/use-auth-bootstrap.ts) — on app start, if there's a persisted refresh token, call `/auth/refresh` to rotate before the router mounts. Without this, a reload after the 15-min access expiry would have stale tokens in the store and every protected call would 401. StrictMode ref-guarded so dev's double-mount doesn't burn through the one-shot rotation.

**Three sharp edges to know**

1. **uvicorn `--reload` is flaky on macOS bind mounts.** When you change Python in `apps/api/src/`, you sometimes need an explicit `docker compose restart api` for the change to take. I hit this once on this step (the SQL fix didn't propagate). Adding a hard `restart` after suspect changes is the fast diagnostic.

2. **SQLAlchemy `text()` mis-parses `:param::text` casts.** It treats `::text` as part of the parameter name. Workaround: pass the wildcard pattern from Python (`'%' + q + '%'` or `'%'` for "no filter") and use `ILIKE :pattern` unconditionally. The Postgres `IS NULL` branch + cast doesn't survive the rewrite.

3. **asyncpg can't infer the type of an int passed into a `'$1 || ' days'::interval` expression** because it sees concatenation context first and infers `text`. Use `make_interval(days => $1)` instead — explicit integer-typed argument.
