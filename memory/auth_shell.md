---
name: Auth shell + real auth backend (FE step 1 + BE step 2)
description: Mocked-then-real sign-in/sign-up/magic-link flow, route guards, JWT issue+refresh
type: project
---

**Real auth wired end-to-end. Pair 1 step 2 complete.**

**Endpoints** ([apps/api/src/auth/router.py](apps/api/src/auth/router.py)):
- `POST /auth/magic/request` (202) — token = `secrets.token_urlsafe(32)`, stored as sha256(token) → email in Redis with 15-min TTL; emails the raw token in the link via Mailpit.
- `GET /auth/magic/consume?token=…` (200/410) — atomic `GETDEL` makes it one-shot. Find-or-create user by email, issue JWT pair.
- `POST /auth/google` (200/401) — verifies Google id_token via `google-auth`. `GOOGLE_CLIENT_ID` empty in dev → always 401, FE shows fallback.
- `POST /auth/refresh` (200/401) — Bearer refresh token. Rotation: redis stores `refresh:{user_id}:{jti}`; `getdel` revokes the old in the same step that issues the new.

**JWT shape** ([apps/api/src/auth/jwt.py](apps/api/src/auth/jwt.py)):
```
{ sub: user_id, wsid: workspace_id | null, type: 'access' | 'refresh', iat, exp, jti }
```
HS256, signed with `JWT_SECRET`. Access = 15 min, refresh = 30 days.

**Two DB DSNs (carries over from step 0.3):**
- `ALEMBIC_DATABASE_URL` = racademy superuser — for migrations.
- `DATABASE_URL` = racademy_api non-superuser — for runtime so RLS applies. Test cleanup uses the superuser DSN directly via asyncpg.

**FE wiring:**
- Vite dev proxies `/api/*` → `http://api:8000` (Docker service name) with the `/api` prefix stripped. `vite.config.ts` is now bind-mounted in `docker-compose.yml` so config changes don't need a rebuild.
- [apps/web/src/lib/api.ts](apps/web/src/lib/api.ts) wraps fetch, prepends `/api`, attaches `Authorization: Bearer ${token}` from the auth store. Use `{ authenticated: false }` to opt out (sign-in flows), `{ useRefreshToken: true }` for /auth/refresh.
- After sign-in the FE branches via [post-signin.ts](apps/web/src/features/auth/post-signin.ts): `wsid` → `/today`, `null` → `/onboarding/create-workspace` (placeholder until pair 1 step 3 lands).

**Why these choices:**
- *Magic-link hashed in redis*: a snapshot leak of redis lets an attacker enumerate emails but not mint sessions. Cheap insurance.
- *Refresh rotation via redis*: stateless JWT alone can't be revoked. Storing the jti is the minimum state we need; one redis key per active refresh token.
- *Sub-204 silent failure on `/auth/magic/request`*: SMTP fail returns 202 anyway. We don't leak which addresses are deliverable, and operators see the failure in structlog.

**Test gotchas (apps/api/tests/test_auth.py):**
- Redis singleton in `deps.py` binds to whichever event loop first uses it. Tests override the `get_redis` dependency with a per-test client to dodge "Event loop is closed."
- SQLAlchemy's async engine has the same loop-binding problem. The test `client` fixture calls `engine.dispose()` on teardown.
- Tests for /auth/magic/request `monkeypatch.setattr("src.auth.router.send_magic_link_email", ...)` — patch at the import site, not the definition site.

**14/14 tests green.** End-to-end smoke verified: `curl -X POST /api/auth/magic/request` → Mailpit → consume → 200 with JWT → replay → 410.

**StrictMode footgun (fixed):** any effect that performs a one-shot operation (magic-link consume, Google id_token exchange) needs a `useRef(false)` guard set synchronously inside the effect. The "cancelled flag" pattern is *not* enough — the first call still happens and consumes the redis key, then StrictMode's second mount sees a 410 and the user lands on the error screen with the work already done but no JWT stored. Pattern: see [MagicLinkLanding.tsx](apps/web/src/features/auth/MagicLinkLanding.tsx) `startedRef`.

**Open question for the next step:** the access token is held in memory only. Refresh on bootstrap needs a persistence story before any user actually relies on staying logged in across reloads. The httpOnly-cookie path requires a small endpoint change (`Set-Cookie: refresh_token=…`); leaving that decision for when /auth/refresh has an actual consumer.
