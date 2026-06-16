# racademy — AI-drafted assessment summaries

> Gemini-powered "draft summary from scores" on the assessment screen. Coach picks one of three voices; draft fills the textarea; coach edits and publishes as today. Same format as `docs/15-build-plan.md` — feed one step at a time; run the **Verify** block; advance only when **Done when** is green.

---

## Scope (locked)

- **Model:** Gemini 2.5 Flash (cheap, fast, JSON-mode). One outbound call per "Draft" tap.
- **Trigger:** Manual only. A "Draft with AI ✦" button on the assessment screen. Never auto-applied; coach reads + edits + saves as today.
- **Personalization:** Per-coach `summary_style` ∈ `{'encouraging','direct','warm'}`, default `'encouraging'`. Stored on `users` so it travels across workspaces.
- **Rollout:** Always on. No workspace-level toggle. Privacy note in T&Cs.
- **Languages:** Draft language follows the coach's `preferred_locale` (`en` or `id`).
- **Inputs sent to Gemini:** trainee first name, sport, session focus(es), per-skill `{name, score, optional coach note}`. No PII beyond display name. No tier names, no other trainees, no historical data at MVP.
- **Output:** plain-text summary, 60–140 words. The coach's existing rich-text affordances stay (newlines preserved).

## Out of scope

- Few-shot from past summaries (revisit if presets feel too generic).
- Workspace-level voice override / brand-tone settings.
- Streaming the draft into the textarea (one round-trip is fast enough at Flash speed).
- Drafting the per-skill notes — only the overall summary.
- Drafting in any language other than EN/ID.
- Caching drafts server-side — every tap is a fresh call.

## Conventions inherited (silent)

All `CLAUDE.md` + `docs/01-design-principles.md` rules apply: TS strict, mypy strict, Tailwind tokens only, sentence case, 0.5px hairlines, 44pt tap targets, lucide-react outline icons, EN+ID i18n.

---

# Pair G — Gemini integration (backend foundation)

## Step G1 [BE] — Gemini client + prompt builder + style presets

**Goal.** Standalone module that takes a payload + style and returns a draft string. No HTTP surface yet — just the unit-testable core.

**Reads.** `apps/api/src/config.py`, Anthropic/Google SDK conventions in existing httpx usage.

**Files to create.**

```
apps/api/src/ai/__init__.py
apps/api/src/ai/gemini_client.py           # thin httpx wrapper around generateContent
apps/api/src/ai/draft_summary.py           # build prompt + parse response
apps/api/src/ai/prompts/summary_en.py      # system + style strings (EN)
apps/api/src/ai/prompts/summary_id.py      # system + style strings (ID)
apps/api/tests/test_ai_draft_summary.py    # unit tests with a stubbed Gemini call
```

**Config additions (`apps/api/src/config.py`).**

```python
gemini_api_key: str = ""
gemini_model: str = "gemini-2.5-flash"
gemini_timeout_s: float = 12.0
```

`.env.example` documents the new keys; missing key → endpoint returns 503 with `"AI drafting is not configured."` so deploys without a key fail loudly.

**Style preset shape (per locale).**

Three system-prompt fragments per locale; same skeleton, different voice:

| Preset       | Voice                                                                 |
|--------------|-----------------------------------------------------------------------|
| `encouraging` | Growth mindset; weaknesses framed as opportunities; warm but specific |
| `direct`      | Clinical, factual, prioritise concrete feedback over softening        |
| `warm`        | Friendly, supportive, slightly more emotive; addresses trainee by name |

**Prompt structure.** Single `generateContent` call with `response_mime_type: 'text/plain'`, `maxOutputTokens: 320`, `temperature: 0.6`.

```
[system]
You are an experienced padel coach writing the summary for a single training
session. Voice: <style fragment for chosen preset>. Length: 60–140 words.
Address the trainee by first name. Mention 1–2 strengths and 1–2 focus areas.
Reference concrete skills by their names exactly as given. Never invent
scores, drills, or facts the input doesn't contain. Write in <locale name>.
[user]
Trainee: {first_name}
Session focuses: {focuses_joined}
Skills assessed:
- {skill_name_1}: {score}/5  {optional_note}
- ...
```

**Implementation notes.**

- `gemini_client.py` keeps a single httpx.AsyncClient lifecycle; reuse from main.py's startup so each request doesn't open a connection. Timeout = `settings.gemini_timeout_s`. On non-200 raise `GeminiError(status_code, body)`.
- `draft_summary.py` exports one async function: `async def draft_assessment_summary(*, trainee_first_name, locale, style, focuses, skills, http) -> str`.
- Tests stub the client via dependency injection (`http` arg) — no real network.
- Truncate the input skills list to 27 (it never grows past this) so prompt size is bounded.
- Strip leading/trailing whitespace + any model-emitted markdown wrappers ("```") before returning.

