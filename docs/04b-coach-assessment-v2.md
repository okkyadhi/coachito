# Coach · Assessment v2

> Spec update for the assessment feature. Adds: 1:1 Session ↔ Assessment mapping, Draft + Edit lifecycle, and Trainee Feedback (optionally anonymous). This document supersedes the relevant sections of `04-coach-assessment.md` and adds a new doc surface for feedback. Read alongside `12-data-model.md` and `padel-skill-framework-v0.md`.

## TL;DR (what changes from v1)

| Concern | v1 (current) | v2 (this spec) |
|---|---|---|
| Session ↔ Assessment | Loose: assessments optionally reference a session_id | **Strict 1:1.** Every assessment belongs to exactly one session; every completed session has exactly one assessment (which may be empty of scores). |
| Save model | Single "Save" → published | **Draft → Published → Edited.** Coach can `Save draft` (private) and later `Publish` (visible to trainee/parent). |
| Edit after Save | Append-only inserts of new score rows | **Mutable assessment** with version history. Edits create an audit row, not a new assessment. |
| Trainee feedback | None | **New.** Trainee can leave optional feedback after each published assessment. May be anonymous. |
| Coach sees feedback | N/A | New screen + Today/Trainee Profile surfaces. |

---

## 1. Core model decision: Assessment = Session (1:1)

### Rule

> One Session has exactly zero or one Assessment. One Assessment belongs to exactly one Session. There is no "free-floating" assessment.

- Sessions with `status = 'completed'` **must** have an assessment row (even if it has 0 scores and 0 summary — a coach observation-only session is a valid empty assessment).
- Sessions with `status = 'cancelled' | 'no_show'` **must not** have an assessment.
- Sessions with `status = 'scheduled'` **may** have an assessment **only** in `draft` state (coach started scoring early or mid-session).
- The relationship is enforced at the DB level with a `UNIQUE (session_id)` constraint on `assessments`.

### Implications for entry points

| Trigger | Current behavior | v2 behavior |
|---|---|---|
| Tap "New assessment" on trainee profile | Creates a new assessment, optionally a session | **Always opens a "Pick or create session" sheet first.** Coach picks an existing session today/recent, or taps "Quick session" to inline-create one (today, now, default 60min, focus=general). |
| Tap a session row on Coach Today | Opens trainee profile | **New default:** opens that session's assessment (creates it on-demand in draft state if absent). |
| Tap "Assess now" on an upcoming session | N/A | Same as above, plus auto-marks session `completed` on Publish. |

### Why 1:1

- Tier progression is computed from "what happened in a session." Without a session anchor, you can't answer "what changed this week?" cleanly.
- PDF monthly reports group by session. 1:1 makes the join trivial.
- Trainee feedback is "on the session you just had with the coach" — it needs a session to attach to.
- Removes the ambiguity of "is this assessment a stand-alone snapshot or tied to a real meeting?"

### Edge cases (decide before build)

1. **Two coaches, one session.** Club has co-coaches who both observed. Allowed?
   - **Recommendation:** session has one `primary_coach_id`. Only the primary coach writes the assessment. Co-coaches can read but not edit (V1.5: add "co-observation note" field).
2. **Assessment without a real session (back-dating).** Coach forgot to log Monday's session, wants to add it Wednesday.
   - **Recommendation:** allow it. "Quick session" creation supports a back-dated `scheduled_at`. Cap at -14 days; older needs admin override.
3. **Re-doing an assessment after publish (e.g., realized wrong trainee).** Delete the assessment? Or transfer?
   - **Recommendation:** soft-archive the bad assessment + session pair, force re-create. Audit log records both events.

---

## 2. State machine: Draft / Published / Edited

```
   ┌─────────┐  Publish   ┌──────────────┐  Edit   ┌──────────────┐
   │  Draft  │ ─────────► │  Published   │ ──────► │   Edited     │
   └─────────┘            └──────────────┘         │ (still pub.) │
       ▲                       │                   └──────────────┘
       │ Discard               │ Withdraw                 │
       └───────────────────────┴──────────── (V1.5) ──────┘
```

Statuses live on the `assessments` row, not in separate tables.

