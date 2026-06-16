# TennisCoach — Tennis Curriculum & Multi-Sport Workspace Implementation Plan (v0.1)

> Tennis V2 activation plan. Defines the skill ontology, tier model, graduation thresholds, and database seed needed to surface tennis on the platform — and the multi-sport workspace refactor needed for one coach or one club to operate across both padel and tennis. Built on ITF (International Tennis Federation) coaching framework. Mirrors `padel-skill-framework-v0.md` structure for cross-sport consistency.

> **Status:** v0.1 draft. v0 covered tennis as a single-sport activation. v0.1 expands scope to multi-sport workspaces, because real Indonesian clubs run both padel and tennis under one roof and one billing relationship. Refine all skill content with a certified ITF / PTR / RPT coach advisor before locking into production. Budget ~2 weeks of advisor time for curriculum, plus ~2–3 weeks of engineering for the multi-sport refactor.

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| v0 | 2026-05 | Initial tennis framework. Assumed one workspace = one sport. |
| v0.1 | 2026-05 | Added multi-sport workspace architecture (Section 3). Updated DB, UI, timeline, risks. Curriculum content (Sections 4–9) unchanged. |

---

## 0. Context & cost

Two streams of work, sequenced:

| Stream | Effort | Owner |
|--------|--------|-------|
| **A. Multi-sport workspace refactor** (Section 3) | ~2–3 weeks engineering | Engineering |
| **B. Tennis curriculum authoring** (Sections 4–9) | ~2 weeks advisor + Claude | Advisor + Claude |
| **C. Tennis seed & UI activation** (Sections 10–11) | ~3 days engineering | Engineering |
| **D. Pilot with multi-sport clubs** | 4–6 calendar weeks | Product |

Streams A and B run in parallel. C and D depend on both. Total calendar time: ~3 months from kickoff to tennis GA.

**Key shift from v0:** v0 assumed activating tennis was a 3-day engineering job because the data model already had `sports.is_active` + sport-scoped skills. That remained true — but it's not enough. Without the multi-sport refactor, a club that runs padel and tennis must create two separate workspaces, which fragments billing, branding, and athlete identity. The refactor is the right cost to pay now, not later.

---

## 1. How to use this document

1. **Engineering — multi-sport refactor:** Section 3 is the schema and API spec. Section 10 carries the migration order. Section 11 lists every UI touchpoint.
2. **Engineering — tennis seed:** Sections 4 (skills), 6 (tiers), 7 (thresholds), 10 (seed data).
3. **Advisor engagement:** Sections 2, 4, 5, 7, 16 are the advisor brief.
4. **Product / pilot:** Sections 12, 13, 14, 15.
5. **Pilot clubs:** Show only user-facing labels (EN + ID). Skill codes stay internal.

---

## 2. ITF alignment — what we adopt, what we diverge from

The ITF publishes a coaching framework covering technical, tactical, physical, and mental development, plus a junior pathway (Play and Stay) and a rating system (WTN). We adopt selectively:

| ITF element | Our stance |
|-------------|------------|
| **Four-category model** (technical / tactical / physical / mental) | **Adopt.** Matches our platform's locked 4-category ontology and matches padel. Trainees moving across sports see consistent language. |
| **Five tactical game situations** (serve / return / baseline rally / approach + net / defensive) | **Adopt and slightly extend.** These map cleanly to TACT skills with two additions (doubles tactics, reading the game). |
| **Play and Stay stages** (Red / Orange / Green / Yellow) | **Inform but don't adopt as tier names.** We mirror padel's Beginner → Diamond progression so the platform's tier metaphor stays cross-sport. ITF stages are referenced in early-tier descriptors and cited in coach-facing curriculum notes. |
| **WTN (World Tennis Number, 1–40)** | **Reference only.** Each tier lists an equivalent WTN band as informational context. We do not import WTN as the rating engine — it's externally calculated, requires match results we don't capture at MVP, and is too granular for curriculum tiering. V2+ feature: pull a player's WTN from match history if/when we add tournament integration. |
| **ITF Coaching Education levels** (L1 / L2 / L3) | **Inform descriptors.** Level 1 syllabus drives Beginner–Bronze descriptors. Level 2 drives Silver–Gold. Level 3 drives Platinum–Diamond. |
| **Court types & ball pressure as part of curriculum** | **Out of scope at v0.** Coach can record session context in the notes field. V1.5 may add structured ball type / court type to the session model. |
| **Wheelchair tennis as separate competency stream** | **Out of scope at v0.** Future: separate `sports` row, separate curriculum. |
| **Junior vs adult separate curricula** | **Out of scope at v0.** Same skill ontology applies, progression speed differs. V1.5 may add age-adjusted tier thresholds. |

Headline mental model: **ITF's game-situation framework drives tactical skills, ITF's L1–L3 syllabus drives technical descriptors, ITF's Play and Stay informs the bottom three tiers without renaming them.**

---

## 3. Multi-sport workspace architecture (platform refactor)

This section supersedes the v0 assumption that one workspace = one sport. It's a cross-cutting platform change that benefits padel-only workspaces too (a padel club deciding to add tennis later just enables a sport, doesn't create a new workspace).

