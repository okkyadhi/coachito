# Memory index

- [PadelCoach monorepo stack](project_stack.md) — Stack, tooling quirks, scaffold state (steps 0.1–0.3 done)
- [Auth shell (FE step 1)](auth_shell.md) — Mocked sign-in/sign-up/magic-link, route guards, i18n setup
- [Workspaces + RLS context (BE step 4)](workspaces.md) — CRUD, current_user_id GUC, WITH CHECK policies
- [Coach Today + nav shell (FE step 5)](coach_today.md) — /today screen, 5-tab bottom nav, mock data contract
- [Sessions + Trainees endpoints + seed (BE step 6)](sessions_athletes.md) — real /sessions/today and /trainees, tier caching, dev_seed_demo, FE bootstrap
- [Trainees list + Add + WhatsApp (FE step 7)](trainees_add_invite.md) — /trainees screen, /trainees/new modal form, wa.me deep-link
- [Trainees CRUD + invite landing (BE step 8)](trainees_invites.md) — POST/PATCH/DELETE /trainees, public /i/{token} OG landing
- [Coach trainee profile (FE step 9)](coach_trainee_profile.md) — /trainees/:id screen, hand-rolled SVG radar, skills accordion
- [Skill + tier names stay English](feedback_naming_locale.md) — product convention: never translate these to ID