**Done when.**

- [ ] `pytest tests/test_ai_draft_summary.py` green: covers each style preset returns a non-empty string when client is stubbed; surfaces `GeminiError` on stubbed 5xx; respects locale (EN prompt for `en`, ID prompt for `id`).
- [ ] Missing `GEMINI_API_KEY` causes the module to raise `RuntimeError` only at first real call, never at import.
- [ ] No business logic in `gemini_client.py` — purely an HTTP wrapper.

**Verify.**

```bash
docker compose -f infra/docker-compose.yml exec api pytest tests/test_ai_draft_summary.py -v
# Live smoke (only with GEMINI_API_KEY set):
docker compose exec api python -c "
import asyncio, httpx
from src.ai.draft_summary import draft_assessment_summary
async def main():
    async with httpx.AsyncClient() as c:
        out = await draft_assessment_summary(
            trainee_first_name='Andi', locale='en', style='encouraging',
            focuses=['groundstrokes'],
            skills=[{'name':'Forehand Drive','score':3,'note':None},
                    {'name':'Bandeja','score':2,'note':'Late preparation.'}],
            http=c)
        print(out)
asyncio.run(main())
"
```

---

# Pair S — Style preset on user

## Step S1 [BE] — `users.summary_style` column + GET/PATCH /users/me

**Goal.** Persist the coach's chosen voice. Default `'encouraging'` for every user (trainees never use it, costs nothing to have the column).

**Files to create / edit.**

```
apps/api/alembic/versions/0027_users_summary_style.py     # NEW
apps/api/src/users/me_schemas.py                          # EDIT
apps/api/src/users/me_router.py                           # EDIT
apps/api/tests/test_users_me.py                           # EDIT
```

**Schema.**

```sql
ALTER TABLE users
  ADD COLUMN summary_style VARCHAR(20) NOT NULL DEFAULT 'encouraging'
  CHECK (summary_style IN ('encouraging','direct','warm'));
```

**Schema additions (`me_schemas.py`).**

```python
SummaryStyle = Literal['encouraging','direct','warm']

class MeOut(BaseModel):
    # ...existing fields...
    summary_style: SummaryStyle

class MePatch(BaseModel):
    # ...existing fields...
    summary_style: SummaryStyle | None = None
```

**Implementation notes.**

- Add `summary_style` to the existing `user_changes` block in `patch_me`; no new endpoint.
- Tests: PATCH each of the three valid values; PATCH `"shouty"` returns 422.

**Done when.**

- [ ] `alembic upgrade head` runs cleanly.
- [ ] GET /users/me returns `summary_style: 'encouraging'` for existing users (default fills).
- [ ] PATCH with valid style succeeds; PATCH with invalid value returns 422.

## Step S2 [FE] — Setting on `/me` profile

**Goal.** Single-select control in the existing Account section. Same auto-save pattern as locale.

**Files to edit.**

```
apps/web/src/features/profile/profile-api.ts                    # add summaryStyle to MeProfile + patch shape
apps/web/src/features/profile/sections/AccountSection.tsx       # add segmented control
apps/web/src/locales/{en,id}.json                               # 4 strings
```

**Layout.** Add a third row to `AccountSection` (below the locale toggle): label "Draft voice", subtitle "How AI-drafted assessment summaries sound.", then a 3-segment SegmentedControl with the preset labels. Only render for coaches (`user.role !== 'trainee' && user.role !== 'parent'`) — no point showing it to trainees.

**i18n keys.**

```jsonc
{
  "me": {
    "account": {
      "draftVoice": "Draft voice",
      "draftVoiceHint": "How AI-drafted assessment summaries sound."
    }
  },
  "draftVoice": {
    "encouraging": "Encouraging",
    "direct": "Direct",
    "warm": "Warm"
  }
}
```

**Done when.**

- [ ] Toggling the preset auto-saves; reload preserves the choice.
- [ ] Trainee/parent users don't see the row.
- [ ] No layout regression in the Account section.

---

# Pair E — Endpoint: POST /assessments/{id}/draft-summary

## Step E1 [BE] — Endpoint + auth + payload assembly

**Goal.** One endpoint the FE calls when the coach taps "Draft with AI". Returns `{draft: string}`. Re-draft on every tap (no caching).

**Files to create / edit.**