### 3.1 Product requirements

| # | Requirement | Why |
|---|-------------|-----|
| 1 | A workspace can offer 1+ sports | Real clubs run both padel and tennis under one roof |
| 2 | A coach (workspace member) can be qualified in 1+ sports within a workspace | Some coaches specialize; some do both. Don't block legitimate assessments, don't allow uncertified assessments |
| 3 | An athlete can be enrolled in 1+ sports at the same workspace | A junior who plays padel Tuesday and tennis Thursday is one person, not two records |
| 4 | A session belongs to exactly one sport | A session is one block of court time in one sport. No mixed sessions. |
| 5 | An athlete's tier is per-sport | A Bronze padel player may be Silver in tennis. The tier badge shows the relevant sport's tier. |
| 6 | A workspace's curriculum selection is per-sport | Padel uses padel-default-appa; tennis uses tennis-default-itf. Independent. |
| 7 | Pricing remains per-workspace, not per-sport | Club Pro tier includes all sports. No per-sport seat math at MVP. |
| 8 | A workspace can enable / disable a sport in settings | Lifecycle: add tennis when courts open; archive padel if courts close. |

### 3.2 What changes — the headline diagram

```
BEFORE (v0)
─────────────────────────────────────────────
workspaces                athletes
  sport_id ──────►          (single record, implicitly padel)
  curriculum_id

workspace_memberships     sessions
  (no sport context)        (sport implicit)


AFTER (v0.1)
─────────────────────────────────────────────
workspaces                workspace_sports ◄────── new
  (sport_id DROPPED)        workspace_id
  (curriculum_id DROPPED)   sport_id
                            curriculum_id
                            is_active

athletes                  athlete_sports ◄──────── new
  display_name              athlete_id
  date_of_birth             sport_id
                            joined_sport_at
                            archived_at

workspace_memberships     membership_sports ◄──── new
  workspace_id              membership_id
  user_id                   sport_id
  role                      certification
                                                  ┌──── new column
sessions ◄─── + sport_id ─┘

assessments ◄── sport derivable via skill.sport_id, but denormalize for query speed
```

### 3.3 Schema changes — concrete SQL

```sql
-- Migration: 20260601_multisport_workspaces.sql

BEGIN;

-- ─── New: workspace_sports ──────────────────────────────────────────────
CREATE TABLE workspace_sports (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  sport_id        UUID NOT NULL REFERENCES sports(id),
  curriculum_id   UUID NOT NULL REFERENCES curricula(id),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  enabled_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  archived_at     TIMESTAMPTZ,
  UNIQUE (workspace_id, sport_id)
);

CREATE INDEX idx_workspace_sports_workspace ON workspace_sports (workspace_id) WHERE is_active = TRUE;

-- ─── Backfill from existing workspaces.sport_id ────────────────────────
INSERT INTO workspace_sports (workspace_id, sport_id, curriculum_id, is_active)
SELECT id, sport_id, curriculum_id, TRUE
FROM workspaces
WHERE sport_id IS NOT NULL;

-- ─── Drop old columns (only after API switches over — see deploy plan) ─
-- ALTER TABLE workspaces DROP COLUMN sport_id;
-- ALTER TABLE workspaces DROP COLUMN curriculum_id;
-- ↑ Deferred to a follow-up migration so we can roll back if API has issues.

-- ─── New: athlete_sports ───────────────────────────────────────────────
CREATE TABLE athlete_sports (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  athlete_id        UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  sport_id          UUID NOT NULL REFERENCES sports(id),
  joined_sport_at   DATE NOT NULL DEFAULT CURRENT_DATE,
  archived_at       TIMESTAMPTZ,
  UNIQUE (athlete_id, sport_id)
);

CREATE INDEX idx_athlete_sports_athlete ON athlete_sports (athlete_id) WHERE archived_at IS NULL;
CREATE INDEX idx_athlete_sports_sport   ON athlete_sports (sport_id) WHERE archived_at IS NULL;

-- ─── Backfill: existing athletes inherit their workspace's single sport ─
INSERT INTO athlete_sports (athlete_id, sport_id, joined_sport_at)
SELECT a.id, w.sport_id, a.joined_at
FROM athletes a
JOIN workspaces w ON w.id = a.workspace_id
WHERE w.sport_id IS NOT NULL;

-- ─── New: membership_sports ────────────────────────────────────────────
CREATE TABLE membership_sports (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  membership_id   UUID NOT NULL REFERENCES workspace_memberships(id) ON DELETE CASCADE,
  sport_id        UUID NOT NULL REFERENCES sports(id),
  certification   VARCHAR(120),                       -- optional: 'ITF L2', 'APPA L1'
  certified_at    DATE,
  UNIQUE (membership_id, sport_id)
);

CREATE INDEX idx_membership_sports_membership ON membership_sports (membership_id);

-- ─── Backfill: existing memberships get the workspace's sport ──────────
INSERT INTO membership_sports (membership_id, sport_id)
SELECT m.id, w.sport_id
FROM workspace_memberships m
JOIN workspaces w ON w.id = m.workspace_id
WHERE w.sport_id IS NOT NULL;

-- ─── Modify: sessions get explicit sport_id ────────────────────────────
ALTER TABLE sessions ADD COLUMN sport_id UUID REFERENCES sports(id);

UPDATE sessions s
SET sport_id = w.sport_id
FROM workspaces w
WHERE w.id = s.workspace_id AND w.sport_id IS NOT NULL;

ALTER TABLE sessions ALTER COLUMN sport_id SET NOT NULL;

CREATE INDEX idx_sessions_workspace_sport_date ON sessions (workspace_id, sport_id, scheduled_at);

-- ─── Modify: assessments get denormalized sport_id (query perf) ────────
ALTER TABLE assessments ADD COLUMN sport_id UUID REFERENCES sports(id);

UPDATE assessments a
SET sport_id = s.sport_id
FROM skills s
WHERE s.id = a.skill_id;

ALTER TABLE assessments ALTER COLUMN sport_id SET NOT NULL;

CREATE INDEX idx_assessments_athlete_sport_date ON assessments (athlete_id, sport_id, assessed_at DESC);

-- ─── New: athlete_sport_tiers (denormalized current tier per sport) ───
CREATE TABLE athlete_sport_tiers (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  athlete_id      UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  sport_id        UUID NOT NULL REFERENCES sports(id),
  tier_id         UUID NOT NULL REFERENCES tiers(id),
  promoted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (athlete_id, sport_id)
);

CREATE INDEX idx_athlete_sport_tiers_athlete ON athlete_sport_tiers (athlete_id);

-- Populated by the existing tier-calculation job, now run per-(athlete, sport)

COMMIT;
```

