# Coachito — Trainee-facing reports

> Gives trainees access to their PDF reports inside the app + an email
> notification when one is generated.  Same format as `docs/15`; feed one
> pair at a time.

## Scope (locked)

- **Endpoint:** `GET /trainees/me/reports` returns completed reports for the
  signed-in trainee, newest first.  RLS-isolated to the caller.  No write
  endpoints — coaches still own creation.
- **Trainee `/me` profile:** new "Reports" row in the Personal section
  linking to `/me/reports`.  Hidden if the trainee has zero reports yet
  (no point teasing an empty inbox).
- **`/me/reports` list screen:** sentence-case rows showing period label
  ("April 2026" or session date), coach name, view-count, and a "View PDF"
  CTA that opens `pdf_url` in a new tab.  Browsers handle PDF rendering.
- **`/home` banner:** when at least one report was generated in the last 7
  days and the trainee hasn't tapped into it yet, show a one-line clay-bg
  pill: "New report — April 2026 → view".
- **Email push:** at the end of the RQ generation job, if the trainee
  (`athletes.user_id`) exists, has an email, and `user_notification_prefs
  .monthly_report = true`, send an HTML+plain email with a clay CTA → the
  public PDF URL.  Respects the existing toggle in `/me`.
- **Localization:** EN + ID.  Email subject and body follow the coach's
  workspace `primary_locale`; the in-app screens follow the trainee's
  `preferred_locale`.

## Out of scope

- In-app PDF preview (we open the URL in a new tab; mobile browsers
  render PDFs natively).
- Push notifications (the existing notification toggle covers email
  only — Web Push is V1.5).
- Parent-only view (parents still receive the PDF via the manual share
  flow; in-app reports are trainee-only for now).
- Marking a report "viewed by trainee" (the existing `view_count` already
  increments on `GET /reports/:id`; we'll reuse, not extend).

## Pairs

### Pair B — Backend

#### B1: `GET /trainees/me/reports`

- New router file `apps/api/src/trainees/reports_router.py`.
- Returns `[{id, period_start, period_end, period_label, generated_at,
  pdf_url, view_count, coach_display_name, is_session_report}]`.
- Filter: `athletes.user_id = caller`, `status = 'completed'`.  Ordered by
  `generated_at DESC`.  Cache `private, max-age=30`.
- Test: trainee A sees only A's reports; trainee with no reports sees `[]`.

#### B2: Email send hook in the generation job

- New module `apps/api/src/reports/emails.py` with one async function:
  `send_report_ready_email(*, to_email, locale, trainee_first_name,
  period_label, pdf_url)`.  Mirrors the magic-link template (clay button,
  bone bg, ink text).  Subject "Your Coachito report is ready" / "Laporan
  Coachito-mu siap".
- Hook in `apps/api/src/reports/jobs.py::_run` right after the
  `status = 'completed'` UPDATE.  Best-effort — log on failure, do NOT
  fail the job.  Skip when: athlete has no `user_id`, user has no email,
  or `user_notification_prefs.monthly_report = false`.
- Test: stub `aiosmtplib.send`; assert it's called when pref is on, not
  called when pref is off, not called when athlete has no user link.

### Pair T — Trainee FE

#### T1: `/me/reports` list screen + profile row

- New feature folder `apps/web/src/features/trainee-reports/`.
- `reports-api.ts`: `fetchMyReports()` → typed array.
- `TraineeReportsScreen.tsx`: list view; if no reports, an empty state
  ("Reports drop on the 1st of each month.  Your coach can also generate
  one anytime.").
- `ReportRow.tsx`: period label + coach name + "View PDF" CTA.
- Route at `/me/reports` under `TraineeShellGate`.
- A new row in `/me` → `PersonalSection` (or a sibling section) linking to
  the list.  Show "N reports" or hide row entirely if 0.

#### T2: Home banner

- Add to `TraineeHomeScreen.tsx` above the first card: if `useQuery(['me',
  'reports', 'latest'])` returns a report with `generated_at` within 7
  days, show a clay-bg pill "New report — {period_label} → view".  Tap
  navigates to `/me/reports`.
- Dismissal: localStorage key `coachito.reportBanner.dismissed_until`
  stored as ISO date; setting it to the report's `generated_at` removes
  the banner until the next one drops.  Tapping the CTA also dismisses.

### Pair L — Localization keys

Single batch — add to both `en.json` and `id.json`:

```jsonc
"trainee": {
  "reports": {
    "title": "Reports",
    "subtitle": "Monthly progress, signed by your coach.",
    "viewCta": "View PDF",
    "emptyTitle": "No reports yet",
    "emptyBody": "Reports drop on the 1st of each month — and your coach can generate one anytime.",
    "viewCountLabel_one": "Opened {{count}} time",
    "viewCountLabel_other": "Opened {{count}} times",
    "byCoach": "By {{name}}",
    "perSessionTag": "Per-session",
    "monthlyTag": "Monthly"
  },
  "home": {
    "newReportBanner": "New report — {{label}} →"
  }
}
```

### Pair V — Verification (end-to-end)

1. Sign in as `head@coachito.dev`, generate a report for Andi (via the
   "Generate report" button on `/trainees/:id`).
2. Wait ~2s for the worker.
3. In Mailpit (`http://localhost:8025`) confirm an email landed for
   `andi@coachito.dev` with subject "Your Coachito report is ready" and a
   clay button linking to the PDF URL.
4. Sign in as Andi.  `/home` shows the "New report — May 2026 →" pill.
5. Tap → `/me/reports` lists the report.  Tap "View PDF" → new tab opens
   the PDF.
6. Return to `/home` — banner gone.
7. Toggle "Monthly report ready" off in `/me`, generate another report
   as coach → no new email lands.

## Notes / decisions parked

- Push notifications: deferred to V1.5 once we add a service worker
  notification surface.
- Parent emails: parents share the PDF link manually for now; if we ever
  add parent accounts, the same hook applies to `users.primary_guardian_id`.
- "Mark as read" UX: the existing `view_count` is sufficient feedback for
  the coach side.  A dedicated read-receipt would need a new column; not
  worth it at MVP.
