# Match Maker — Implementation Plan

> V2 feature. Lets anyone — coach, club admin, trainee, or independent player — run match events on one or more courts using common social/league formats (Americano, Mexicano, King of the Hill) with configurable scoring, live leaderboard, and mid-event roster changes.
>
> **All roles can host.** Coaches and club admins typically run organized events for their members; trainees and players can host their own casual events. Public viewers (anyone with the link) consume standings without an account.
>
> **Free for everyone.** Monetization stays on the existing B2B coaching platform (assessment, tier, PDF report). Match Maker is the growth-loop surface that brings new users in and makes existing trainees stickier.
>
> Reuses the existing workspace/athlete model and iOS design tokens — no new auth pattern, no new billing.
>
> **Implementation note:** §16 breaks this spec into ~15 small slices (≈1–3 days each). Work one slice at a time. Don't try to ship everything in one PR.

---

## 1. Scope

### In scope (this feature)
- Event setup: pick format, scoring, courts, players/teams
- Pre-computed and dynamic pairing per format
- Live score entry per round, per court (offline-first like assessments)
- Live leaderboard (sortable by points or wins)
- Late-arrival flow: swap a player or team between rounds
- Event completion: final standings, exportable summary
- **Public standings view (no login required)** — anyone with the link can see scores
- **Player-only mode** — non-coaches can host casual events without seeing coaching UI
- **Profile claim flow** — walk-in / invited players claim their participant slot
- EN + ID localization

### Out of scope (first release)
- Multi-day tournaments with brackets / knockouts
- Auto-rating impact on tier (events are social, not assessment data)
- WhatsApp auto-broadcast (manual share via wa.me is fine)
- Payment integration / entry fees / paid tiers
- Cross-event padel rating system (V3 candidate)

### Out of scope (forever, or until requested)
- Single-elimination / classical bracket tournaments — use a dedicated tournament tool
- Live spectator commentary / video

---

## 2. Format catalog

Three families, each with variants.

| Family | Variant | Roster unit | Pairing logic | Notes |
|---|---|---|---|---|
| **Americano** | Americano | Individual | Pre-computed schedule; everyone partners everyone | Classic social format |
| | Team Americano | Fixed pair | Pre-computed schedule; each team plays every other | Couples / doubles partners |
| | Mix Americano | Individual | Americano + gender/tag-mix constraint per match | Each match has ≥1 of each tag per side |
| **Mexicano** | Mexicano | Individual | Dynamic — re-rank by points each round; top 4 → court 1, next 4 → court 2 … | Within-court: `1-3 vs 2-4` OR `1-4 vs 2-3` |
| | Team Mexicano | Fixed pair | Same dynamic re-rank applied to teams | No within-court setting (teams fixed) |
| | Mixicano | Individual | Mexicano re-rank with mixed-pair constraint within each court | Pair stays mixed even after re-rank |
| **King of the Hill** | KOTH | Individual | Court 1 = "the hill". Winners move up, losers move down | Within-court pairing rotates each round |
| | Team KOTH | Fixed pair | Same as KOTH with fixed teams | |

Format and variant are picked once at setup and locked for the event.

---

## 3. Scoring system

Two scoring modes, picked at setup.

### 3.1 Point scoring (race-to-N)
Race to a fixed point total. Both teams accumulate points until target is hit. **Player's total event points = sum of points scored across all their matches.** Default for Americano events.

Configurable targets: `16`, `21`, `24`, `32`, `untimed*`.

`untimed` = no point cap, match ends by timer (default 12 min per round). When timer expires, current point total stands.

### 3.2 Normal scoring (games)
Tennis-style game scoring within a match. Each match is one short set.

Modes:
- **First to N games** — race to N games won. `N ∈ {3, 4, 5, 6}`
- **Total of N games** — play exactly N games; score = games won per side
- **First to N with tiebreak at N-1 all** — standard padel short set

### 3.3 Mapping to leaderboard
| Scoring | Per-match player gain |
|---|---|
| Point scoring | Raw points scored in that match |
| Normal — First to N | 1 if won, 0 if lost (+ optional games-diff as tiebreak) |
| Normal — Total of N | Games won in that match |

---

## 4. Courts

- `court_count` is set at event start: integer ≥ 1.
- Max courts = ⌊ active_player_count / 4 ⌋ for individual formats, ⌊ active_team_count / 2 ⌋ for team formats.
- If player count isn't a multiple of 4 (or 2 for teams), surplus sits out as **resters**, rotated each round.
- Courts labelled `Court 1 … Court N`. In Mexicano/KOTH, Court 1 is always the highest-ranked court.

---

## 5. Leaderboard

Sortable by `points` or `wins`. Sort choice is sticky per-event but user-changeable any time.

| Sort | Primary | Tiebreaker 1 | Tiebreaker 2 |
|---|---|---|---|
| **Points** | Total points scored | Wins | Head-to-head |
| **Wins** | Match wins | Points scored | Head-to-head |

Head-to-head only applies between 2 tied players/teams. For 3+ way ties, fall through to alphabetical (deterministic) and mark them as "tied" in UI.

For Team formats, leaderboard rows are teams.

---

## 6. Pairing algorithms

### 6.1 Americano (individual)
- Pre-computed schedule based on `player_count`. Common sizes (8, 12, 16, 20…) use known balanced schedules; generate on the fly for arbitrary sizes using a round-robin generator (Berger tables adapted to 4-per-court).
- Each player should partner every other player at most ⌈total_rounds / (N-1)⌉ times.
- Total rounds = N-1 in ideal sizes; coach can shorten.

### 6.2 Team Americano
- Round-robin between teams. Each team plays every other team `floor(total_rounds / (T-1))` times where T = team count.
- Teams fixed; only opponent rotates.

### 6.3 Mix Americano
- Americano schedule + tag-based constraint. Each player has a `tag` (default `M`/`F`; coach can rename to `A`/`B` for skill mixing).
- Every match must have ≥1 of each tag per side, when possible.
- If impossible (e.g. odd gender count), relax with one-time toast: `Mix constraint relaxed`.