### 3.4 RLS implications

Row Level Security policies are unchanged. They scope by `workspace_id` — they don't know or care about sport. Sport filtering happens at the query layer:

- "List sessions in this workspace" → `WHERE workspace_id = $1` (RLS) `AND sport_id = $2` (app filter)
- "List athletes a coach can assess" → `WHERE workspace_id = $1` (RLS) `AND EXISTS (membership_sports ms WHERE ms.membership_id = $coach AND ms.sport_id = $sport)` (app filter)

One new app-layer check is the coach-sport authorization on `POST /assessments`:

```python
async def authorize_assessment(coach_membership_id, sport_id):
    qualified = await db.fetch_one(
        "SELECT 1 FROM membership_sports "
        "WHERE membership_id = $1 AND sport_id = $2",
        coach_membership_id, sport_id
    )
    if not qualified:
        raise Forbidden("Coach is not qualified to assess this sport")
```

This isn't enforced via RLS because cross-table policies are awkward in Postgres. App-layer check is fine; it's defense-in-depth for the workspace-tenancy boundary that RLS already enforces.

### 3.5 API surface changes

Endpoints that **gain a sport filter or sport parameter**:

| Endpoint | Change |
|----------|--------|
| `GET /workspaces/:id` | Response includes `sports[]` array (active sports, each with curriculum reference) |
| `GET /workspaces/:id/athletes` | Optional `?sport_id=X` query param; default returns all sports |
| `GET /workspaces/:id/sessions/today` | Returns all sports, each session has `sport_id` |
| `POST /workspaces/:id/athletes` | Body includes `sport_ids[]` (which sports this athlete trains) |
| `PATCH /athletes/:id/sports` | New endpoint: add or remove sport enrollment for an athlete |
| `POST /workspaces/:id/invites` | Body includes `sport_ids[]` (which sports this coach is qualified for) |
| `PATCH /memberships/:id/sports` | New endpoint: update a coach's sport qualifications |
| `POST /sessions` | Body requires `sport_id` |
| `POST /assessments` | Validates coach is qualified for the sport of the skill being assessed |
| `GET /athletes/:id` | Response includes `enrolled_sports[]` and `tier_per_sport[]` |
| `GET /athletes/:id/skills` | Required `?sport_id=X` parameter — skills are sport-scoped |
| `GET /athletes/:id/tier` | Required `?sport_id=X` parameter |
| `GET /athletes/:id/report/:month` | Required `?sport_id=X` — one PDF per sport |
| `POST /workspaces/:id/sports` | New endpoint: enable a new sport on a workspace (admin-only) |
| `DELETE /workspaces/:id/sports/:sport_id` | New endpoint: archive a sport (admin-only) |

All endpoints stay backward-compatible during migration: if a workspace has exactly one active sport and the request omits `sport_id`, the server defaults to that sport. Clients are migrated to pass `sport_id` explicitly during the rollout window.

### 3.6 Tier recalculation

The existing job that recomputes a trainee's tier after each assessment now runs **per (athlete, sport)** instead of per athlete. Code-wise: take the existing function, wrap in a loop over `athlete_sports`.

```python
async def recalc_tier(athlete_id: UUID):
    sports = await get_athlete_sports(athlete_id)
    for sport_id in sports:
        await recalc_tier_for_sport(athlete_id, sport_id)

# Triggers: post-assessment write hook, nightly batch
```

---

## 4. Skill list (29 total)