| Status | Trainee can see? | Counts toward tier? | Surfaces in PDF? | Generates trainee notification? |
|---|---|---|---|---|
| `draft` | **No** | **No** | No | No |
| `published` | Yes | Yes | Yes | Yes (push + in-app) |
| `edited` | Yes | Yes (latest values) | Yes (with "updated" marker) | Yes (separate "updated" notification, throttled) |
| `withdrawn` (V1.5) | No | No | No | Yes ("Your coach is reviewing this assessment") |

### Draft behavior

- **Save draft** persists scores, notes, and summary text server-side under `status='draft'`.
- Drafts are **per (coach, session)**; only the assessment's coach can resume it.
- Drafts auto-save every 5s when input is dirty (debounced). No "Save draft" button needed for auto-save; but expose an explicit `Save draft` action so coaches feel in control.
- Drafts hold an **exclusive write lock** on the session — another coach opening the session sees "Coach Novia is drafting an assessment — view only."
- Drafts older than **14 days** are flagged on the coach's Today screen ("You have 2 unfinished assessments"). Drafts are never auto-deleted in MVP — coaches decide.

### Publish behavior

- Publish requires the assessment to pass validation (see §4).
- On publish:
  - `status` flips to `published`.
  - `published_at = NOW()`.
  - Session flips to `status='completed'` if it wasn't already.
  - Tier recalculation job fires for the trainee.
  - Trainee + parent (if junior) get a push + in-app notification.
  - Email/PDF inclusion: yes for the next monthly report.

### Edit behavior

- An assessment in `published` or `edited` status can be re-opened. UI: `Edit` action in the assessment screen's `⋯` menu.
- Editing creates an in-flight `edit_session` (in-memory; not a new DB row yet). On `Save changes`:
  - Status flips to `edited` (idempotent — second edit stays `edited`).
  - `edited_at` updates.
  - A row inserts into `assessment_edits` audit table with diffs (see §6 data model).
  - Tier recalculates.
  - Trainee notification fires **only** if scores changed (not if only a typo in the summary was fixed). Throttle: max 1 "updated" notification per assessment per 24h.
- Editing is allowed **only by the original coach** in MVP. Club admins get an override action in V1.5.
- Hard edit window: **forever** for MVP (no time cap). Most edits happen within 24h, but a coach may correct an obvious error a week later. We'll observe and add caps if abuse appears.

### Discard / withdraw

- `Discard` draft → hard delete of the draft assessment row (audit log retains intent only). Session row remains (still `scheduled` or back to `scheduled` if it was flipped).
- `Withdraw` published (V1.5) → status back to `draft`. Trainee sees a soft state: "Your coach is reviewing this assessment." Not in MVP.

---

## 3. Trainee feedback

### Purpose

Give trainees and parents a low-friction way to tell coaches: did this session land? Did the assessment match what you felt? Provide signal back to coaches so they can adapt. Also a quality input for club admins later (V1.5 aggregation).

### Model

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | |
| `assessment_id` | UUID FK → assessments | **Required.** Feedback is always anchored to a specific published assessment. |
| `submitted_by_user_id` | UUID FK → users | Always stored, regardless of anonymity flag. Used for rate-limit + abuse review. |
| `submitter_role` | enum | `trainee` \| `parent` |
| `is_anonymous` | boolean | If true, coach-facing UI hides `submitted_by_user_id` and shows "Anonymous trainee" / "Anonymous parent." |
| `rating_overall` | smallint 1–5 | "How was the session?" — required. |
| `rating_fairness` | smallint 1–5 | "Did the scoring feel fair?" — optional. |
| `comment` | text (≤500 chars) | Optional free text. |
| `submitted_at` | timestamptz | |
| `edited_at` | timestamptz NULL | Trainee can edit within 24h of submit. |
| `withdrawn_at` | timestamptz NULL | Trainee can delete anytime. |

### Anonymity model — be explicit

> **Anonymous to the coach. Never anonymous to the system.**

- The DB always knows who submitted. This is non-negotiable for:
  - Rate-limiting (one feedback per assessment per user).
  - Abuse moderation (a coach reporting harassment, an admin needs to investigate).
  - Edit/withdraw (trainee must be able to come back to their own feedback).
- The coach UI never reveals identity when `is_anonymous = true`. Backend filters the field at the API boundary; no client-side hiding.
- Workspace admin (club owner) sees identity **only** when handling an abuse report — gated by an explicit "Review feedback" action that audit-logs the reveal.

### Flow