### 6.4 Mexicano (individual)
- **Round 1** seeded: either `initial_seed` order (coach drags) or random.
- After each round, players ranked by leaderboard (points first).
- **Round k+1**: top 4 → Court 1, next 4 → Court 2 …
- Within each court, apply `mexicano_pairing` setting:
  - `1-3 vs 2-4` (default; "champion-challenger")
  - `1-4 vs 2-3` ("top-with-bottom"; more balanced)
- Resters: rotation prefers players who haven't rested yet.

### 6.5 Team Mexicano
- Teams are the unit. Top 2 teams → Court 1, next 2 → Court 2, etc. No within-court setting.

### 6.6 Mixicano
- Mexicano re-ranking happens, but within each court the pair must stay mixed by tag.
- Algorithm picks the pairing variant that satisfies the mix constraint. Falls back to user-configured default if both work.

### 6.7 KOTH
- Round 1: seed players to courts (same as Mexicano round 1). Court 1 is "the hill".
- After each round:
  - Court 1 winners stay (or rest if rotation requires)
  - Court 1 losers drop to Court 2
  - Court 2 winners move up to Court 1
  - Court 2 losers drop to Court 3, and so on
  - Lowest-court losers stay on lowest court
- Within-court pair-up rotates each round (different partners on same court).
- **King of the Hill** = whoever holds Court 1 at end of last round.

### 6.8 Team KOTH
- Teams replace individuals. Each court has 2 teams. No within-court pair-up.

---

## 7. Late entry, substitution, withdrawal

Roster changes are allowed **between rounds**, never mid-round.

| Action | When allowed | Effect on standings |
|---|---|---|
| **Add player** | Between rounds, before final round | Joins from current round; previous-round points = 0 |
| **Replace player** (sub) | Between rounds | Replacement inherits original's points & rank; original archived from active roster |
| **Remove player** | Between rounds | Accumulated points stay on leaderboard (frozen rank); no future assignments |
| **Add team** | Between rounds (team formats) | Joins from current round |
| **Replace team member** | Between rounds (team formats) | Team identity preserved; only one slot replaced. Points unchanged |

UI: single "Manage roster" sheet from event header. Row kebab → Sub / Remove. Add button at bottom.

Pairing engine re-runs for the upcoming round on any roster change. Played rounds are immutable.

---

## 8. Event lifecycle (state machine)

```
draft  ──setup confirmed──▶  active  ──final round done──▶  completed
  │                            │
  │                            └──host cancels──▶  cancelled
  │
  └──host abandons─▶  cancelled
```

| State | Allowed actions |
|---|---|
| `draft` | Edit anything: format, scoring, courts, roster, pairing setting |
| `active` | Enter scores, edit current / past round scores, sub players, change leaderboard sort, share standings, end early |
| `completed` | View results, export PDF, share, archive |
| `cancelled` | Soft-deleted, viewable in history |

Once `active`, **format and scoring are locked**. Court count and pairing setting can still be changed (forces re-pairing for next round only).

---

## 9. User types & workspace model

Match Maker is touched by three distinct user types. Each gets a different surface, all on the same backend.

### 9.1 The four types

All four are first-class in V2. Any authenticated user can create events. The host's workspace context determines where the event lives and who sees it by default.

| Type | Origin | Workspace context when hosting | What they see |
|---|---|---|---|
| **Coach / club admin** | Existing user in `club` or `personal` workspace | Hosts in their club/personal workspace; event visible to club members | Existing coach app + Match Maker bottom-nav tab |
| **Trainee** | Existing user in `club` workspace | Hosts in their auto-created `play` workspace (separate from club). Also receives club events from their coach as participant | Trainee home + "Next event" card (when in coach-run event) + "Create event" link that drops them into play context |
| **Player** (no club) | New persona — non-coach, non-trainee | Hosts in their auto-created `play` workspace | Events + Profile only |
| **Public viewer** | Anyone with the link | None (read-only) | Read-only standings page, no login required |

### 9.2 Hosting context — coach vs play

When a trainee or coach (both have multiple memberships possible) creates an event, the app needs to know which workspace owns it:

- **Coach in club workspace** → defaults to club workspace. Event shows up in club event list. Other coaches in the club can see it.
- **Trainee in club workspace** → defaults to their personal `play` workspace. Event is private to them unless they invite others. Coach doesn't see it.
- **Pure player** → only the `play` workspace exists.

For coaches who want to host something off-club (e.g., a personal friend group), they can switch to their own play workspace via the workspace switcher. The "Create event" CTA respects the currently-active workspace.

### 9.3 New workspace type: `play`

Extends `workspaces.type`:

```sql
-- in 12-data-model.md
ALTER TYPE workspace_type ADD VALUE 'play';
-- now: 'club' | 'personal' | 'play'
```

`play` workspace characteristics:
- Auto-created on signup via Match Maker entry point
- Owner = the user themselves, no other memberships unless they invite people to events
- **Never** surfaced as "workspace" in UI — the word doesn't appear
- No settings page (or minimal: account, language only)
- Bottom nav reduced to **Events** + **Profile**
- No access to: assessments, tier, PDF report, trainees, sessions
- No `curriculum_id`, no `tier_style`, no `plan` enforcement (free forever)

### 9.4 Multi-workspace users

The existing `workspace_memberships` pattern handles users who span types:
- A trainee in Senayan Padel Club who also organizes casual events → membership in club workspace + owns a play workspace
- A coach at one club who's also a trainee at another → multiple club memberships
- Workspace switcher (existing) lets them flip between modes

Default workspace = last one used.

---

## 10. Data model

New tables, all workspace-scoped with the existing RLS pattern. Reuses `athletes` for individual players in coach-hosted events.

