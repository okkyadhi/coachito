# Coach · Assessment

> The screen where coaches actually score skills. Tap-based segmented control, inline level descriptors, and a session summary field.

## Purpose

The single most important screen in the product. Coaches use it during or right after a session to:
1. Score 27 skills on a 1–5 rubric
2. Reference level descriptors for accuracy
3. Add per-skill notes (when context matters)
4. Write a session summary for the trainee/parent to read

Everything in PadelCoach — tier progression, radar, blockers, PDF reports, trainee motivation — is downstream of what gets entered here.

## Audience

- **Role:** Coach
- **Workspace types:** Both
- **Context:** During a session (courtside on phone), at the end of a session, or shortly after. Hands often sweaty/wet — large tap targets matter.

## Layout (top to bottom)

1. **Top nav bar**
   - Left: `< Today` (or whatever screen they came from)
   - Right: `Save` (accent color, weight 500) — saves the entire assessment + summary
2. **Trainee strip**
   - Avatar (44×44) + name (large title 22px) + "Lower Bronze · 10 May, session 42"
3. **Level legend** (single line, 5 pills)
   - "1 Belajar / Learning" through "5 Mahir / Mastery"
4. **4 collapsible category groups** (Technical default open)
   - Technical (13 skills) · 9/13
   - Tactical (6 skills) · 2/6
   - Physical (4 skills) · 1/4
   - Mental (4 skills) · 1/4
5. **Per skill row** (inside open category):
   - Skill name (left)
   - Score pill: "{level} {label}" or "Not rated"
   - Info icon button (right)
   - Segmented control 1–5 below
   - **When info expanded:** descriptor panel with all 5 level cards (currently selected highlighted) + note textarea
6. **Session summary section** (after all categories)
   - Section header with "Draft from scores" link (sparkle icon, AI-assist V1.5)
   - Single textarea, optional, "How did the session go overall?" placeholder
   - Foot: "Visible to trainee and parent" disclosure + character count
7. **Bottom tab bar** — Today active

## Components used

- Segmented control (5 segments, selected lifts to white-on-tinted)
- Score pill (variants: `Not rated` neutral, `{level} {label}` accent)
- Info button (toggle, accent when active)
- Descriptor panel with 5 selectable cards (numbered circle + label + descriptor text)
- Note row (rounded card with textarea, "Catatan / Note" label)
- Session summary card with prompt + textarea + footer with disclosure
- Sparkle icon (`ti-sparkles`) for AI suggest action
- Tabler icons: `ti-info-circle`, `ti-chevron-up/down`, `ti-eye`, `ti-sparkles`

## Data requirements

| Field | Source | Notes |
|-------|--------|-------|
| Trainee identity | `trainees` | name, current tier |
| Session metadata | Created on screen open or passed from previous screen | session #, date, time |
| Skills list (27) + categories | `skills` table where `is_platform_default=true` OR matches workspace overrides | Order by `display_order` |
| Per skill: previous score | Latest `assessments.level` per skill_id | For prefill display |
| Level descriptors per skill | `skill_level_descriptors` for current locale | 5 strings per skill |
| Per skill: current input | Local component state | Not persisted until Save |
| Session summary text | Local component state | Not persisted until Save |
| Per skill notes | Local component state, keyed by skill code | Not persisted until Save |

## Interactions

| Action | Result |
|--------|--------|
| Tap segmented control button | Set score for that skill. If already selected, clear (toggle off). |
| Tap info icon | Expand descriptor panel for that skill. Tap again to collapse. |
| Tap descriptor card inside panel | Set score to that level. Same as tapping the segmented button. |
| Type in note textarea | Save to local state, keyed by skill code |
| Type in summary textarea | Save to local state |
| Tap "Draft from scores" | Call Claude inference with current scores + skill context, populate summary with editable draft |
| Tap category header | Toggle that category open/closed. Single-open mode (opening one closes the others) by default. |
| Tap Save | Persist all scores + notes + summary in one transaction. Navigate back. |
| Tap back without saving | Show confirmation: "Discard changes?" if any input has been modified. |

## States

### Default
Trainee with prior assessments — segmented controls show last known score selected. Summary textarea empty.

### First assessment (no prior scores)
All segments empty. No "Score: X" shown — placeholders read "Not rated". Summary still empty.

### Loading
Skeleton: trainee strip + 4 category headers. Skip skeletoning the segmented controls; users can interact as soon as identity loads.

### Saving
Save button shows spinner inline; disabled during save. Other interactions disabled. On success: navigate back. On failure: show toast "Couldn't save · Tap to retry" — keep state intact so coach doesn't lose work.

### Offline
Save still works — writes to local queue, shows sync pill "Saved offline" on the trainee profile after navigating back. Banner persists. See `10-error-offline-states.md`.

## Workspace type adaptations