1. **Trigger.** Trainee receives push: "Coach Novia rated your session. Tap to see your skills."
2. After viewing the assessment, trainee scrolls to a **"How was this session?"** card pinned at the bottom of their session detail screen.
3. Tapping it opens a sheet:
   - Single big "overall" emoji-row (1–5, large taps, sweaty-thumb sized — courtside parity).
   - Optional "Did the scoring feel fair?" (same scale, smaller).
   - Optional free-text textarea (max 500 chars, char count visible).
   - Anonymous toggle, off by default, with helper text: *"Your coach sees your name unless this is on. The platform always knows it's you so we can keep things safe."*
   - Submit / Cancel.
4. Once submitted: card collapses to "✓ You shared feedback · Edit (24h) · Withdraw."
5. After 24h, only `Withdraw` is available.

### Required or optional?

**Optional in MVP.** Mandatory feedback gates feel coercive and degrade signal quality (people just tap 5 to dismiss). After 4 weeks of pilot data, consider gentle nudges ("3 sessions since you last gave feedback").

### Junior trainees

Both the trainee (if a user account exists) and the parent can submit. **One feedback per assessment per submitter role** — i.e. up to one from the trainee and one from the parent. UI labels each as such to the coach.

### Coach notification

- New feedback → in-app badge on Coach Today ("3 new feedback").
- Push notification: **batched daily at 7pm local**, never per-message. Coaches scoring 5 sessions/day don't need 5 dopamine pings.
- Anonymous feedback still pings, just labeled.

### Coach view of feedback

Three surfaces:

1. **Per-assessment** — at the bottom of the assessment screen, after publishing. Sticky "Feedback (1)" pill linking down to the card.
2. **Per-trainee profile** — a "Feedback" mini-section below "Recent sessions," showing the last 3 with `View all`.
3. **Inbox** (new, lightweight) — under `Today → Feedback` tab or the bell icon. Chronological feed of unread items first, then read. Each row: assessment context (trainee name unless anonymous, session date, focus) + ratings + comment preview.

Coach can **react** to a feedback item with a simple "Thanks · seen" tap (writes a `read_at` timestamp and optionally a tiny acknowledgement message back to the trainee). No threaded chat in MVP — keeps moderation surface small.

### Moderation

- Free text passes through a profanity/abuse classifier (server-side, on submit). Flagged feedback is quarantined: not shown to coach, queued for workspace-admin review.
- Coach can **report** any received feedback. Reported items are hidden until admin reviews.
- Trainee accounts with >2 confirmed-abusive feedbacks in 30 days are throttled (rate-limited to 1 feedback / week).

---

## 4. Validation on Save / Publish

| Rule | On Save Draft | On Publish |
|---|---|---|
| Assessment is tied to a session | Yes (auto-create allowed) | Yes (must exist, not cancelled) |
| At least 1 skill scored OR summary text > 10 chars | No | **Yes** — otherwise show "Add at least one score or a session summary before publishing." Override option: "Publish empty" with confirmation (rare observation-only case). |
| Session focus and date set | No | Yes |
| Trainee still active in workspace | Yes | Yes (block if archived) |
| Coach is the session's primary_coach | Yes | Yes |
| All in-flight notes ≤ 280 chars; summary ≤ 1000 chars | Yes | Yes |

Validation errors surface inline next to the offending field, plus a top-banner summary if multiple.

---

## 5. UI changes (delta from `04-coach-assessment.md`)

### Top nav bar

- Right side becomes two actions:
  - `Save draft` (text button, neutral) — visible always.
  - `Publish` (text button, accent, weight 500) — visible always; primary action.
- After publish, the screen re-renders in **"View / Edit mode"**: `Publish` replaced by `Edit` (text, accent). `Save draft` hidden.

### Status strip (new)

Between the trainee strip and the level legend, a thin status row:
- Draft: `● Draft · Saved 3s ago`
- Published: `● Published 10 May 14:23 · Trainee notified`
- Edited: `● Edited 12 May 09:01 · Originally published 10 May`

Tappable → shows full timeline (audit history sheet).

### Footer banner (new, on Publish action)

A confirmation sheet, not a silent toast:
- "Publish this assessment?"
- Summary: "10 skills scored · 6 skills changed since last session · summary 142 chars"
- "Trainee Andi + parent Pak Budi will be notified."
- Buttons: `Cancel` / `Publish`.