```
apps/api/src/assessments/draft_router.py             # NEW — POST /assessments/{id}/draft-summary
apps/api/src/main.py                                 # EDIT — register router
apps/api/tests/test_assessment_draft.py              # NEW
```

**Response.**

```jsonc
{ "draft": "Andi, your forehand stayed clean today...", "model": "gemini-2.5-flash" }
```

**Authorization.**

- Caller must be the assessment's `coach_id` OR `head_coach`/`club_admin` in the workspace. Other coaches → 403. Trainees/parents → 403.
- 404 if assessment doesn't exist or isn't in caller's workspace (RLS already filters).
- 409 if assessment has no scored skills yet ("Nothing to draft from — score at least one skill first.").

**Payload assembly.**

- Trainee first name = `athletes.display_name`, split on whitespace, first token.
- `focuses` = `SELECT focus FROM session_focuses WHERE session_id = a.session_id ORDER BY ordinal` (fallback to `sessions.focus` if join row absent).
- `skills` = `SELECT skill.name_{locale}, score.level, score.note FROM assessment_scores JOIN skills ORDER BY skill.display_order`.
- `locale` = the *coach's* `preferred_locale` (not the trainee's).
- `style` = the coach's `summary_style`.

**Rate limit / quota.** None at MVP. Gemini Flash cost is ~$0.0002/call so even abusive usage is negligible. Track every call via the audit log (see below); revisit a credit/cap model only when we have ≥2 weeks of real usage data and a pricing decision to make about gating AI drafts behind paid tiers.

**Implementation notes.**

- The endpoint does NOT write to the DB. The draft is returned only — coach pastes/edits/saves through the existing PATCH-draft flow.
- Audit log: `ai.draft_generated` with `{assessment_id, style, locale, skill_count, latency_ms}` (no draft text, no trainee data). Reuse the `@audit_action` decorator. This is the primary usage-tracking surface — query it later to decide if/how to introduce credits.
- Gemini errors: surface as 502 `"AI service is temporarily unavailable, try again."` Don't leak upstream error bodies.
- Missing API key → 503 `"AI drafting is not configured for this deploy."`
- Test stubs `draft_assessment_summary` to return a canned string so the endpoint test exercises auth + payload assembly without hitting Gemini.

**Done when.**

- [ ] Owning coach hits endpoint → 200 + draft.
- [ ] Non-owning coach in same workspace → 403.
- [ ] Head coach in same workspace → 200.
- [ ] Trainee/parent → 403.
- [ ] Empty assessment → 409.
- [ ] `pytest test_assessment_draft.py` covers all five paths above + audit row written with the documented fields.

**Verify.**

```bash
docker compose exec api pytest tests/test_assessment_draft.py -v
COACH_JWT=...
ASSESSMENT_ID=...
curl -s -X POST localhost:8000/assessments/$ASSESSMENT_ID/draft-summary \
  -H "Authorization: Bearer $COACH_JWT" | jq .
```

---

# Pair F — FE integration on the assessment screen

## Step F1 [FE] — "Draft with AI ✦" button + summary fill

**Goal.** New button next to (or above) the existing summary textarea. Tap → spinner → draft replaces textarea contents (with a one-tap "Undo" affordance for 8s).

**Files to edit.**

```
apps/web/src/features/assessment/assessment-api.ts         # add draftSummary(assessmentId)
apps/web/src/features/assessment/AssessmentScreen.tsx      # button + handler
apps/web/src/features/assessment/SummaryField.tsx          # (if extracted; else inline)
apps/web/src/locales/{en,id}.json                          # 6 strings
```

**Behavior.**

1. Button hidden until at least 1 skill is scored (mirrors the BE 409 guard).
2. Tap → button shows spinner + disabled state; existing summary text is captured to a `previousSummary` ref.
3. Success → `setSummary(draft)`, `markDirty()`, show inline pill "Drafted — undo" for 8s. Tapping undo restores `previousSummary`.
4. Error → toast with the server's message; summary unchanged.
5. If summary already has user-typed content, prepend a confirm step: small modal `"Replace your current summary with an AI draft?"` (preserves coach work).

**Visuals.**

- Button: `SecondaryButton` style, `Sparkles` lucide icon (size 16, strokeWidth 1.75), label "Draft with AI" (EN) / "Bantu draft" (ID). Positioned right-aligned, above the textarea, same row as the existing "X / 1000 characters" hint.
- Loading: swap icon for `Loader2` spinning; label "Drafting…".
- "Drafted — undo" pill: success-bg, success-text, `Sparkles` + label + small text button.