No structural differences. Both club and personal coaches use the identical assessment flow.

## Localization

| EN | ID |
|----|----|
| Today (back button) | Hari ini |
| Save | Simpan |
| Beginner / Lower Bronze / Bronze | Pemula / Perunggu Muda / Perunggu |
| 10 May, session 42 | 10 Mei, sesi 42 |
| 1 Learning ... 5 Mastery | 1 Belajar ... 5 Mahir |
| Not rated | Belum dinilai |
| 3 Functional | 3 Fungsional |
| Show descriptors | (icon-only, no label) |
| Hide descriptors | (icon-only, no label) |
| Note (optional) | Catatan (opsional) |
| Optional placeholder text per skill | "Observasi untuk {skill}…" |
| Session summary | Ringkasan sesi |
| Draft from scores | Buat draf dari skor |
| How did the session go overall? | Bagaimana sesi berjalan secara keseluruhan? |
| Optional | Opsional |
| Visible to trainee and parent | Terlihat oleh trainee dan orang tua |
| Discard changes? | Buang perubahan? |
| Couldn't save · Tap to retry | Gagal simpan · Tap untuk coba lagi |

**Categories (Technical/Tactical/Physical/Mental) and skill names (Forehand drive, Bandeja, Víbora, etc.) stay in original.** Level labels and descriptors translate fully.

## Design rationale

**Why segmented control (tap-based) instead of slider.**
- The 1–5 scale is *discrete*; each level has its own descriptor. Slider implies a continuous gradient that contradicts the rubric.
- Apple's UISegmentedControl is the platform pattern for "pick one of N".
- Tap is faster than drag-release for coaches scoring 27 skills per session.
- On mobile, dragging exactly to "3" vs "4" is fiddly; tap is unambiguous.

**Why descriptors expand inline, not in a modal sheet.** Coaches need the descriptor *while* scoring, not as a separate flow. Modal sheets break context. Inline expansion keeps the segmented control + descriptor + note all in one view.

**Why descriptor cards are also tappable (set the score).** This gives slow-input mode for free: a coach who's still calibrating their judgment can read the descriptor and tap it to assign that level. Confident coaches use the segmented control; learning coaches use the descriptor cards. Both work.

**Why single-open category mode by default.** Reduces vertical scroll; coach focuses on one category at a time. They can still toggle open multiple if they want, but it's not the default.

**Why the session summary is at the bottom, after all skills.** Reflection follows action. Coach scores the skills first, *then* steps back and writes the holistic note. Putting it at the top inverts the flow.

**Why "Visible to trainee and parent" disclosure under the summary.** Coaches need to know, *before* writing, that this isn't a private internal note. They will word things differently when they know it's customer-facing. Per-skill notes can stay internal; this disclosure is for the summary specifically.

**Why "Draft from scores" is a button, not auto-fill.** Auto-filled summaries that get sent to parents unedited are a product disaster waiting to happen. The sparkle button is opt-in: coach taps when they want help, edits the result, then saves. Human-edited AI-assist > unattended AI-write.

**Why no character count limit on the summary.** Coaches who want to write paragraphs shouldn't get stopped. The visible char count is informational only.

**Why optional, not required.** Forcing summary input dilutes the value of real summaries. Some sessions genuinely don't have anything narrative to add.

## Out of MVP scope

- Voice → text input for the summary (V1.5 — coaches' hands are wet/sweaty)
- Per-skill voice notes (V2)
- Photo attachment per skill (V2 — show technique correction picture)
- Compare with previous assessment side-by-side (V1.5)
- Session focus tags as multi-select chips at the top (V1.5)
- Custom rubric overrides per skill (V2)
- Bulk-set "all category to level X" (V2 — edge case)
- Auto-save while typing (V1.5 — Save button is fine for MVP)

## Open questions

1. Should pressing Save with zero scores entered show a warning? **Recommendation:** yes, "No skills assessed — save anyway?" — sometimes coach only writes a summary without scoring (e.g., observation-only session).
2. If a coach starts an assessment and abandons mid-way, does it auto-save as draft? **Recommendation:** V1.5. For MVP, "Discard changes?" confirmation on back is enough.
3. How do we handle a coach who scores level 1 then taps level 1 again (toggle off)? Does the row revert to "Not rated"? **Yes** — that's the documented toggle behavior.
4. AI-suggest draft: which model, what context window? **Recommendation:** Claude Haiku for speed/cost, prompt includes scores + level labels + previous summary if any. Keep summary < 200 tokens by design.

## Related screens

- `03-coach-trainee-profile.md` — typical entry point ("New assessment" button)
- `02-coach-today.md` — alternative entry point (tap session row)
- `08-pdf-report.md` — where the summary text ends up monthly
- `05-trainee-home.md` — where the summary surfaces immediately after Save