### Trainee feedback card (new, only when feedback exists)

Renders below session summary, above the bottom tab bar.
- Header: "Feedback from Andi · 11 May"
- If anonymous: "Anonymous trainee · 11 May"
- Star/emoji rating row (overall + fairness if given)
- Comment text (italic, lighter weight)
- `Thanks` action (one-tap acknowledgement)

If multiple feedbacks (e.g., trainee + parent), stack vertically.

---

## 6. Data model (deltas to `12-data-model.md`)

### `assessments` — restructure

The current append-one-row-per-skill design must change. Replace with a parent + child structure:

```sql
-- Parent: one row per (session, coach) — drives the 1:1 mapping.
CREATE TABLE assessments (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  session_id      UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  athlete_id      UUID NOT NULL REFERENCES athletes(id),
  coach_id        UUID NOT NULL REFERENCES users(id),
  status          VARCHAR(16) NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','published','edited','withdrawn')),
  summary         TEXT,                        -- session summary, customer-facing
  internal_notes  TEXT,                        -- coach private
  saved_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at    TIMESTAMPTZ,
  edited_at       TIMESTAMPTZ,
  withdrawn_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_assessments_session ON assessments (session_id);
CREATE INDEX idx_assessments_athlete       ON assessments (workspace_id, athlete_id, published_at DESC);

-- Child: one row per skill scored in this assessment.
CREATE TABLE assessment_scores (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  assessment_id   UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  skill_id        UUID NOT NULL REFERENCES skills(id),
  level           SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 5),
  note            TEXT,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_assessment_scores ON assessment_scores (assessment_id, skill_id);
```

**Tier calculation** still queries "latest score per (athlete, skill)" — but now joins through `assessments` and filters `status IN ('published','edited')` so drafts don't pollute tier math.

### `assessment_edits` (new) — audit trail

```sql
CREATE TABLE assessment_edits (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  assessment_id   UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  edited_by_id    UUID NOT NULL REFERENCES users(id),
  edited_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  changes_jsonb   JSONB NOT NULL,              -- e.g. {"summary":{"from":"…","to":"…"}, "scores":[{"skill":"BANDEJA","from":2,"to":3}]}
  reason          TEXT                          -- optional coach-provided rationale
);

CREATE INDEX idx_assessment_edits ON assessment_edits (assessment_id, edited_at DESC);
```

### `feedbacks` (new)

```sql
CREATE TABLE feedbacks (
  id                     UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id           UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  assessment_id          UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  submitted_by_user_id   UUID NOT NULL REFERENCES users(id),
  submitter_role         VARCHAR(16) NOT NULL CHECK (submitter_role IN ('trainee','parent')),
  is_anonymous           BOOLEAN NOT NULL DEFAULT FALSE,
  rating_overall         SMALLINT NOT NULL CHECK (rating_overall BETWEEN 1 AND 5),
  rating_fairness        SMALLINT CHECK (rating_fairness BETWEEN 1 AND 5),
  comment                TEXT,
  submitted_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  edited_at              TIMESTAMPTZ,
  withdrawn_at           TIMESTAMPTZ,
  read_at                TIMESTAMPTZ,                  -- when coach marked seen
  flagged_at             TIMESTAMPTZ,                  -- moderation
  flagged_reason         TEXT
);

-- One feedback per (assessment, submitter, role)
CREATE UNIQUE INDEX uq_feedback_one_per_role
  ON feedbacks (assessment_id, submitted_by_user_id, submitter_role)
  WHERE withdrawn_at IS NULL;

CREATE INDEX idx_feedbacks_assessment ON feedbacks (assessment_id);
CREATE INDEX idx_feedbacks_workspace_unread
  ON feedbacks (workspace_id, submitted_at DESC)
  WHERE read_at IS NULL AND withdrawn_at IS NULL;
```

### RLS sketch

- `assessments`: coach sees own + workspace assessments. Trainee + parent see only `status IN ('published','edited')` for their own athlete.
- `assessment_scores`: inherits from parent assessment via subquery in policy.
- `feedbacks`: trainee/parent sees only rows they submitted. Coach sees rows for assessments where `coach_id = current_user`, **but** the API strips `submitted_by_user_id` and resolves the display name only if `is_anonymous = false`. Workspace admin gets unmasked access only via explicit moderation endpoint with audit logging.

