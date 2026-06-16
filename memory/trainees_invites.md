---
name: Trainees create/update/delete + invite landing (BE step 8)
description: POST/PATCH/DELETE /trainees, POST /trainees/{id}/invite, GET /i/{token} with branded OG
type: project
---

**Pair 4 step 8 done.** 46/46 tests green (10 new). FE add-trainee flow now creates real rows; WhatsApp invite links unfurl with workspace branding.

**Endpoints**
- `POST /trainees` — creates athlete + initial invite in one transaction. Body: `{name, phone_e164, date_of_birth?, parent_phone_e164?}`. Phone validation accepts whitespace and strips it. Returns `{trainee, invite{id, code, phone_e164, expires_at, landing_url}}`.
- `PATCH /trainees/{id}` — updates `display_name` / `date_of_birth` / `notes`. Recomputes `is_minor` if DOB changes.
- `DELETE /trainees/{id}` — soft-delete via `archived_at`. 204 No Content. Subsequent `GET /trainees` filters it out.
- `POST /trainees/{id}/invite` — re-invite. Revokes all pending invites for that athlete (sets `revoked_at = NOW()`) then mints a new one. Idempotency-friendly.
- `GET /i/{token}` — **public, no auth.** Returns HTML with workspace-branded OG meta tags + `Cache-Control: public, max-age=86400` so CDN-fetching link unfurlers (WhatsApp / iMessage) cache the response.

**Invite token format** ([invites/service.py](apps/api/src/invites/service.py)) — `{workspace_slug}-{trainee_handle}-{rand8}` per docs/07. Example: `sen-andi-_OuM_1zI`. Slug derived from `workspace.slug` else first 3 ASCII chars of name (lowercase). Handle = first word of trainee's name, ASCII-only, ≤8 chars. Random suffix = 8 URL-safe chars from `secrets.token_urlsafe(6)`.

**Public landing page** ([invites/router.py](apps/api/src/invites/router.py), [templates/invite_landing.html](apps/api/templates/invite_landing.html)) — minimal centered hero, brand mark, workspace name + coach name in a card, two CTAs (continue / sign in), expiry footnote. Locale picked from `workspaces.primary_locale`. Renders the same template for invalid/expired states with localized title + lead. Returns:
- 200 + full unfurl tags for valid tokens
- 410 GONE for expired/revoked/claimed (template still includes branded OG so a stale unfurl still shows the right club name)
- 404 for unknown tokens

**Key architectural choice: bypass RLS for the public landing**
- The invites table has FORCE RLS with `USING workspace_id = current_workspace_id()`. A public endpoint has no JWT → no workspace context → the row would be invisible to the very lookup that's supposed to find it.
- Fix: [og_landing.py](apps/api/src/invites/og_landing.py) opens its own asyncpg connection using the superuser DSN (from `ALEMBIC_DATABASE_URL` env, falling back to `DATABASE_URL`) for the lookup query. Documented in the file; the TODO is to replace with a `SECURITY DEFINER` SQL function granted to racademy_api when we want a cleaner pattern.

**Migration 0013**
Added explicit `WITH CHECK (workspace_id = current_workspace_id())` to athletes / sessions / assessments / reports / invites / subscriptions. Previously these policies had only USING (which Postgres reuses for INSERT validation by default — fine when wsid matches, but explicit is better than implicit and matches the workspaces / memberships fix from migration 0010).

**Vite proxy extension** ([apps/web/vite.config.ts](apps/web/vite.config.ts))
Added `/i` → `http://api:8000` (no prefix rewrite). The WhatsApp invite link the FE generates points to `${web_url}/i/${code}`; the FE proxy forwards the unfurl request to the BE so a single hostname serves both the SPA and the public landing. Vite would otherwise intercept `/i/*` and serve the SPA shell with a 200 — masking the failure.

**FE wiring** ([trainees-api.ts](apps/web/src/features/trainees/trainees-api.ts), [AddTraineeScreen.tsx](apps/web/src/features/trainees/AddTraineeScreen.tsx))
- `createTrainee` now hits real `POST /trainees`. Returns `landingUrl` from the BE instead of constructing it client-side.
- `AddTraineeScreen` uses the BE-supplied landing URL when assembling the wa.me message, so the FE doesn't need to know the canonical host.

**Two gotchas captured here for next time**
1. **Starlette `TemplateResponse` signature flipped** in 1.0: it's now `(request, name, context, ...)` — the legacy `(name, context_dict_with_request)` form raises `TypeError: unhashable type: 'dict'` because the dict gets used as a cache key. If you see that error, swap positional order.
2. **Vite proxies only match prefixes you list explicitly.** Anything not under `/api`, `/i`, etc. falls through to the SPA. When adding a new BE-served public route (e.g., a future `/share/{token}` or `/og/{kind}`), add it to `server.proxy` too.

**Open followups**
- Capture parent_phone properly (right now it goes into `athletes.notes` as a marker line — a real `athletes.parent_phone_e164` column or a join through `user_guardians` should ship with the parent-account flow).
- Migrate to `SECURITY DEFINER public_invite_lookup(token)` SQL function instead of opening a separate asyncpg connection from the public route.
- The 410 GONE template path doesn't render the "request a new invite" CTA yet — just shows expired copy. Add a "contact your coach" action when the invite-resend flow is exposed in the trainee profile UI.