### 10.1 `match_events`
```sql
CREATE TYPE match_event_status AS ENUM ('draft','active','completed','cancelled');
CREATE TYPE match_event_format AS ENUM (
  'americano','team_americano','mix_americano',
  'mexicano','team_mexicano','mixicano',
  'koth','team_koth'
);
CREATE TYPE scoring_mode AS ENUM ('point','normal_first_to','normal_total','normal_first_to_tiebreak');
CREATE TYPE mexicano_pairing AS ENUM ('1_3_vs_2_4','1_4_vs_2_3');
CREATE TYPE leaderboard_sort AS ENUM ('points','wins');

CREATE TABLE match_events (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id        UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  title               VARCHAR(120) NOT NULL,
  venue               VARCHAR(200),                   -- free-text, shown on public view
  format              match_event_format NOT NULL,
  scoring_mode        scoring_mode NOT NULL,
  scoring_target      INTEGER,                        -- 16/21/24/32 or N; NULL for 'untimed'
  round_timer_seconds INTEGER,                        -- NULL unless scoring_target is NULL
  court_count         INTEGER NOT NULL CHECK (court_count >= 1),
  mexicano_pairing    mexicano_pairing,               -- only for mexicano/mixicano
  leaderboard_sort    leaderboard_sort NOT NULL DEFAULT 'points',
  total_rounds        INTEGER NOT NULL,
  current_round       INTEGER NOT NULL DEFAULT 0,
  status              match_event_status NOT NULL DEFAULT 'draft',
  is_public           BOOLEAN NOT NULL DEFAULT TRUE,  -- standings URL viewable without login
  public_slug         VARCHAR(20) UNIQUE,             -- short URL slug for /e/<slug>
  starts_at           TIMESTAMPTZ,
  completed_at        TIMESTAMPTZ,
  created_by_id       UUID NOT NULL REFERENCES users(id),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  archived_at         TIMESTAMPTZ
);

CREATE INDEX idx_match_events_workspace_active
  ON match_events (workspace_id, status, starts_at DESC)
  WHERE archived_at IS NULL;
CREATE UNIQUE INDEX idx_match_events_slug
  ON match_events (public_slug) WHERE public_slug IS NOT NULL;
```

`public_slug` powers the shareable URL `padelcoach.app/e/<slug>`. Random URL-safe ID, separate from `id` (UUID) so we don't leak internal IDs.

### 10.2 `match_event_participants`
```sql
CREATE TABLE match_event_participants (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  event_id        UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
  athlete_id      UUID REFERENCES athletes(id) ON DELETE SET NULL,   -- nullable: guest/walk-in
  claim_user_id   UUID REFERENCES users(id) ON DELETE SET NULL,      -- nullable; filled when a guest claims via magic-link
  display_name    VARCHAR(120) NOT NULL,                              -- copied so events read consistently
  team_id         UUID REFERENCES match_event_teams(id) ON DELETE SET NULL,
  tag             VARCHAR(20),                                        -- 'M'/'F' or 'A'/'B'
  initial_seed    INTEGER,                                            -- coach-set or random
  joined_round    INTEGER NOT NULL DEFAULT 1,
  withdrew_round  INTEGER,                                            -- NULL = still active
  replaced_by_id  UUID REFERENCES match_event_participants(id),       -- if subbed out
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mep_event_active
  ON match_event_participants (event_id, withdrew_round)
  WHERE withdrew_round IS NULL;
CREATE INDEX idx_mep_claim_user
  ON match_event_participants (claim_user_id) WHERE claim_user_id IS NOT NULL;
```

Key field: `claim_user_id`. A host can pre-create a participant for a walk-in with just a `display_name`. Later, that walk-in claims it via magic-link profile flow → `claim_user_id` gets filled → their event history is now linked to a real account.

### 10.3 `match_event_teams`, `match_event_rounds`, `match_event_matches`

```sql
CREATE TABLE match_event_teams (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  event_id      UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
  display_name  VARCHAR(120) NOT NULL,
  tag           VARCHAR(20),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE match_event_rounds (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  event_id      UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
  round_number  INTEGER NOT NULL,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  UNIQUE (event_id, round_number)
);

CREATE TABLE match_event_matches (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id       UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  event_id           UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
  round_id           UUID NOT NULL REFERENCES match_event_rounds(id) ON DELETE CASCADE,
  court_number       INTEGER NOT NULL,
  side_a_p1_id       UUID NOT NULL REFERENCES match_event_participants(id),
  side_a_p2_id       UUID NOT NULL REFERENCES match_event_participants(id),
  side_b_p1_id       UUID NOT NULL REFERENCES match_event_participants(id),
  side_b_p2_id       UUID NOT NULL REFERENCES match_event_participants(id),
  score_a            INTEGER,
  score_b            INTEGER,
  winner_side        CHAR(1) CHECK (winner_side IN ('A','B','D')),
  recorded_at        TIMESTAMPTZ,
  recorded_by_id     UUID REFERENCES users(id),
  client_recorded_at TIMESTAMPTZ
);

CREATE INDEX idx_mem_round_court ON match_event_matches (round_id, court_number);
```

### 10.4 RLS — public read exception

RLS scopes writes by `workspace_id = current_workspace_id()`. Standings read needs a public path that bypasses workspace context:

```sql
-- Public read: anyone can SELECT match_events / participants / rounds / matches
-- IF the parent event has is_public = TRUE and archived_at IS NULL.
-- Enforced via a separate role that the public endpoint connects as.
CREATE ROLE match_maker_public NOLOGIN;
GRANT SELECT ON match_events, match_event_participants,
                match_event_rounds, match_event_matches,
                match_event_teams
  TO match_maker_public;

CREATE POLICY match_events_public_read ON match_events
  FOR SELECT TO match_maker_public
  USING (is_public = TRUE AND archived_at IS NULL);
-- Similar policies for child tables, joining back to event.
```

API layer: public-read endpoints (`/public/e/...`) use a connection that `SET ROLE match_maker_public`. Authenticated endpoints continue with the normal workspace-scoped role.

---

## 11. API surface

```
# Authenticated (workspace-scoped)
POST   /events                         create draft event
GET    /events                         list events (filter by status)
GET    /events/:id                     event detail + current round + leaderboard
PATCH  /events/:id                     edit draft (or limited fields while active)
POST   /events/:id/start               draft → active; generate round 1
POST   /events/:id/cancel              → cancelled
POST   /events/:id/complete            → completed

POST   /events/:id/participants        add player (or team member)
PATCH  /events/:id/participants/:pid   rename, retag, replace (sub)
DELETE /events/:id/participants/:pid   withdraw (soft)

POST   /events/:id/teams               (team formats) create team
PATCH  /events/:id/teams/:tid          rename
DELETE /events/:id/teams/:tid          delete (only if no scores yet)

GET    /events/:id/rounds              all rounds with matches
POST   /events/:id/rounds/next         generate next round pairings
POST   /events/:id/rounds/:rid/regenerate   re-pair current round (only if no scores)

PATCH  /events/:id/matches/:mid/score  enter or edit a match score (offline-queueable)

GET    /events/:id/leaderboard?sort=points|wins
GET    /events/:id/export.pdf          final summary PDF

# Public (no auth required)
GET    /public/e/:slug                 standings, players, format, host name
GET    /public/e/:slug/leaderboard     sort=points|wins
POST   /public/e/:slug/claim           magic-link request to claim a participant slot

# Auth for play mode
POST   /auth/magic-link                send magic link to email
GET    /auth/magic-link/verify?token=  verify + sign in
POST   /auth/me/claim                  link authed user to participant_id (after magic-link return)
```

