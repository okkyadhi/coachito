---
name: Workspaces CRUD + RLS context (BE step 4)
description: POST /workspaces, GET /workspaces/mine, switch; current_user_id GUC + WITH CHECK policies
type: project
---

**Pair 1 step 4 done.** 23/23 tests pass.

**Endpoints** ([apps/api/src/workspaces/router.py](apps/api/src/workspaces/router.py)):
- `POST /workspaces` (201) — body `{type, name, city?, brand_color?, primary_locale}`. Server fills `sport_id` from the seeded `padel` row, `plan='free_trial'`, `trial_ends_at = now+30d`. Creates the workspace + active membership (`club_admin` if club, `coach` if personal) in one transaction. Returns `{workspace, tokens{access, refresh, workspace_id}}` — the FE must swap the rotated pair into the auth store.
- `GET /workspaces/mine` (200) — joins workspaces × memberships, filtered by `user_id` from the JWT. Cross-workspace by design (the user might belong to multiple).
- `POST /workspaces/{id}/switch` (200/403) — validates an active membership exists, then mints a new JWT with `wsid` set. 403 if you're not a member.

**RLS context** ([apps/api/src/middleware/rls.py](apps/api/src/middleware/rls.py)):
- `db_with_rls` is a FastAPI dependency that, on every authenticated request, sets two Postgres GUCs from the access JWT: `app.current_workspace_id` (from `wsid`) and `app.current_user_id` (from `sub`).
- Empty string → `current_workspace_id()` / `current_user_id()` returns NULL — policies fall back to "platform data only".
- Use `Depends(db_with_rls)` on routes that read tenant-scoped tables. `Depends(get_session)` for routes that don't (auth, healthz).

**Two RLS policy fixes shipped in migrations 0009 + 0010:**
1. *Cross-workspace listing*: the original `workspace_memberships` policy was `USING (workspace_id = current_workspace_id())` — too strict to answer "what workspaces do I belong to?" Migration 0009 added `current_user_id()` helper and replaced the policy with `USING (user_id = current_user_id() OR workspace_id = current_workspace_id())`.
2. *Creating a workspace while scoped to another one*: Postgres reuses `USING` for INSERT validation when there's no `WITH CHECK` clause. Creating workspace W2 from a session scoped to W1 failed because `W2.id != current_workspace_id()`. Migration 0010 added explicit `WITH CHECK (owner_user_id = current_user_id() OR current_user_id() IS NULL)` to `workspaces` and a matching check to `workspace_memberships`. Going forward, **every tenant-scoped table whose policy is "workspace_id matches the GUC" needs a WITH CHECK clause for the INSERT path** — either ownership-based or just `current_workspace_id() IS NOT NULL`.

**Token rotation helper:** `issue_and_register_token_pair` lives in [apps/api/src/auth/service.py](apps/api/src/auth/service.py). Used by both `/auth/*` and `/workspaces/*` endpoints. Each call issues a fresh access+refresh pair and registers the refresh jti in redis for rotation.

**FE wiring** ([apps/web/src/features/workspaces/](apps/web/src/features/workspaces/)):
- `workspace-api.ts` — camelCase TS shapes; converts to/from the snake_case wire format.
- `CreateWorkspaceScreen.tsx` — club/personal segmented control, name + city + locale fields, owns the rotation: pulls the new tokens from the create response and `signIn()`s them back into the store before navigating to `/today`.
- Router guard `RequireWorkspace` redirects authenticated-but-unaffiliated users to `/onboarding/create-workspace`.

**How to apply:**
- Any new endpoint that reads tenant tables: depend on `db_with_rls` from `src.middleware.rls`.
- Any new tenant table created in a migration: add a `WITH CHECK` clause when you create the policy, not "later" — same-transaction inserts (workspace + membership in one go) routinely trip the implicit-USING-as-WITH-CHECK default.

**Open question for next step:** workspaces table doesn't have FORCE ROW LEVEL SECURITY (only USING + WITH CHECK, ENABLE). Need to double-check that's deliberate vs. an oversight before the first tenant goes live; with the racademy_api role being non-superuser, ENABLE alone is enough, but if any production role ends up being the table owner, only FORCE blocks the bypass.