> _Unchanged from v0. Curriculum content sections (4–9) are sport-curriculum work, independent of the workspace architecture refactor in Section 3._

Codes are stable IDs. Indonesian labels follow the platform rule — translate generic terms (forehand, volley), keep universal tennis vocabulary in English (kick serve, slice). PELTI-aligned where Indonesian terminology exists.

### A. Technical — 14 skills

| Code | Skill | Indonesian | ITF reference | Notes |
|------|-------|------------|---------------|-------|
| `TENNIS_TECH_FH_DRIVE` | Forehand drive | Forehand drive | L1 groundstroke | Topspin baseline drive |
| `TENNIS_TECH_BH_DRIVE` | Backhand drive | Backhand drive | L1 groundstroke | One- or two-handed; coach tags variant in notes, single skill |
| `TENNIS_TECH_FH_SLICE` | Forehand slice | Forehand slice | L2 variant | Underspin defensive / approach |
| `TENNIS_TECH_BH_SLICE` | Backhand slice | Backhand slice | L1 (1HBH) / L2 (2HBH) | Underspin; chip return, approach, defense |
| `TENNIS_TECH_FH_VOLLEY` | Forehand volley | Voli forehand | L1 net play | First contact at net |
| `TENNIS_TECH_BH_VOLLEY` | Backhand volley | Voli backhand | L1 net play | First contact at net |
| `TENNIS_TECH_HALF_VOLLEY` | Half-volley | Half-volley | L2 transition | Pickup off the bounce, transition zone |
| `TENNIS_TECH_SERVE_FLAT` | Flat / first serve | Servis pertama | L1 serve | Power-oriented first delivery |
| `TENNIS_TECH_SERVE_SPIN` | Spin serve (kick / slice) | Servis spin | L2 serve | Second-serve reliability with margin |
| `TENNIS_TECH_RETURN` | Return of serve | Pengembalian servis | L1 return | Block / chip / drive return |
| `TENNIS_TECH_SMASH` | Overhead smash | Smash | L1 finishing shot | High-ball finisher |
| `TENNIS_TECH_LOB` | Lob (offensive + defensive) | Lob | L1 / L2 | Both defensive globo and offensive topspin lob |
| `TENNIS_TECH_DROP` | Drop shot | Drop shot | L2 finesse | Short ball, both wings |
| `TENNIS_TECH_APPROACH` | Approach shot | Approach shot | L2 transition | Mid-court ball that earns net position |

### B. Tactical — 7 skills

Five mirror ITF's tactical game situations. Two extend for doubles and anticipation.

| Code | Skill | Indonesian | ITF reference | Notes |
|------|-------|------------|---------------|-------|
| `TENNIS_TACT_SERVE_PATTERNS` | Serve patterns | Pola servis | Game situation 1 | Placement, serve+1, body / wide / T |
| `TENNIS_TACT_RETURN_PATTERNS` | Return patterns | Pola pengembalian | Game situation 2 | Position, intent, return-and-attack |
| `TENNIS_TACT_BASELINE` | Baseline rally play | Rally baseline | Game situation 3 | Cross-court rhythm, direction change, depth control |
| `TENNIS_TACT_NET_PLAY` | Net play & approach | Permainan net | Game situation 4 | Closing, court coverage at net, finishing |
| `TENNIS_TACT_DEFENSE` | Defensive play | Bertahan | Game situation 5 | Lob defense, neutralizing, getting passed |
| `TENNIS_TACT_DOUBLES` | Doubles tactics | Taktik ganda | ITF doubles syllabus | I-formation, Australian, poaching, partner coverage |
| `TENNIS_TACT_READING` | Reading the game | Membaca permainan | L2 anticipation | Reading opponent's contact, court position, patterns |

### C. Physical — 4 skills

| Code | Skill | Indonesian | Notes |
|------|-------|------------|-------|
| `TENNIS_PHYS_FOOTWORK` | Footwork & court coverage | Footwork & cakupan lapangan | Side-shuffle, cross-step, recovery |
| `TENNIS_PHYS_SPLIT` | Split step & reaction | Split step & reaksi | Timing on opponent's contact |
| `TENNIS_PHYS_ENDURANCE` | Endurance | Stamina | Sustaining quality across 2–3 sets |
| `TENNIS_PHYS_POWER` | Power & explosiveness | Power & eksplosivitas | Serve speed, ground stroke pace, first-step |

### D. Mental — 4 skills

| Code | Skill | Indonesian | Notes |
|------|-------|------------|-------|
| `TENNIS_MENT_FOCUS` | Focus & concentration | Fokus & konsentrasi | Point-to-point presence |
| `TENNIS_MENT_COMPOSURE` | Composure under pressure | Ketenangan di bawah tekanan | Break points, tiebreaks, deciding sets |
| `TENNIS_MENT_DECISION` | Decision-making speed | Kecepatan keputusan | Shot selection under time pressure |
| `TENNIS_MENT_RESILIENCE` | Resilience after errors | Bangkit dari kesalahan | Bounce-back rate, body language |

---

## 5. Skill level descriptors

Each skill carries five descriptors on the locked 1–5 scale: 1 Learning · 2 Developing · 3 Functional · 4 Proficient · 5 Mastery.