**Pairing remains server-authoritative.** Score entry is offline-queueable (Dexie, same pattern as assessments). Public endpoints bypass workspace context and only return events where `is_public = TRUE`.

---

## 12. Screens

Aligns with `01-design-principles.md`: iOS HIG, grouped tables, single accent, sentence case, ≥44pt taps.

### Coach POV

#### 12.1 Events list (`/events`)
Coach gets a new bottom-nav entry **Events**. Coach Today (`02-coach-today.md`) gets a "Today's events" card if any.

- Grouped sections: `Active`, `Upcoming`, `Past`
- Row: title, format meta, court count · player count, status pill
- "New event" primary CTA top-right
- Empty state per `09-empty-states.md`

#### 12.2 Create event — Step 1: Format (`/events/new`)
- Section "Format" — 3 family rows, expand to variant choice
- Section "Scoring" — segmented `Point` | `Normal`. Target picker below
- Section "Courts" — stepper
- Section (Mexicano / Mixicano only) "Pairing" — segmented `1-3 vs 2-4` | `1-4 vs 2-3`
- Section "Leaderboard sort" — segmented `Points` | `Wins`
- Primary CTA: `Next: add players`

#### 12.3 Create event — Step 2: Roster
- Picker pulled from workspace `athletes` (search). Tap to add. "Add guest" for non-trainees (creates participant with no `athlete_id`)
- For team formats: drag two players into a team card; team name auto-filled (`Andi & Budi`), editable
- For mix variants: each row has a tag toggle (`M`/`F` customizable)
- Drag-to-reorder for `initial_seed`, or "Random seed"
- Primary CTA: `Start event`

#### 12.4 Live event (`/events/:id`)
Sticky header — title, `Round 3 of 7`, segmented `Courts` | `Leaderboard` | `Roster`.

**Courts tab** (default):
- One card per court. Side A / vs / Side B / score row / status
- Bottom CTA: `Finish round → draw next`
- "Resters this round" card if any

**Leaderboard tab**: grouped table, sortable header chip, ties marked.

**Roster tab**: kebab per row → `Replace…`, `Withdraw`. `Add player` button.

#### 12.5 Event complete
- `Final standings` header
- Primary: `Export PDF`. Secondary: `Share via WhatsApp` (wa.me link to public URL)
- Top of leaderboard gets accent-tinted `Winner` or `King` pill

---

### Trainee POV

#### 12.6 Trainee home — "Next event" card
Update to `05-trainee-home.md`: add a card at top of trainee home when trainee has an active event today or upcoming this week.

```
┌─ Next event ─────────────────────┐
│ Sunday Americano                 │
│ Today, 7 PM · Senayan Padel Club │
│ You're on Court 2 · Round 3 of 7 │
│              [ View event > ]    │
└──────────────────────────────────┘
```

No new bottom-nav entry for trainees. Match Maker lives inside the existing trainee home as content, not as its own surface.

#### 12.7 Trainee event view
Tap "View event" → read-only version of §12.4:
- Courts tab: trainee's own match highlighted
- Leaderboard tab: full view, trainee's row highlighted
- Roster tab: hidden
- No score entry, no roster controls, no "draw next round" CTA

---

### Player POV (play workspace)

#### 12.8 Play landing (`/play`)
Public landing for players who want to host a casual event. Reached via:
- Marketing link
- "Host your own" CTA on a public standings page
- Direct `/play` URL

```
Run a quick Americano with friends.
Free. No setup.

[ Sign in with email ]
[ Continue with Google ]
```

Single primary action. No mention of workspace, coaching, plans, or features.

#### 12.9 Player home (after first sign-in)
Lands here after magic link or Google sign-in via `/play` entry. Backend has silently created a `play` workspace.

```
┌─ PadelCoach ─────────────────────┐
│  Events                          │
│                                  │
│  Active                          │
│  ┌─ Sunday Americano ──────────┐ │
│  │ Round 3 of 7 · 2 courts     │ │
│  └─────────────────────────────┘ │
│                                  │
│  Past (3)                        │
│                                  │
│      [ + Create event ]          │
│                                  │
│  ──────────────────────────────  │
│   📅 Events       👤 Profile    │
└──────────────────────────────────┘
```

Bottom nav: **Events**, **Profile** only. No Trainees, no Sessions, no Reports, no Settings (Settings folded into Profile as account + language).

Event create flow = same as §12.2–12.3 but without the "pick from workspace athletes" step (no athletes exist). Player adds guests by name; guests can later claim profiles.

#### 12.10 Player profile (`/profile`)
- Avatar, display name (editable)
- "Events I've played" — list (hosted + participated)
- "I'm also a coach" → link to create personal coach workspace
- "Join a club" → invite-code entry
- Account: email, language, sign out

No tier, no skill radar, no coach features. If the user becomes a trainee later (via club invite), they get a workspace switcher and the trainee home becomes available alongside.

---

### Public POV (no login)

#### 12.11 Public event view (`padelcoach.app/e/<slug>`)
Anyone with the link can see this. No login required.

```
Sunday Americano
GBK Padel · Hosted by Coach Andi
12 players · Round 3 of 7

  ┌──────────────────────────────────────┐
  │  Standings  │  Rounds  │  Players    │   ← segmented tabs
  └──────────────────────────────────────┘

Standings (sorted by points)
─────────────────────────────────────────
1.  Andi P.       24 pts   2W
2.  Budi S.       21 pts   2W
3.  Citra D.      18 pts   1W
4.  Dimas R.      16 pts   1W
…

[ Is one of these you? Claim profile ]

──────────────────────────────────
Powered by PadelCoach
```