---

## 7. Notifications

| Event | Recipient | Channel | Throttle |
|---|---|---|---|
| Assessment published | Trainee + parent | Push + in-app + email digest (parent) | None — one per assessment |
| Assessment edited (scores changed) | Trainee + parent | Push + in-app | Max 1 per assessment per 24h |
| Feedback submitted | Coach | In-app badge + daily 7pm push digest | Daily |
| Feedback flagged | Workspace admin | Email + in-app | Immediate |
| Draft stale > 7 days | Coach | In-app only (Today screen banner) | Weekly |

All notification copy must localize EN/ID. See §10.

---

## 8. Offline behavior

Assessment v1 was already offline-first for `Save`. v2 adds:
- **Drafts sync** when back online. Conflict policy: server takes the latest `saved_at` wins; older device shows a "Your draft was overridden by a newer save" banner with a one-tap restore from local cache.
- **Publish** is **blocked offline** for MVP. Reason: publish triggers tier recalc, notifications, and PDF eligibility — all server-side. Show banner: "Connect to publish. Your draft is saved." V1.5: queued publish with optimistic UI.
- **Feedback submission** by trainees works offline: queued in IndexedDB, sent on reconnect. Anonymity toggle is preserved per-item in the queue.

---

## 9. Empty states (additions to `09-empty-states.md`)

### Coach · Today · Feedback inbox (no feedback)

- Icon: `ti-message-circle`
- Title: "No feedback yet"
- Description: "After you publish an assessment, your trainees can share how the session felt."
- Primary: (none)

### Trainee · Session detail (after view, no feedback given)

- Card "How was this session?" pinned, primary CTA "Share feedback" — see §3 flow.

### Coach · Assessment screen (resuming an old draft)

- Top of screen banner: "Resumed from draft saved 3 days ago" with `Discard draft` link.

---

## 10. Localization (additions to `11-localization-rules.md`)

| EN | ID |
|---|---|
| Save draft | Simpan draf |
| Publish | Terbitkan |
| Publish this assessment? | Terbitkan penilaian ini? |
| Draft | Draf |
| Published | Terbit |
| Edited | Diedit |
| Saved 3s ago | Tersimpan 3 detik lalu |
| Trainee notified | Trainee diberi tahu |
| Edit | Edit |
| Edit history | Riwayat edit |
| How was this session? | Bagaimana sesi tadi? |
| Did the scoring feel fair? | Apakah penilaiannya terasa adil? |
| Share feedback | Bagikan masukan |
| Submit anonymously | Kirim tanpa nama |
| Your coach sees your name unless this is on. | Coach kamu melihat namamu kecuali ini dinyalakan. |
| The platform always knows it's you so we can keep things safe. | Platform tetap mengenali kamu untuk menjaga keamanan. |
| Anonymous trainee | Trainee anonim |
| Thanks · seen | Terima kasih · dilihat |
| Feedback (3) | Masukan (3) |
| Report feedback | Laporkan masukan |
| Withdraw | Tarik kembali |
| Connect to publish | Hubungkan untuk menerbitkan |

Coach narrative (summary text, comment text) **never** auto-translates — store as-typed. Same rule from `CLAUDE.md`.

---

## 11. Open decisions — need your call before build

The following are real forks where the implementation depends on a product call:

1. **Per-skill notes visibility.** Today they're private to coach. Should feedback context expose them to the trainee? *Default: keep private.*
2. **Co-coach observation.** Allow multiple coaches per session? *MVP recommendation: no, one primary coach only.*
3. **Draft auto-publish on session end.** When a session is marked `completed` externally (e.g., via the Sessions tab), should an existing draft auto-publish? *Recommendation: no — explicit publish only, avoid surprise.*
4. **Edit window cap.** Forever, 24h, 7d, or "until next assessment for same trainee exists"? *Recommendation: forever in MVP, observe abuse.*
5. **Feedback eligibility.** Can a trainee feedback the same assessment after edit? *Recommendation: yes, edit window resets to 24h when the coach edits — surfaces the change.*
6. **Anonymous to whom.** Confirm: anonymous-to-coach, never-to-system, admin-can-unmask-only-for-moderation. *(Locked above, please re-confirm.)*
7. **Parent-without-trainee-user-account.** A junior with no app login — feedback goes via parent only. Should we support a magic-link "feedback only" web flow for trainees with no install? *Recommendation: V1.5.*
8. **Withdraw published.** Coach realizes mistake after publish — full retraction or only edit? *MVP: edit only. Withdraw is V1.5.*
9. **Score-changed threshold for re-notification.** A single skill bumped 2→3, do we notify? *Recommendation: yes if any score changed OR summary changed by >20 chars; otherwise silent edit.*
10. **Tier recalc on edited.** Always re-run; what about if downgraded? *Recommendation: always re-run; if downgrade, surface gently in trainee UI as "Tier reassessed."*