**i18n keys.**

```jsonc
{
  "assessment": {
    "draft": {
      "cta": "Draft with AI",
      "loading": "Drafting…",
      "confirmReplaceTitle": "Replace your summary?",
      "confirmReplaceBody": "Your current summary will be replaced by an AI draft. You can undo for a few seconds.",
      "confirmReplaceConfirm": "Replace",
      "successPill": "Drafted",
      "undo": "Undo",
      "failed": "Couldn't draft right now. Try again."
    }
  }
}
```

**Implementation notes.**

- Network call uses the existing `api.post`; no streaming.
- Don't auto-publish — draft remains in the unsaved-edits buffer like manual typing. The existing autosave 10s timer kicks in normally.
- Telemetry hook (when one exists): emit `ai_draft_used` with `{accepted: boolean}` flipped by whether the coach modified the textarea before publishing. Out of scope to wire if the telemetry layer isn't ready.

**Done when.**

- [ ] Button appears once a skill is scored; tapping fills the textarea.
- [ ] Undo pill restores the prior text within 8s, then disappears.
- [ ] Confirm modal appears only when the textarea has user content already.
- [ ] Spinner state blocks repeat taps.
- [ ] Trainee-locale toggle changes the language of subsequent drafts (since locale follows the coach's `preferred_locale`).
- [ ] Coach with `summary_style='direct'` gets a noticeably terser draft than `summary_style='warm'` for the same assessment (manual eyeball).

**Verify.**

```bash
pnpm --filter @racademy/web dev
# Manual: assess 4–5 skills on a demo trainee → tap Draft with AI → wait → confirm the
# textarea fills with sensible prose. Toggle the coach's preferred_locale to id → tap
# again → confirm Indonesian draft. Switch summary_style in /me to 'direct' → confirm
# voice changes.
```

---

# Pair D — Doc updates

## Step D1 — Note the feature in the right places

**Files to edit.**

```
docs/04b-coach-assessment-v2.md     # EDIT — add "AI-drafted summary" subsection under the summary field
docs/06-workspace-settings.md       # EDIT — add a sentence: coaches choose their draft voice in their /me profile (not workspace settings)
docs/README.md                      # EDIT — list docs/18
.env.example                        # EDIT — GEMINI_API_KEY=... + GEMINI_MODEL=gemini-2.5-flash
```

**Done when.**

- [ ] `docs/README.md` table lists docs/18 with a one-line description.
- [ ] `.env.example` includes the new keys with sensible placeholders.

---

# End-to-end verification

After F1 + D1 land:

1. Sign in as `coach1@racademy.dev`; open Andi's assessment screen.
2. Score 6 skills across 2 categories; leave the summary empty.
3. Tap "Draft with AI ✦" → wait ~1–2s → textarea fills with a coherent paragraph that names Andi + references a subset of the scored skills.
4. Edit one line, save as draft, then publish — the published assessment shows the (edited) draft.
5. Go to `/me` → change Draft voice to **Direct** → return to a different assessment → confirm the next draft is noticeably terser.
6. Sign in as a non-owning coach → open same assessment → confirm "Draft with AI" button does NOT appear in their view (gated by `isAssignedCoach`).
7. Disconnect from network mid-draft → confirm graceful failure toast, no textarea change.

If any step fails, the failing pair owns the bug — don't advance.

---

# Open questions (out of MVP, parked)

- **Credits / paid-tier gating** — currently free + unlimited; usage is tracked via the `ai.draft_generated` audit row. After ~2 weeks of real data, decide whether to add a per-workspace monthly cap tied to plan (e.g. Free: 20/mo, Club Starter: 100/mo, Club Pro: unlimited). Per-workspace is the right axis (workspaces are the billing unit), with an optional per-coach sub-cap if a power coach drains the pool.
- Per-workspace "house voice" override that wraps the per-coach style — probably yes when the first big club asks.
- Draft as hint vs. replacement — render alongside the textarea as a "suggestion" the coach copies from. Heavier UI; revisit if coaches complain about losing typed content.
- Feed prior session summaries for the same trainee so drafts feel continuous. Cost: longer prompts + privacy surface area.
- Tier-aware tone — easier language for beginners, more technical for advanced — useful, deferred.

---

# Suggested calendar

| Pair | Steps    | Estimate |
|------|----------|----------|
| G    | G1       | ~1 day  |
| S    | S1 → S2  | ~0.5 day |
| E    | E1       | ~1 day  |
| F    | F1       | ~0.5 day |
| D    | D1       | ~0.25 day |

~3 working days end-to-end.
