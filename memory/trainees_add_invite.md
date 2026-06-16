---
name: Trainees list + Add trainee + WhatsApp invite (FE step 7)
description: /trainees list with search/empty state, /trainees/new modal form, wa.me share
type: project
---

**Pair 4 step 7 done.** Trainees tab renders real data from BE step 6; "+" → modal form → WhatsApp hand-off.

**New routes**
- `/trainees` (under CoachShell) — list with search + empty state + "+" button. Uses `useQuery(['trainees', q || null])` against [`listTrainees`](apps/web/src/features/trainees/trainees-api.ts).
- `/trainees/new` (full-screen, no bottom tab bar) — modal-style form. Guarded by `RequireWorkspace` directly (not `CoachShellGate`) so it doesn't render inside the nav layout.

**Form** ([trainee-form.ts](apps/web/src/features/trainees/trainee-form.ts))
- zod schema with `.transform()` that strips whitespace before E.164 validation (`/^\+[1-9]\d{1,14}$/`).
- React Hook Form via `@hookform/resolvers/zod`. Error messages are i18n *keys* (e.g. `phone.invalid`); the screen runs them through `t()` so locale flips the wording.
- Required: `name`, `phone`. Optional: `dateOfBirth` (YYYY-MM-DD), `parentPhone`.
- Coaching section (starting tier, lead coach) is read-only at MVP — picker UI ships later. Tier defaults to BEGINNER; coach defaults to the signed-in user's `displayName`.

**WhatsApp hand-off** ([whatsapp.ts](apps/web/src/features/trainees/whatsapp.ts))
- `buildWhatsAppUrl(phoneE164, message)` → `https://wa.me/<digits-only>?text=<urlencoded>`. The `+` is stripped because wa.me expects pure digits.
- `firstName()` pulls the leading word so the templated message reads "Hi Andi" not "Hi Andi Pratama".
- Verified live: `+62 812 3456 7890` → phone path `6281234567890`; decoded `text` param matches the templated message verbatim including newlines + em-dash.

**Message templates** (in [en.json](apps/web/src/locales/en.json) / [id.json](apps/web/src/locales/id.json), key `trainees.inviteMessage`) match docs/07 §2 word-for-word. Passed through `t(key, { lng: locale, name, coach, workspace, link })` so the trainee's preferred-locale variant is sent. Workspace name is currently the placeholder `racademy` — real workspace fetch is still on the followup list from step 5.

**Mocked `createTrainee`** ([trainees-api.ts](apps/web/src/features/trainees/trainees-api.ts))
- Returns `{ trainee, invite }` after 250ms. Invite code follows the `{slug}-{handle}-{random4}` shape from docs/07.
- The real BE `POST /trainees` (with invite mint) is the next step (pair 4 BE step 8).
- After success the FE invalidates `['trainees']` so the list query refetches when the user returns to /trainees.

**Two `exactOptionalPropertyTypes` snags fixed**
- `TextInput` / `PhoneInput` had `error?: string`, which under `exactOptionalPropertyTypes: true` rejects callers passing `error={undefined}`. Loosened to `error?: string | undefined` so the form's "include the prop, but maybe undefined" pattern works without conditional spreads.
- General pattern when this trips: either change the prop type (cheap) or conditionally spread `{...(value ? { prop: value } : {})}` (no API surface change).

**Empty state path**
Matches docs/09 § "Coach · Trainees" exactly: `UserPlus` icon (60×60 muted bg), "Add your first trainee" title, 30-second pitch, two CTAs ("Add and invite" primary, "Add without invite" secondary). Both navigate to `/trainees/new`; the `intent` query param is set but not consumed yet — future enhancement: auto-toggle the form's submit-on-Enter behavior based on intent.

**Open followups**
- Replace `mockedCreateTrainee` with `POST /api/trainees` once BE step 8 ships. Schema fields map 1:1.
- Stash workspace name in the auth store on sign-in/switch so the WhatsApp template doesn't say "racademy" generically.
- Picker UI for starting tier + lead coach (postponed per "row picker" in docs/07 — needs a bottom-sheet primitive we haven't built yet).