Full descriptor sets for the 14 technical skills are in the v0 draft and seeded into `apps/api/src/skills/data/tennis.py`. Tactical, physical, and mental descriptors are drafted in seed and finalized with the advisor before v1 lock.

_(Full descriptor blocks omitted in this version for brevity — they're unchanged from v0 and live in the seed file.)_

---

## 6. Tier structure

Seven tiers, mirroring padel. Game-style labels by default; Skill-style and Custom available per `06-workspace-settings.md`.

| Tier code | Game label EN / ID | Skill label EN / ID | WTN band | Play and Stay equivalent | Typical archetype |
|-----------|----|----|----|----|----|
| `BEGINNER` | Beginner / Pemula | Beginner / Pemula | 40 | Red ball | First sessions, learning to rally |
| `LOWER_BRONZE` | Lower Bronze / Perunggu Bawah | Improver / Tingkat Lanjut Awal | 35–39 | Orange ball | Can rally, basic serve, working on volleys |
| `BRONZE` | Bronze / Perunggu | Intermediate / Menengah | 25–34 | Green / early Yellow | All shots introduced, point construction emerging |
| `SILVER` | Silver / Perak | Upper intermediate / Menengah Atas | 18–24 | Yellow — club | Solid club player, all shots functional |
| `GOLD` | Gold / Emas | Advanced / Mahir | 12–17 | Yellow — competitive | Tournament-ready, weapons developing |
| `PLATINUM` | Platinum / Platinum | Expert / Ahli | 6–11 | Yellow — sectional | National junior or strong sectional adult |
| `DIAMOND` | Diamond / Berlian | Elite / Elit | 1–5 | Yellow — national+ | National level or top regional ranking |

WTN bands are coach-facing reference points only.

---

## 7. Tier graduation thresholds

_(Unchanged from v0 — see prior version for the per-tier minimum skill matrices.)_

---

## 8. Tier focus areas

_(Unchanged from v0.)_

---

## 9. Skill introduction matrix

_(Unchanged from v0.)_

---

## 10. Database implementation — combined plan

Two migrations, sequenced. The multi-sport refactor goes first (Stream A); tennis seed second (Stream C).

### 10.1 Migration sequence

```
M1 — 20260601_multisport_workspaces.sql   (Section 3.3 — DDL + backfill)
M2 — 20260605_api_writes_to_new_tables.py (deploy: API writes to both old and new columns)
M3 — 20260612_api_reads_from_new_tables.py(deploy: API reads from new tables only)
M4 — 20260619_drop_workspace_sport_cols.sql (drop workspaces.sport_id, workspaces.curriculum_id)
M5 — 20260626_activate_tennis.sql         (Section 10.2 — tennis seed)
```

The 3-week gap between M2 and M4 is the rollback window. If anything breaks, the old columns are still populated.

### 10.2 Tennis seed

```sql
-- M5: 20260626_activate_tennis.sql

BEGIN;

UPDATE sports SET is_active = TRUE WHERE code = 'tennis';

INSERT INTO curricula (sport_id, workspace_id, code, name_en, name_id, description_en, description_id)
SELECT id, NULL, 'tennis-default-itf', 'Tennis (ITF default)', 'Tenis (ITF default)',
       'Default tennis curriculum aligned with ITF coaching framework.',
       'Kurikulum tenis default berdasarkan kerangka pelatih ITF.'
FROM sports WHERE code = 'tennis';

-- Skills, descriptors, tiers, requirements: populated by seed.py
COMMIT;
```

Seed code lives in `apps/api/scripts/seed.py` and constants in `apps/api/src/skills/data/tennis.py`.

### 10.3 No RLS changes

RLS policies scope by `workspace_id` and remain sport-agnostic. Sport filtering is an app-layer concern (Section 3.4).

---

## 11. UI activation — combined plan

The multi-sport refactor introduces sport context to many screens. Existing screens are data-driven, but they need a sport-aware shell.

### 11.1 New primitive: sport context

A workspace's active sport context lives in the URL (e.g. `/workspaces/abc/padel/today`) and in Zustand. When a workspace has one sport, the context is invisible — every screen renders that sport. When a workspace has 2+ sports, the context is explicit.

```
URL pattern:
  /workspaces/:workspace_id/:sport_code/today
  /workspaces/:workspace_id/:sport_code/trainees
  /workspaces/:workspace_id/:sport_code/trainees/:athlete_id
  /workspaces/:workspace_id/settings              ← workspace-global, no sport
```

Cross-sport screens (Coach Today's "all sports" view, Settings) have no `:sport_code` segment.

### 11.2 Sport switcher component

A new chip-style switcher appears in the top bar of sport-scoped screens:

```
┌─────────────────────────────────────────────────────┐
│  Senayan Sports Club                                │
│  ┌────────┐ ┌────────┐ ┌─────────────┐              │
│  │ Padel  │ │ Tennis │ │ All sports  │              │
│  └────────┘ └────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────┘
```

Selected sport is filled with `--accent-bg`; others are hairline-bordered. "All sports" is shown only on screens that support a multi-sport view (Coach Today, Trainees list). On screens that require a single sport context (Assessment, Trainee profile), the switcher hides "All sports".

For single-sport workspaces, the switcher is hidden entirely. The shell is the same; the chrome adapts.

### 11.3 Screen-by-screen changes

#### Coach Today (`02-coach-today.md`)

- Default view: **All sports.** Sessions list shows every sport's sessions today, sorted by time. Each session row has a small sport chip ("Padel" / "Tennis") next to the athlete name.
- Filter chips at top — tapping "Padel" filters to padel-only; tapping "All sports" returns.
- Trainee list section below has the same filtering.

#### Trainees list (`03-coach-trainee-profile.md`)

- Each trainee row shows sport chips inline with the name: `Andi Pratama · [Padel] [Tennis]`
- If a trainee is in only one sport, one chip; both, two chips.
- Filter at top: All / Padel / Tennis.
- Tier badge on the row shows the tier for the **currently filtered sport**. If "All sports" is selected, show only the higher tier with a small "+1" indicator if there's another sport.

#### Trainee profile

Reworked with a **sport tab strip** below the header:

```
┌─────────────────────────────────────────────────────┐
│   ←  Trainees                                  ⋯    │
│                                                     │
│   AP  Andi Pratama                                  │
│       Joined Sep 2025                               │
│                                                     │
│  ┌─────────┐ ┌─────────┐                            │
│  │ Padel ● │ │ Tennis  │   ← sport tabs (filled = active)
│  │ Bronze  │ │ Bronze  │   ← tier per sport
│  └─────────┘ └─────────┘                            │
│                                                     │
│   [stats] [tier progress] [radar] [sessions]        │
│   ↑ all scoped to selected sport                    │
└─────────────────────────────────────────────────────┘
```

- Header (avatar, name, joined date) is sport-neutral
- Tab strip shows enrolled sports only with the tier badge per sport
- Below the tabs: stats, tier progress, radar, blockers, session log — all scoped to active sport
- Switching tabs reloads the lower section instantly (TanStack Query keyed by sport_id)

#### Skill assessment (`04-coach-assessment.md`)

- Entry must pick a sport if the trainee is in multiple. From Coach Today: tap session → already sport-scoped. From Trainees → "Assess" button: if trainee is in 1 sport, go directly; if 2, show a "Which sport?" picker before opening the assessment.
- The assessment header reads `Andi Pratama · Tennis · Bronze · 10 May, session 12`
- Skill list shown is only the active sport's skills. Categories collapse the same way; descriptor info icons unchanged.
- Coach without the right sport qualification: the "Assess" button is disabled with a tooltip ("You're not qualified to assess tennis in this workspace. Ask an admin.").

#### Add trainee (`07-invite-and-onboarding.md`)

- Form gains a "Sports" multi-select (segmented control style):

```
Sports they train in
┌────────────────────────────────────────┐
│  ◉ Padel        ○ Tennis               │
└────────────────────────────────────────┘
                              ↑ multi-select; both can be picked
```

- Defaults to the sport currently in URL context (if scoped) or all workspace sports (if "All sports" view)
- Validation: at least one sport required

#### Invite coach (workspace settings → members)

- The invite form gains "Sports this coach is qualified for"
- Multi-select; required
- Optional certification field per sport ("e.g. ITF L2")
- A coach with only padel selected cannot assess tennis trainees (Section 3.4)

#### Workspace settings — new "Sports" panel

A new section in `06-workspace-settings.md`:

```
┌─ Sports ──────────────────────────────────────────┐
│                                                   │
│  Padel                              Active   ●    │
│  Curriculum: APPA default                         │
│                                                   │
│  Tennis                             Active   ●    │
│  Curriculum: ITF default                          │
│                                                   │
│  ───────────────────────────────                  │
│  + Add a sport                                    │
└───────────────────────────────────────────────────┘
```

- Each row shows sport name, current curriculum, active toggle
- Adding a sport: bottom sheet to pick from available sports (initially padel / tennis), then pick curriculum (default or, at Club Pro, a custom one)
- Archiving a sport: confirmation modal explaining trainees and sessions in that sport will be hidden but not deleted
- Solo coach plan: limited to 1 sport at MVP (upsell at sport-add). Club Starter: 1 sport. Club Pro: unlimited sports.

#### Bottom nav (mobile)

Unchanged. Today / Trainees / Sessions / Reports / Settings. The sport context lives one level above the nav — chosen in the top bar — and persists across nav taps.

#### PDF report (`08-pdf-report.md`)

- One report **per sport per month** per trainee
- Sport name appears in the header next to the club name: `Senayan Sports Club · Tennis · April 2026`
- If a trainee is in two sports, two PDFs generated; the parent gets two links
- Permalink format: `/r/andi-tennis-2026-04` and `/r/andi-padel-2026-04` (sport segment added)
- Multi-sport combined report deferred to V1.5 (not the right MVP shape — better as two focused reports)

#### Trainee home (`05-trainee-home.md`)

- If trainee is in 1 sport: identical to today
- If 2 sports: sport tab strip below the header, same pattern as coach trainee profile
- Each tab has tier progress, recent gains, upcoming session, coach note — sport-scoped
- "Upcoming session" badge shows sport icon for clarity

#### Empty states (`09-empty-states.md`)

- New empty state: workspace has multiple sports but no athletes in this sport yet — "No tennis trainees yet. Padel has 12. Add your first tennis trainee →"
- New empty state: coach is qualified for padel but viewing tennis — "You don't coach tennis at this club. Ask an admin to give you tennis access, or switch to padel."

### 11.4 Workspace naming nudge

When a single-sport workspace adds a second sport, the system inspects the workspace name. If it contains "Padel" or "Tennis", a one-time non-blocking banner appears in Settings:

> Your workspace is called "Senayan Padel Club" but now offers tennis too. Consider renaming.
> [ Rename ]  [ Keep as-is ]

Soft nudge, dismissable. Don't auto-rename.

### 11.5 Localization

All new copy (sport switcher, sport tab strip, sport pickers, settings panel) goes through `i18next` with EN + ID keys. New keys are namespaced under `multisport.*` in the locale files.

---

## 12. Advisor engagement

_(Unchanged from v0 — see prior version. Tennis curriculum advisor is one workstream; multi-sport refactor is an engineering workstream and needs no advisor input.)_

---

## 13. Pilot launch plan — refined for multi-sport

### 13.1 Pilot club profile (revised)

Target 2–3 clubs that **already run both padel and tennis** (or are about to). These clubs will exercise the multi-sport workspace from day one, which gives much better signal than a tennis-only pilot.

Likely candidates in Jakarta: clubs in BSD and Pondok Indah that have both padel courts (often newer addition) and established tennis programs. Ask the founder's existing padel pilot clubs whether they also run tennis or plan to — they're the warmest leads.

### 13.2 Pilot phases

| Phase | Weeks | Focus |
|-------|-------|-------|
| **0. Migrate existing padel workspaces** | 1 | Run M1–M4 migrations. Existing padel-only workspaces continue working unchanged (one sport in workspace_sports table). |
| **1. Internal multi-sport dogfood** | 1 | Set one internal test workspace to "padel + tennis" and run all flows. Find UI gaps. |
| **2. Tennis curriculum advisor lock** | 2 | Independent of phase 1. Advisor finalizes descriptors and thresholds. |
| **3. Tennis seed deploy** | 0.5 | Run M5. Tennis available to all workspaces. |
| **4. Multi-sport pilot** | 4–6 | 2–3 clubs use both sports actively |
| **5. v1 lock and GA** | 1 | Consolidate feedback, lock curriculum v1, market tennis to existing padel workspaces |

### 13.3 Pilot success criteria (revised)

| Metric | Target | Why |
|--------|--------|-----|
| Coach completes ≥ 1 assessment per trainee per week | 80% adherence | Curriculum is being used |
| Sport switcher used at least once per day by multi-sport coaches | 100% | Multi-sport UX is discoverable |
| Coaches do not create duplicate workspaces for sports | 0 | The single-workspace design worked |
| Multi-sport athletes get reports per sport | 100% | Reports flow scopes correctly |
| Net Promoter feedback after 4 weeks | ≥ 7/10 | Coaches would recommend |
| Migration of existing padel data: 0 data-loss incidents | 0 | Refactor was safe |

---

## 14. Roadmap & timeline (revised)

| Week | Stream A (refactor) | Stream B (curriculum) | Stream C (seed + UI) |
|------|----------|----|----|
| **0** | Refactor design lock; advisor recruitment | Advisor recruitment | — |
| **1–2** | Schema migration M1; backfill scripts; API dual-write | Advisor authors descriptors | — |
| **3** | API switches to read from new tables (M3) | Advisor refines tier thresholds | — |
| **4** | Drop old columns (M4); internal QA | Advisor Indonesian pass | UI sport switcher, sport tabs, sport pickers built |
| **5** | Multi-sport dogfood pilot in internal workspace | — | Tennis seed code (data/tennis.py), seed script tested |
| **6** | — | v1 advisor sign-off | M5 tennis seed deploy; sport picker activated; QA |
| **7** | — | — | Pilot club recruitment, onboarding |
| **8–11** | Bug fixes from pilot | — | 4-week pilot |
| **12** | — | — | v1 curriculum lock, GA tennis, marketing |

Total: **~12 weeks** from kickoff to tennis GA — up from ~10 in v0 due to the refactor stream.

---

## 15. Risks & mitigations (updated)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Multi-sport migration breaks padel data | Low | Severe | Dual-write window (3 weeks) before dropping old columns. Snapshot DB before each migration step. |
| Coaches confused by sport switcher | Medium | Medium | Single-sport workspaces hide the switcher entirely. Dogfood phase 1 catches UX gaps before pilot. |
| Workspace name "Senayan Padel Club" feels wrong once tennis added | Medium | Low | Soft nudge banner in settings; don't force rename. |
| Coach assesses a trainee in a sport they're not qualified for (bug) | Low | High | App-layer authorize check (Section 3.4). Plus disabled assess button in UI. Audit log captures any anomalies. |
| Tier-per-sport confuses parents reading PDFs | Low | Low | Sport name in PDF header. Separate PDF per sport. No combined report at MVP. |
| Advisor unavailable in Indonesia at ITF L2+ | Medium | High | Fall back to PTR / RPT advisor; or remote ITF advisor on Zoom |
| Multi-sport athletes' tier badges look inconsistent in list view | Medium | Low | Lead with the highest tier and a "+1 sport" marker. Iterate based on pilot feedback. |
| Solo coach plan customers want multi-sport at no extra cost | Medium | Medium | Solo Coach plan: 1 sport. Upsell to "Solo Coach Plus" for multi-sport (V1.5 — confirm pricing during pilot). |
| Club Starter plan upselled into Club Pro for multi-sport | Medium | Medium | Decision: Club Starter gets 1 sport, Club Pro gets unlimited. Or, all club plans get unlimited and we differentiate elsewhere. Decide before GA. |

---

## 16. Open questions for advisor (curriculum) + product (multi-sport)

### Curriculum (advisor)

1. **Slice as one skill or two?** Currently split FH and BH. Merge into single `TENNIS_TECH_SLICE`?
2. **One-handed vs two-handed backhand.** Single skill or two distinct skills?
3. **Serve split.** Flat + spin (2 skills) or flat + kick + slice (3)?
4. **Half-volley as standalone.** Skill or fold into volley descriptors?
5. **Approach as standalone.** Technical or tactical?
6. **Doubles formation depth.** One skill or split serve+1 / return / net?
7. **Junior progression speed.** Realistic timelines for 8–12yo Indonesian juniors?
8. **Tournament participation as Diamond requirement.** Hard requirement or optional?
9. **PELTI conventions.** Indonesian terminology preferences?
10. **Wheelchair tennis.** Where does this fit?
11. **Mental skills at Beginner level.** Assessable at age 8, or only Bronze+?
12. **Singles vs doubles tier blending.** Track separately or combine?

### Multi-sport architecture (product)

13. **Pricing structure for multi-sport.** Does adding tennis cost extra on Club Starter? On Solo Coach? Pricing options: (a) all sports free across all plans; (b) Solo Coach = 1 sport, Club Starter = 1 sport, Club Pro = unlimited; (c) per-sport pricing add-on. **Recommended:** option (b), confirm during pilot.
14. **Cross-sport athlete identity.** When a trainee plays both sports, do their sessions count toward one cumulative number or separately? **Recommended:** separately per sport. Cumulative blurs the picture.
15. **PDF reports.** Separate per sport (v0.1 default) or combined? Parents may prefer one PDF. **Recommended:** separate at MVP; combined "annual cross-sport review" as V1.5.
16. **Coach who switches sport mid-career.** If a coach gets ITF certified after only being padel-cert, how do they add the sport qualification? Self-service in their profile, or admin-only? **Recommended:** admin-only — keeps the qualification authoritative.
17. **Athlete moves between sports.** What happens to their padel tier if they pause padel and play tennis only? **Recommended:** tier is preserved; "last assessed" timestamp goes stale, surfaced in trainee profile as "Padel — last assessed 6 months ago, may need re-baseline".
18. **Workspace deletion cascade.** Deleting a workspace cascades through workspace_sports, athlete_sports, etc. — but archive only, never hard delete at MVP. **Recommended:** mirror existing archive pattern.

---

## 17. Out of scope (v1+)

- **Combined cross-sport PDF report.** V1.5.
- **Cross-workspace identity** (same person, multiple clubs across different cities). V2+.
- **Per-sport billing or seat counting.** V2+.
- **Wheelchair tennis as separate sport.** V2+.
- **Junior ITF Play and Stay curriculum variant.** V1.5 if pilot signal.
- **WTN auto-import from match results.** V2+.
- **Cross-sport athlete rankings or comparisons.** Never (philosophical: this is per-trainee progress, not relative competition).
- **Match Maker multi-sport events.** Possibly V2 — Match Maker (`14-match-maker.md`) is already sport-aware via workspace, may need light extension.
- **AI-suggested sport-pairing for development** ("Andi's tennis footwork would help his padel"). Cute idea, V2+.

---

## Version

- **v0** (2026-05) — initial tennis framework, single-sport workspace assumption
- **v0.1** (2026-05, current) — multi-sport workspace architecture added (Section 3, UI in Section 11)
- **v1** — after advisor refinement and pilot feedback consolidation
- **v2** — post-launch iteration

---

*Document maintained as the canonical platform default for tennis and as the architecture spec for multi-sport workspaces. Skill ontology and 1–5 scale are platform-locked across sports. Workspace tenancy model and `workspace_sports` join pattern are now canonical across all sports.*

*Related docs: `padel-skill-framework-v0.md` (sister sport framework), `12-data-model.md` (DB schema — update to reflect Section 3.3), `04-coach-assessment.md` (assessment UI — update for sport context), `06-workspace-settings.md` (add Sports panel per Section 11.3), `02-coach-today.md` (add all-sports view per Section 11.3), `CLAUDE.md` (multi-sport architecture decision — update decision #2 with the join-table approach).*