**Standings tab** (default): aggregate standings (current §12.11).

**Rounds tab**: round-by-round breakdown. Each completed round shows all matches and scores:

```
Round 3  ──────────────────────  (completed)
Court 1   Andi & Citra   21
          Budi & Dimas   18
─────────────────────────────────
Court 2   Eka & Faisal   21
          Gilang & Hadi  15

Round 2  ──────────────────────  (completed)
Court 1   Andi & Hadi    21
          Eka & Citra    19
…

Round 4  ──────────────────────  (in play)
Court 1   Andi & Budi    14
          Citra & Dimas  11
…
```

For events still `active`, the **current round** shows live scores (read-only, refreshing). Future rounds are hidden until generated (avoids leaking pairings before they're official).

**Players tab**: full participant list with totals (display name + total points + wins + matches played).

What's shown publicly:
- Title, host name, venue (free-text), format
- Current round number, total rounds, status
- **Standings (aggregate) AND round-by-round match scores**
- Players list with summary stats (display names only — no contact info)

What's NOT shown:
- Roster controls / Add / Sub / Withdraw actions
- Host private notes
- Anyone's profile detail (email, phone, athlete record)
- Future-round pairings before the round is generated

#### 12.12 Claim profile flow
On the public standings page, tap a name (or "Claim profile"):

1. Modal: "Is one of these you?" — list of participants
2. Tap your name
3. "We'll email you a link to claim this profile"
4. Email input → magic link sent
5. User clicks magic link → lands signed-in on `/profile`
6. Background: `participant.claim_user_id` set; play workspace auto-created if new

If the email matches an existing user (e.g. trainee at another club), no new workspace is created — the participant is just linked to their existing user account.

#### 12.13 Join via invite link
Player A invites Player B via WhatsApp: "Wanna play? padelcoach.app/e/xyz/join"

1. Land on public event preview (read-only): time, venue, players-in
2. CTA: `Join this event`
3. Magic link form (email) or Google sign-in
4. Click link in inbox → land in event view as participant
5. Background: account created if new, play workspace auto-created, participant row added

---

## 13. Auth & onboarding flows

Summary of entry paths into Match Maker:

| Entry | Auth | End state |
|---|---|---|
| Coach signs in normally → opens Events tab | Existing JWT | Coach view of Match Maker (§12.1–12.5) |
| Trainee signs in normally → sees event card on home | Existing JWT | Trainee event view (§12.6–12.7) |
| Player goes to `/play` | Magic link or Google | Player home (§12.9), play workspace silent-created |
| Friend taps invite link `/e/<slug>/join` | Magic link | Player home + auto-added as participant |
| Stranger taps standings link `/e/<slug>` | None | Public standings view (§12.11) |
| Stranger claims their name on standings | Magic link | Player home + participant claim linked |

### 13.1 Magic link as primary auth for players
- Email-only, no password
- Token valid 15 min
- Single-use
- After successful verify, browser stores standard JWT (per existing pattern)

Phone OTP remains out of scope (CLAUDE.md decision #7).

### 13.2 No welcome wizard
After magic-link verify, user lands **directly on what they were trying to see** — the event, the player home, the profile. Never a "welcome, let's set up your workspace" screen.

### 13.3 Workspace creation is silent
For play-mode users, the workspace is created server-side on first sign-in. They never see the word "workspace." If they later choose "I'm also a coach", a separate `personal` workspace is created with the existing coach onboarding flow.

---

## 14. Localization

Per `11-localization-rules.md`. Format and variant names don't translate (international vocab, same rule as Bandeja / Víbora).

| String | EN | ID |
|---|---|---|
| Family names | Americano, Mexicano, King of the Hill | Americano, Mexicano, King of the Hill |
| Variant prefix | Team, Mix | Tim, Mix |
| Tabs | Courts, Leaderboard, Roster | Lapangan, Klasemen, Daftar pemain |
| Status pills | Active, Completed, Draft | Berlangsung, Selesai, Draf |
| "Round N of M" | Round {n} of {m} | Babak {n} dari {m} |
| "Resters this round" | Resters this round | Istirahat babak ini |
| "Final standings" | Final standings | Klasemen akhir |
| "Winner" / "King" | Winner / King of the Hill | Pemenang / King of the Hill |
| "Next event" card title | Next event | Event selanjutnya |
| Play landing hero | Run a quick Americano with friends. Free. No setup. | Bikin Americano cepat sama temen. Gratis. Tanpa setup. |
| "Is one of these you?" | Is one of these you? | Ada nama kamu di sini? |
| "Claim profile" | Claim profile | Klaim profil |
| "Powered by PadelCoach" | Powered by PadelCoach | Didukung oleh PadelCoach |

Public-facing copy uses **trainee-tone, not coach-tone** — encouraging, casual.

---

## 15. Edge cases & decisions

1. **Player count not a multiple of 4** → resters rotate. If less than 4 active, can't progress; calm warning.
2. **Mid-event court_count change** → re-pairs from next round only. Played rounds frozen.
3. **Tie at end of last round** → no playoff. Apply tiebreakers (H2H → alphabetical). Mark `tied` in UI; "Resolve tie" sheet lets host override.
4. **Mix Americano impossible mix** (e.g. 7M 1F) → relax constraint, one-time toast.
5. **Substituting the leader** → replacement inherits points + rank. Original frozen in event history with `withdrew_round` filled.
6. **Editing past round's score** → recomputes leaderboard. Allowed while `active`. Disallowed once `completed`.
7. **Offline score entry conflict** → last-write-wins by `client_recorded_at`. Host sees `Synced ✓` with `Reload` link if overwritten.
8. **Host leaves event mid-way** → event stays `active`. Any workspace member with `coach`+ role can take over. For play workspaces (single user), the owner is the only host.
9. **Trainee in event** → read-only view per §12.7.
10. **Player tries to claim an already-claimed name** → block, suggest contacting the host.
11. **Email collision between play user and existing trainee** → it's the same `users` row. No new account, no new play workspace if one already exists. Workspace switcher handles cross-context navigation.
12. **Host makes event `is_public = FALSE`** → standings URL returns 404. Existing participants still see it via the authenticated path.
13. **Profile claim arrives after event is completed** → still works. `claim_user_id` set; user sees the event in past events.

---

## 16. Implementation slices

> **Read this before starting to code.** Match Maker is a large feature (~8 weeks of work). Implementing it as one PR is unreviewable and unsafe. The work is broken into ~15 small slices, each ≈1–3 days of focused work, each landable as its own PR behind a feature flag. **Work one slice at a time.** Don't skip ahead.
>
> The slices below are ordered as a dependency chain — Slice 2 depends on Slice 1, etc. Some pairs can be parallelised (noted where applicable).
>
> Each slice has: **In scope**, **Out of scope** (so the agent doesn't drift), and **Acceptance** (so you know when it's done).
>
> **Feature flag:** Match Maker ships behind `FF_MATCH_MAKER`, default off. Each slice can toggle it independently in dev.

### Phase A — Foundation

#### Slice 1 — DB schema + types (~1 day)
**In scope**
- Add `'play'` to `workspace_type` enum
- All migrations from §10: `match_events`, `match_event_participants`, `match_event_teams`, `match_event_rounds`, `match_event_matches`
- All enums: `match_event_status`, `match_event_format`, `scoring_mode`, `mexicano_pairing`, `leaderboard_sort`
- RLS policies (incl. `match_maker_public` role + public-read policy)
- Pydantic models in `apps/api/app/models/match_maker.py`
- TS types regenerated for frontend

**Out of scope**
- Any API endpoints
- Any UI
- Seed data (no fixtures yet)

**Acceptance**
- `alembic upgrade head` succeeds on a clean DB
- Existing test suite still passes
- New types are importable from both sides

#### Slice 2 — Magic-link auth (~2 days)
**In scope**
- `POST /auth/magic-link` — accept email, send link via SMTP
- `GET /auth/magic-link/verify?token=` — verify, mint JWT, set httpOnly cookie
- Token storage table `auth_magic_links` (id, email, token_hash, expires_at, consumed_at)
- Rate limiting: 3 requests/min per email
- Reuse existing JWT pattern (`{user_id, active_workspace_id, role, exp}`)
- New play-workspace auto-created on first verify if email is new

**Out of scope**
- Any Match Maker UI
- Google sign-in changes (existing flow stays)
- Phone OTP (deferred per CLAUDE.md)

**Acceptance**
- Can request magic link via curl, receive email (dev: log to console)
- Can verify token, get JWT
- Verifying twice with same token fails
- New email creates user + play workspace silently

### Phase B — Coach hosts Americano end-to-end

#### Slice 3 — Events tab + draft event CRUD (~2 days)
**In scope**
- Backend: `POST /events`, `GET /events`, `GET /events/:id`, `PATCH /events/:id`, `DELETE /events/:id` (soft archive)
- All endpoints workspace-scoped via RLS
- Frontend: new bottom-nav entry "Events" (gated by `FF_MATCH_MAKER`)
- Events list page with empty state per `09-empty-states.md`
- Create event wizard, Step 1 (format / scoring / courts / pairing setting / leaderboard sort)
- Save as draft. No participants yet.

**Out of scope**
- Roster step
- Starting the event
- Pairing engine
- Public URL

**Acceptance**
- Coach can navigate to Events tab, see empty state, tap "New event", complete format step, save draft, see it in list
- Draft can be edited (returns to same wizard step)

#### Slice 4 — Roster + Americano pairing engine (~3 days)
**In scope**
- Backend: `POST /events/:id/participants`, `PATCH`, `DELETE`
- Backend: Americano pairing algorithm (deterministic; standard sizes + fallback for arbitrary)
- Backend: `POST /events/:id/start` (draft → active, generates round 1)
- Backend: `POST /events/:id/rounds/next` (generates next round)
- Frontend: Roster step (pick athletes, add guest, drag-to-reorder seed, random seed)
- Frontend: empty Live event shell (header, tabs scaffolded but not filled)

**Out of scope**
- Mexicano, KOTH (different engines)
- Team variants
- Mix tag constraint
- Score entry UI
- Leaderboard rendering

**Acceptance**
- Coach can finish wizard, see draft with participants
- Tap "Start event" → status active, round 1 visible (matches generated, no scores)
- Can tap "Finish round → draw next" (no validation yet) and round 2 generates
- Unit tests: pairing engine returns valid pairings for 4, 8, 12, 16 players

#### Slice 5 — Score entry (point scoring) + live state (~2 days)
**In scope**
- Backend: `PATCH /events/:id/matches/:mid/score` (idempotent on `client_recorded_at`)
- Frontend: Courts tab fully wired. Tap-to-edit score steppers. Status: Not started / In play / Final
- Point scoring only (16 / 21 / 24 / 32 / untimed-with-timer)
- "Finish round" CTA disabled until all courts have final
- Round timer for untimed mode (frontend only — count-up display)

**Out of scope**
- Normal scoring modes (Slice 12)
- Offline-first queue (Slice 13)
- Leaderboard tab content (Slice 6)
- Roster mid-event changes (Slice 14)

**Acceptance**
- Coach plays through a 2-round Americano with 8 players, enters all scores, finishes both rounds
- Score persists if page refreshed
- Stepper buttons respect target (won't go beyond it)

#### Slice 6 — Leaderboard + complete flow (~2 days)
**In scope**
- Backend: `GET /events/:id/leaderboard?sort=points|wins`
- Backend: `POST /events/:id/complete`, `POST /events/:id/cancel`
- Frontend: Leaderboard tab content (sortable header, rank, name, points, wins)
- Tie handling: mark "tied" rows; H2H tiebreaker; alphabetical fallback
- "Resolve tie" sheet (manual override)
- Frontend: Final standings view for completed events; "Winner" pill

**Out of scope**
- Public URL (Slice 7)
- PDF export (Slice 15)
- "Resolve tie" UI can be a simple list reorder; no fancy DnD

**Acceptance**
- After Slice 5 flow, coach sees correct standings sorted by points
- Switch to wins sort, ordering changes correctly
- Tie scenario produces tied indicator
- Tap "Complete event" → status completed, can't edit scores anymore

### Phase C — Public-by-default

#### Slice 7 — Public standings URL (~2 days)
**In scope**
- Backend: `match_maker_public` role + public endpoints
- `GET /public/e/:slug` (standings tab data)
- `GET /public/e/:slug/rounds` (round-by-round)
- `GET /public/e/:slug/players` (player list)
- `public_slug` generation on event create (random URL-safe 8 chars)
- Frontend: public page at `/e/:slug` (no auth required)
- Segmented tabs: Standings / Rounds / Players (per §12.11)
- "Powered by PadelCoach" footer
- Coach event view: "Share" button → copies `/e/:slug` to clipboard + wa.me deeplink

**Out of scope**
- Claim profile CTA (Slice 11) — show static text only
- Live refresh / polling (do it server-rendered for now; revisit if needed)

**Acceptance**
- Anyone can open the public URL in incognito and see standings + rounds + players
- Future-round pairings are hidden
- For active events, current round shows live scores
- Coach can share via "Share" → WhatsApp opens with link in message body

### Phase D — Other formats

#### Slice 8 — Team Americano (~2 days)
**In scope**
- Backend: `POST /events/:id/teams`, `PATCH`, `DELETE`
- Team-based pairing variant of Americano engine
- Frontend: roster step gets team-creation UI (drag two athletes into team card)
- Live event renders teams instead of individuals
- Leaderboard rows = teams

**Out of scope**
- Team Mexicano / Team KOTH (Slice 10)

**Acceptance**
- Coach can create Team Americano with 4 teams of 2, run a full event

#### Slice 9 — Mexicano + Mexicano pairing setting (~3 days)
**In scope**
- Backend: Mexicano pairing engine (re-rank + within-court pair-up)
- Pairing setting `1_3_vs_2_4` / `1_4_vs_2_3` plumbed through
- Frontend: pairing setting selector in create wizard
- Round generation uses leaderboard state, not pre-computed schedule

**Out of scope**
- Team Mexicano + Mixicano (Slice 10)
- KOTH (Slice 10)

**Acceptance**
- Coach can run a Mexicano with 12 players, 3 courts; after round 1, top 4 go to court 1
- Both pairing settings produce different matchups verifiable in tests

#### Slice 10 — KOTH + Team variants of Mexicano/KOTH (~3 days)
**In scope**
- KOTH movement rules (winners up, losers down)
- Team Mexicano, Team KOTH variants
- Frontend: format picker shows all variants

**Out of scope**
- Mix variants (Slice 11)

**Acceptance**
- Coach can run KOTH with 8 players, 2 courts; court 1 winners stay or rotate per rules
- Team KOTH end-to-end works

#### Slice 11 — Mix Americano + Mixicano (~2 days)
**In scope**
- Tag field on participants (`M`/`F` or custom `A`/`B`)
- Tag UI in roster step (toggle per row, custom tag rename in header)
- Mix constraint in Americano engine
- Mix constraint within-court in Mixicano engine
- Constraint relaxation toast

**Out of scope**
- More than 2 tag groups (V2.5 question per §18)

**Acceptance**
- Coach can run Mix Americano with 8 players (4M 4F); every match has at least 1 of each tag per side
- With 7M 1F, constraint relaxes with toast

#### Slice 12 — Normal scoring modes (~2 days)
**In scope**
- `normal_first_to`, `normal_total`, `normal_first_to_tiebreak`
- Score entry UI for games-style (number stepper per game, or game-counter)
- Leaderboard mapping per §3.3
- Wizard's scoring section gets second segmented option

**Out of scope**
- New formats

**Acceptance**
- Coach can run an Americano with "First to 4 games" scoring; leaderboard reflects W/L correctly
- "Total of 4 games" allows draws

### Phase E — Roster ops + offline

#### Slice 13 — Offline-first score entry (~2 days)
**In scope**
- Dexie queue for score mutations (mirror assessment pattern)
- Sync status pills: `Saved offline ⏳` / `Synced ✓` / `Sync failed ⚠️`
- Last-write-wins by `client_recorded_at`
- Reload prompt if remote conflict detected

**Out of scope**
- Offline event creation (online-only)
- Offline next-round generation (server-authoritative)

**Acceptance**
- Coach can disable network, enter scores, re-enable network → scores sync
- Two devices entering different scores resolve to last-write-wins

#### Slice 14 — Roster management mid-event (~2 days)
**In scope**
- Roster tab content (active + withdrawn participants)
- Add player between rounds
- Replace (sub) flow with point inheritance
- Withdraw flow
- Pairing engine re-runs on roster change for next round

**Out of scope**
- Mid-round changes (forbidden)

**Acceptance**
- Coach can sub a player between rounds; replacement inherits points
- Coach can add new player at round 3; they have 0 prior-round points
- Played rounds unchanged

### Phase F — Player & trainee surfaces

#### Slice 15 — Play workspace + player home (~3 days)
**In scope**
- Auto-create play workspace on magic-link signup (already in Slice 2; refine here)
- `/play` landing page
- Player home (Events + Profile bottom nav)
- Player profile screen (display name, events list, sign out)
- Workspace context resolution: events created in current active workspace

**Out of scope**
- Profile claim from public standings (Slice 16)
- Join via invite link (Slice 17)
- Trainee-as-host (Slice 18)

**Acceptance**
- Brand new user goes to `/play`, gets magic link, lands on empty player home
- Can create event end-to-end (Americano with 4 guests by name)
- Bottom nav shows only Events + Profile

#### Slice 16 — Profile claim from public standings (~2 days)
**In scope**
- Public standings: "Is one of these you?" CTA
- Claim modal with participant list
- `POST /public/e/:slug/claim` — sends magic link to email, stores intended `participant_id`
- After magic-link verify, link `participant.claim_user_id`
- If email matches existing user, no new workspace; else new play workspace

**Out of scope**
- Claim approval flow (claim is FCFS per §18 Q5)

**Acceptance**
- Stranger views public standings, claims a name, gets email, clicks link, lands in player home with that event in their list
- Collision: trying to claim already-claimed name returns clear error

#### Slice 17 — Join via invite link (~2 days)
**In scope**
- `/e/:slug/join` route (public preview + Join CTA)
- Host can mark event as "open to join" (`accepts_self_join` flag on `match_events`)
- Magic link → auto-add as participant
- Capacity check: refuse if event is full

**Out of scope**
- Real-time RSVP list

**Acceptance**
- Player creates event with self-join enabled, shares link
- Friend taps link, joins via magic link, appears as participant

#### Slice 18 — Trainee integration (~2 days)
**In scope**
- "Next event" card on trainee home (when trainee is participant in active/upcoming event)
- Trainee read-only event view (Courts + Leaderboard tabs, no Roster)
- Trainee's own match highlighted on Courts tab
- "Create event" CTA on trainee home → opens play workspace context
- Workspace switcher exposed if trainee has both club + play memberships

**Out of scope**
- Trainee creating events in club workspace (only in their play workspace)

**Acceptance**
- Trainee in club sees Next event card when coach adds them as participant
- Trainee can tap "Create event" on home, lands in play context, creates personal event
- Workspace switcher correctly toggles between club view and play view

### Phase G — Polish

#### Slice 19 — Coach Today + WhatsApp + i18n + PDF (~3 days)
**In scope**
- "Today's events" card on Coach Today (`02-coach-today.md`)
- WhatsApp share copy templates (event invite, post-event standings)
- ID localization full pass for all Match Maker strings (per §14 table)
- PDF export of final standings (reuse `08-pdf-report.md` infrastructure; new template)

**Out of scope**
- Custom PDF branding (V2.5)

**Acceptance**
- Coach Today shows today's active events
- Share buttons produce wa.me deeplinks with sensible default text
- App is fully usable in ID locale
- "Export PDF" produces a clean A4 standings doc

#### Slice 20 — Hardening + E2E + docs (~2 days)
**In scope**
- Playwright E2E: full Americano coach flow + player claim flow
- Vitest unit tests for all pairing engines (cover edge cases: resters, ties, constraint relaxation)
- Sentry breadcrumbs around event lifecycle transitions
- Doc updates: this file, `02-coach-today.md`, `05-trainee-home.md`, `07-invite-and-onboarding.md`
- Remove `FF_MATCH_MAKER` flag (feature is live)

**Out of scope**
- Load testing (V2.5 if needed)

**Acceptance**
- All E2E green in CI
- Coverage on pairing engines ≥ 85%
- Flag removed, feature on for all workspaces by default

---

### Slice dependency graph

```
Slice 1 (schema) ─┬─→ Slice 3 (Events CRUD) ─→ Slice 4 (roster + pairing) ─→ Slice 5 (score entry) ─→ Slice 6 (leaderboard)
                  │                                                                                       │
Slice 2 (auth)  ──┘                                                                                       ▼
                                                                                                     Slice 7 (public URL)
                                                                                                          │
                  ┌───────────────────────────────────────────────────────────────────────────────────────┤
                  ▼                                                                                       ▼
              Slice 8 (Team Am.)      Slice 9 (Mexicano)     Slice 10 (KOTH+team)   Slice 11 (Mix)   Slice 12 (Normal scoring)
                  │                                                                                       │
                  └──────────────────── these 5 can be parallelised across two devs ──────────────────────┘
                                                                                                          │
                                                                                                          ▼
                                                                                       Slice 13 (offline) + Slice 14 (roster ops)
                                                                                                          │
                                                                                                          ▼
                                                                                       Slice 15 (play ws) → 16 (claim) → 17 (join) → 18 (trainee)
                                                                                                          │
                                                                                                          ▼
                                                                                              Slice 19 (polish) → Slice 20 (hardening)
```

**Total: 20 slices, ≈45 dev-days = ~9 weeks solo.** Parallelisable to ~6 weeks with 2 engineers.

### When implementing one slice

1. Read this whole spec once. Skim §2–§15 for context.
2. Re-read the target slice's "In scope", "Out of scope", "Acceptance".
3. **Stop at slice boundary.** Don't pull in next slice's work even if it seems related — the next slice is sized to ship by itself for a reason.
4. Branch name: `feat/match-maker-slice-NN-short-name`
5. PR description must include the slice number and its acceptance criteria as a checklist.
6. Update this doc in the same PR if the slice teaches you something the spec got wrong.

---

## 17. Success metrics

To know if Match Maker is working, track from day-1 of public release:

| Metric | What it tells you | Target after 3 months |
|---|---|---|
| Events created / week | Adoption | 50+ across pilot clubs |
| Avg participants per event | Engagement | 10+ |
| Public standings URL click-through | Growth loop activation | 60% of participants click |
| Profile claim rate | Player acquisition | 30% of public viewers claim |
| Player-hosted events / coach-hosted events | B2C signal | Watch this ratio; if >30%, B2C is worth investing in |
| Trainee → event participation rate | Trainee retention impact | Trainees in event clubs retain 20% better |

If player-hosted events stay below 10% of total after 6 months, B2C didn't catch — that's fine, Match Maker is still pulling its weight as a B2B retention tool. If above 30%, consider freemium B2C gating in V3.

---

## 18. Open questions for advisor / pilot

1. Should `Mix Americano` support more than 2 tag groups (e.g. 3 skill tiers)? (Default: 2 in V2; arbitrary in V2.5.)
2. KOTH "stay on Court 1 if you win" vs always rotate — configurable, or pick one? (Default: stay. Configurable behind Advanced toggle later.)
3. Should we sub-brand the player surface (e.g. "PadelCoach Match") to separate from coach product? (Default: no rebrand at V2. Revisit if player adoption is strong.)
4. Profile claim collision policy: first-come-first-served, or require host approval? (Default: FCFS, with host able to revoke from roster panel.)
5. Should a trainee be able to invite their coach as a participant in a play-workspace event? (Default: yes — coach gets a player-side participant invite, separate from coaching context.)

---

## Related

- `01-design-principles.md` — visual & interaction language
- `02-coach-today.md` — needs "Today's events" card section
- `05-trainee-home.md` — needs "Next event" card section
- `07-invite-and-onboarding.md` — extend with play-mode magic-link path
- `09-empty-states.md`, `10-error-offline-states.md` — required state patterns
- `11-localization-rules.md` — EN/ID rules; format names don't translate
- `12-data-model.md` — base schema this extends; add `'play'` to workspace type
- `CLAUDE.md` — MVP scope (this is V2; ship after MVP stabilises)