---

## 12. What else you should probably improve (unprompted suggestions)

Things that come up naturally once you have draft + edit + feedback that you didn't ask about but probably want:

- **Assessment timeline view.** Trainee scrolls through their history; show edit markers. Already implied by `recent sessions`, but extend it to: "Coach edited this 2 days after publishing — fairness ↓ if changed."
- **"Compared to last session" diff.** When publishing, show coach an inline "What's changing for the trainee?" summary: "Forehand drive 2→3 · Bandeja unchanged · 4 new skills rated." Improves intentional scoring; reduces "oh wait I didn't mean to set that."
- **Coach reflection field (private).** Already in schema as `internal_notes`; surface it. Coaches want a place to write things they don't want the trainee to see. Important for honest reflection.
- **Bulk-prefill from last session.** "Start from last scores" is the realistic default. Make it the default, with a one-tap "Start blank" alternative — coaches rarely score every skill from scratch every session.
- **Session focus → suggested skills.** If `focus = drilling` and tagged "bandeja week," surface those skills first in the scroll order. Faster scoring path.
- **Trainee read receipts on summaries.** Coach sees "Andi read your summary 2h ago." Subtle accountability for both sides.
- **Aggregate feedback for coach.** A small stat at top of Coach Profile / Settings: "Avg overall rating last 30d: 4.6 from 18 feedbacks." Motivation + signal.
- **Workspace admin feedback rollup (V1.5).** Club owner sees coach-level aggregates. Useful for performance reviews — flag separately as a sensitive surface.
- **Localized rate-fairness scale labels.** "Adil" vs "Tidak adil" don't map cleanly to a 1–5; consider a 3-point ("less than expected / right / more than expected") with EN parity. Pilot-test the wording.
- **PDF report inclusion of feedback.** Decide: does the monthly PDF include the trainee's feedback to the coach? *Recommendation: no in MVP* — keeps the PDF as a coach→trainee document, not bidirectional. Reconsider in V2 if parents request.
- **Schema migration strategy.** Restructuring `assessments` from row-per-skill to parent+child is a non-trivial migration if you've shipped already. If you haven't, do it now. If you have, write a back-fill migration that groups by (session_id, coach_id, recorded_at) and confirm uniqueness before applying the constraint.
- **Idempotency on Publish.** Network blip → double publish → double notification. Wrap publish in an idempotency key. Notifications check `published_at` before sending; if already sent, skip.
- **Coach narrative AI-draft after edit.** If coach edits scores, offer to regenerate the summary draft. The current "Draft from scores" only fires on initial entry.

---

## 13. Related screens to update

- `02-coach-today.md` — add Feedback inbox/badge + draft-resume banner.
- `03-coach-trainee-profile.md` — add feedback section, edited-marker on session cards.
- `04-coach-assessment.md` — superseded by this doc for save/publish flow.
- `05-trainee-home.md` — add feedback CTA on session detail, edit-marker on radar tooltip.
- `08-pdf-report.md` — include edited markers on session entries; decide on feedback inclusion (see §12).
- `09-empty-states.md` — add the two new empty states (§9).
- `10-error-offline-states.md` — add publish-blocked-offline banner.
- `11-localization-rules.md` — add §10 strings.
- `12-data-model.md` — add new tables, change `assessments` structure, add RLS.

---

## 14. Out of scope (explicit, to prevent scope creep)

- Coach-to-trainee in-app chat threading on feedback (V2).
- Trainee self-assessment (V2, already documented as out of MVP in skill framework).
- Video/voice feedback attachments (V2+).
- Workspace-wide feedback analytics dashboard (V1.5).
- Cross-club coach reputation portability (never — privacy + market dynamics).
- Auto-translation of coach summaries or trainee comments (never — see `CLAUDE.md`).
