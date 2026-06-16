# Data Model

> Full Postgres schema, RLS policies, indexes, and key queries. Multi-sport-ready from day 1 (padel MVP, tennis V2). Read this before touching the database.

## Core principles

1. **Workspace = tenant.** Every tenant-scoped table has `workspace_id` + RLS policy filtering by it.
2. **Sport is a row, not hardcoded.** `sports` table; `skills`, `tiers`, `workspaces` reference it.
3. **Platform defaults vs workspace overrides.** Skills, tiers, descriptors have nullable `workspace_id` — `NULL` = platform default, non-null = workspace customization.
4. **UUIDs everywhere.** UUIDv7 for time-sortable IDs (fall back to UUIDv4 if extension unavailable).
5. **Soft delete** via `archived_at`. Hard delete only via Danger Zone with explicit confirmation.
6. **Snake_case in DB.** ORM maps to camelCase at API boundary.
7. **All timestamps `TIMESTAMPTZ` in UTC.** Display layer formats per locale.

---

## Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_uuidv7";       -- uuid_generate_v7() — time-sortable
CREATE EXTENSION IF NOT EXISTS "citext";          -- case-insensitive text (emails)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- fuzzy search on names
```

If `pg_uuidv7` is unavailable in your hosted Postgres (Neon supports it; some don't), substitute `gen_random_uuid()` everywhere. UUIDv4 works fine, just less optimal for clustered indexes.

---

## Sports (platform-level, locked)

Foundation of multi-sport extensibility.

```sql
CREATE TABLE sports (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  code        VARCHAR(20) UNIQUE NOT NULL,         -- 'padel', 'tennis'
  name_en     VARCHAR(50) NOT NULL,
  name_id     VARCHAR(50) NOT NULL,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO sports (code, name_en, name_id, is_active, display_order) VALUES
  ('padel',  'Padel',  'Padel',  TRUE,  1),
  ('tennis', 'Tennis', 'Tenis',  FALSE, 2);  -- inactive at MVP, ready for V2
```

No RLS — public read. Admin-only write.

---

## Users (cross-workspace identity)

Global identity. One user can belong to many workspaces (workspace switcher in app).

```sql
CREATE TABLE users (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  email               CITEXT UNIQUE,                              -- nullable: junior may not have email
  google_sub          VARCHAR(255) UNIQUE,                        -- Google OAuth sub claim
  display_name        VARCHAR(120) NOT NULL,
  avatar_url          TEXT,
  preferred_locale    VARCHAR(5) NOT NULL DEFAULT 'id',           -- 'en' | 'id'
  is_minor            BOOLEAN NOT NULL DEFAULT FALSE,
  date_of_birth       DATE,
  primary_guardian_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at        TIMESTAMPTZ,
  CONSTRAINT users_has_identity CHECK (email IS NOT NULL OR google_sub IS NOT NULL)
);

CREATE INDEX idx_users_email      ON users (email)          WHERE email IS NOT NULL;
CREATE INDEX idx_users_google_sub ON users (google_sub)     WHERE google_sub IS NOT NULL;
CREATE INDEX idx_users_guardian   ON users (primary_guardian_id) WHERE primary_guardian_id IS NOT NULL;
```

**Notes:**
- `is_minor` set TRUE if `date_of_birth < NOW() - INTERVAL '18 years'`. Drives parent-required flows.
- `primary_guardian_id` for junior trainees — parent's user record. Multiple guardians possible via `user_guardians` table below.
- Users authenticate via either email magic link or Google (one of the two identity columns must be set).
- No RLS on users (cross-workspace), but app layer enforces visibility (you can only see users you share a workspace with).

```sql
-- Multi-guardian support (divorced parents, etc.)
CREATE TABLE user_guardians (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,    -- the minor
  guardian_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,    -- the parent/guardian
  relationship VARCHAR(50),                                            -- 'mother', 'father', 'guardian'
  is_primary  BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, guardian_id)
);

CREATE INDEX idx_user_guardians_user     ON user_guardians (user_id);
CREATE INDEX idx_user_guardians_guardian ON user_guardians (guardian_id);
```

---

## Workspaces (the tenant)

```sql
CREATE TABLE workspaces (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  sport_id        UUID NOT NULL REFERENCES sports(id),
  type            VARCHAR(20) NOT NULL CHECK (type IN ('club', 'personal')),
  name            VARCHAR(120) NOT NULL,
  slug            VARCHAR(60) UNIQUE,                           -- optional, for share URLs
  city            VARCHAR(100),                                 -- personal type only (club has address elsewhere)
  brand_color     VARCHAR(7),                                   -- hex, e.g. '#378ADD'; NULL = default
  logo_url        TEXT,
  tier_style      VARCHAR(20) NOT NULL DEFAULT 'game'           -- 'game' | 'skill' | 'custom'
                  CHECK (tier_style IN ('game', 'skill', 'custom')),
  primary_locale  VARCHAR(5) NOT NULL DEFAULT 'id',             -- 'en' | 'id'
  curriculum_id   UUID,                                         -- FK to curricula (added below); platform default if NULL
  plan            VARCHAR(20) NOT NULL DEFAULT 'free_trial'     -- 'free_trial' | 'solo_coach' | 'club_starter' | 'club_pro'
                  CHECK (plan IN ('free_trial', 'solo_coach', 'club_starter', 'club_pro')),
  trial_ends_at   TIMESTAMPTZ,
  active_trainee_quota INTEGER NOT NULL DEFAULT 20,             -- enforced at API layer
  allow_coach_overrides BOOLEAN NOT NULL DEFAULT FALSE,         -- whether coaches can customize per-trainee curriculum
  owner_user_id   UUID NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  archived_at     TIMESTAMPTZ
);

CREATE INDEX idx_workspaces_owner      ON workspaces (owner_user_id);
CREATE INDEX idx_workspaces_sport_type ON workspaces (sport_id, type);
CREATE INDEX idx_workspaces_active     ON workspaces (id) WHERE archived_at IS NULL;
```

**Notes:**
- `type = 'personal'` workspaces have only one coach (the owner). Members table still works.
- `tier_style` controls user-facing tier labels (Game = "Bronze/Silver/Gold", Skill = "Beginner/Intermediate/Advanced", Custom = workspace-defined).
- `plan` enforced at API layer. `active_trainee_quota` set on plan change.
- Trial period: 30 days from signup, no payment required.

---

## Workspace memberships (user ↔ workspace ↔ role)

```sql
CREATE TYPE workspace_role AS ENUM (
  'club_admin',     -- club workspace only; full settings access
  'head_coach',     -- club workspace only; can manage other coaches
  'coach',          -- assesses trainees
  'trainee',        -- a player being coached
  'parent'          -- guardian of a junior trainee (workspace context — different from user_guardians)
);

CREATE TYPE membership_status AS ENUM ('active', 'invited', 'archived');

CREATE TABLE workspace_memberships (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role          workspace_role NOT NULL,
  status        membership_status NOT NULL DEFAULT 'invited',
  invited_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  joined_at     TIMESTAMPTZ,
  archived_at   TIMESTAMPTZ,
  invited_by_id UUID REFERENCES users(id),
  UNIQUE (workspace_id, user_id, role)
);

CREATE INDEX idx_memberships_workspace_user ON workspace_memberships (workspace_id, user_id);
CREATE INDEX idx_memberships_user           ON workspace_memberships (user_id) WHERE status = 'active';
CREATE INDEX idx_memberships_workspace_role ON workspace_memberships (workspace_id, role) WHERE status = 'active';
```

**Notes:**
- A user can have multiple roles in same workspace (e.g., `club_admin` + `coach`). UNIQUE constraint allows this.
- `parent` role is workspace-specific (parent of a trainee in this club). `user_guardians` is global parent-child link. Both exist; they're related but distinct concerns.
- `status = 'invited'` until user accepts invite. App filters most queries on `status = 'active'`.

---

## Athletes (the trainee record)

```sql
CREATE TABLE athletes (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id      UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id           UUID REFERENCES users(id) ON DELETE SET NULL,    -- nullable: trainee may not have claimed account yet
  display_name      VARCHAR(120) NOT NULL,                            -- editable by coach independent of user.display_name
  date_of_birth     DATE,
  is_minor          BOOLEAN NOT NULL DEFAULT FALSE,                   -- denormalized from user/dob for fast filtering
  joined_at         DATE NOT NULL DEFAULT CURRENT_DATE,
  notes             TEXT,                                             -- coach's private notes
  archived_at       TIMESTAMPTZ,
  created_by_id     UUID NOT NULL REFERENCES users(id),               -- the coach who added them
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_athletes_workspace_active ON athletes (workspace_id) WHERE archived_at IS NULL;
CREATE INDEX idx_athletes_user             ON athletes (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_athletes_workspace_name   ON athletes USING GIN (workspace_id, display_name gin_trgm_ops);
```

**Notes:**
- `user_id` nullable — coach can add a trainee record before invite is claimed.
- `is_minor` flag drives parent-required flows.
- A single user can be an athlete in multiple workspaces (different `athletes` rows, same `user_id`).

---

## Curricula

A workspace uses one curriculum. Platform defaults exist; clubs can clone and override at Club Pro tier.

```sql
CREATE TABLE curricula (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  sport_id        UUID NOT NULL REFERENCES sports(id),
  workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,    -- NULL = platform default
  code            VARCHAR(50) NOT NULL,                                 -- 'padel-default-appa', 'padel-tennis-default'
  name_en         VARCHAR(120) NOT NULL,
  name_id         VARCHAR(120) NOT NULL,
  description_en  TEXT,
  description_id  TEXT,
  parent_id       UUID REFERENCES curricula(id),                        -- if cloned from another curriculum
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (sport_id, workspace_id, code)
);

CREATE INDEX idx_curricula_sport_default ON curricula (sport_id) WHERE workspace_id IS NULL;
CREATE INDEX idx_curricula_workspace     ON curricula (workspace_id) WHERE workspace_id IS NOT NULL;
```

Workspace's `workspaces.curriculum_id` references this. NULL = use platform default for the sport.

---

## Skills (platform-locked taxonomy)

```sql
CREATE TYPE skill_category AS ENUM ('technical', 'tactical', 'physical', 'mental');

CREATE TABLE skills (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  sport_id            UUID NOT NULL REFERENCES sports(id),
  curriculum_id       UUID REFERENCES curricula(id) ON DELETE CASCADE,    -- NULL = belongs to all curricula in sport
  workspace_id        UUID REFERENCES workspaces(id) ON DELETE CASCADE,   -- NULL = platform skill, non-null = workspace custom
  code                VARCHAR(80) NOT NULL,                                -- 'PADEL_TECH_BANDEJA'
  category            skill_category NOT NULL,
  name_en             VARCHAR(120) NOT NULL,
  name_id             VARCHAR(120) NOT NULL,                               -- often same as EN for skill names (Bandeja stays)
  description_en      TEXT,
  description_id      TEXT,
  display_order       INTEGER NOT NULL DEFAULT 0,
  is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,                       -- workspace can disable platform skills
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (sport_id, workspace_id, code)
);

CREATE INDEX idx_skills_sport_platform ON skills (sport_id, category, display_order) WHERE workspace_id IS NULL AND is_enabled = TRUE;
CREATE INDEX idx_skills_workspace      ON skills (workspace_id) WHERE workspace_id IS NOT NULL;
```

**Notes:**
- Platform skills: `workspace_id IS NULL`, immutable from app layer.
- Workspace overrides: `workspace_id = X`, `is_enabled = FALSE` means skill hidden in that workspace.
- Custom skills (V1.5+): `workspace_id = X`, new code/category, defined by the club.
- Skill `code` must be unique within `(sport_id, workspace_id)`. Padel and tennis can have same codes.

Seed all 27 padel skills with `sport_id = padel`, `workspace_id = NULL`. See `padel-skill-framework-v0.md` for canonical list.

---

## Skill level descriptors (135 per sport: 27 skills × 5 levels)

```sql
CREATE TABLE skill_level_descriptors (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  skill_id      UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  workspace_id  UUID REFERENCES workspaces(id) ON DELETE CASCADE,    -- NULL = platform default
  level         SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 5),
  description_en TEXT NOT NULL,
  description_id TEXT NOT NULL,
  UNIQUE (skill_id, workspace_id, level)
);

CREATE INDEX idx_descriptors_skill ON skill_level_descriptors (skill_id, level) WHERE workspace_id IS NULL;
CREATE INDEX idx_descriptors_workspace ON skill_level_descriptors (workspace_id, skill_id, level) WHERE workspace_id IS NOT NULL;
```

Resolution at query time:
```sql
-- Get descriptor for skill, preferring workspace override over platform default
SELECT description_en, description_id
FROM skill_level_descriptors
WHERE skill_id = $1
  AND level = $2
  AND (workspace_id = $3 OR workspace_id IS NULL)
ORDER BY workspace_id NULLS LAST
LIMIT 1;
```

---

## Tiers (curriculum levels — Beginner → Diamond)

```sql
CREATE TABLE tiers (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  sport_id        UUID NOT NULL REFERENCES sports(id),
  curriculum_id   UUID REFERENCES curricula(id) ON DELETE CASCADE,
  workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,    -- NULL = platform default
  code            VARCHAR(20) NOT NULL,                                 -- 'BEGINNER', 'BRONZE', 'SILVER'
  display_order   INTEGER NOT NULL,
  -- Game style labels
  name_game_en    VARCHAR(50) NOT NULL,                                 -- 'Bronze'
  name_game_id    VARCHAR(50) NOT NULL,                                 -- 'Perunggu'
  -- Skill style labels
  name_skill_en   VARCHAR(50) NOT NULL,                                 -- 'Intermediate'
  name_skill_id   VARCHAR(50) NOT NULL,                                 -- 'Menengah'
  -- Custom labels (optional, set by workspace)
  name_custom_en  VARCHAR(50),
  name_custom_id  VARCHAR(50),
  color_hex       VARCHAR(7),                                           -- visual badge color
  icon_name       VARCHAR(50),                                          -- lucide icon name
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (curriculum_id, workspace_id, code)
);

CREATE INDEX idx_tiers_sport ON tiers (sport_id, display_order);
CREATE INDEX idx_tiers_curriculum ON tiers (curriculum_id, display_order) WHERE curriculum_id IS NOT NULL;
```

Seed for padel default curriculum: 7 tiers (Beginner, Lower Bronze, Bronze, Silver, Gold, Platinum, Diamond) with both Game and Skill labels.

---

## Tier requirements (skill thresholds for tier graduation)

```sql
CREATE TABLE tier_requirements (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  tier_id     UUID NOT NULL REFERENCES tiers(id) ON DELETE CASCADE,
  skill_id    UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  min_level   SMALLINT NOT NULL CHECK (min_level BETWEEN 1 AND 5),
  UNIQUE (tier_id, skill_id)
);

CREATE INDEX idx_tier_requirements_tier ON tier_requirements (tier_id);
```

Seed per `padel-skill-framework-v0.md` § 6.

---

## Sessions (a coaching session)

```sql
CREATE TYPE session_focus AS ENUM (
  'drilling', 'match_play', 'conditioning', 'mental_training', 'technique_focus', 'general'
);

CREATE TABLE sessions (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  athlete_id      UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  coach_id        UUID NOT NULL REFERENCES users(id),
  scheduled_at    TIMESTAMPTZ NOT NULL,
  duration_min    INTEGER NOT NULL DEFAULT 60,
  focus           session_focus,
  summary         TEXT,                                             -- coach narrative, customer-facing
  internal_notes  TEXT,                                             -- coach private notes
  status          VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                  CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show')),
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_workspace_athlete   ON sessions (workspace_id, athlete_id, scheduled_at DESC);
CREATE INDEX idx_sessions_workspace_coach     ON sessions (workspace_id, coach_id, scheduled_at DESC);
CREATE INDEX idx_sessions_workspace_today     ON sessions (workspace_id, scheduled_at) WHERE status = 'scheduled';
```

---

## Assessments (the actual skill scores)

```sql
CREATE TABLE assessments (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id        UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  athlete_id          UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  coach_id            UUID NOT NULL REFERENCES users(id),
  session_id          UUID REFERENCES sessions(id) ON DELETE SET NULL,
  skill_id            UUID NOT NULL REFERENCES skills(id),
  level               SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 5),
  note                TEXT,
  recorded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  client_recorded_at  TIMESTAMPTZ,                                  -- when coach actually scored (offline → server may sync later)
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assessments_athlete_skill_recent
  ON assessments (workspace_id, athlete_id, skill_id, recorded_at DESC);
CREATE INDEX idx_assessments_session
  ON assessments (session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_assessments_athlete_recent
  ON assessments (workspace_id, athlete_id, recorded_at DESC);
```

**Notes:**
- Assessments are **append-only**. To "change" a score, insert a new row. Latest row per (athlete, skill) is current.
- `client_recorded_at` for offline-first: when the coach actually entered it on their device. `recorded_at` is server-side time (default NOW()).
- Tier is derived from latest assessment per skill (server-side calculation).

---

## Reports (PDF monthly reports)

```sql
CREATE TABLE reports (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id      UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  athlete_id        UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  coach_id          UUID NOT NULL REFERENCES users(id),
  period_start      DATE NOT NULL,
  period_end        DATE NOT NULL,
  generated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  pdf_url           TEXT,                                           -- R2 URL
  pdf_size_bytes    INTEGER,
  generation_type   VARCHAR(20) NOT NULL DEFAULT 'auto'
                    CHECK (generation_type IN ('auto', 'manual')),
  generated_by_id   UUID REFERENCES users(id),                       -- NULL for auto
  shared_at         TIMESTAMPTZ,                                     -- when first viewed externally
  view_count        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_reports_workspace_athlete ON reports (workspace_id, athlete_id, period_end DESC);
```

---

## Invites (pending workspace memberships)

```sql
CREATE TABLE invites (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  email           CITEXT,                                           -- nullable: invite by phone-only flow
  phone_e164      VARCHAR(20),
  role            workspace_role NOT NULL,
  athlete_id      UUID REFERENCES athletes(id) ON DELETE CASCADE,   -- if inviting trainee, link to existing athlete record
  invite_code     VARCHAR(40) UNIQUE NOT NULL,                       -- random URL-safe, used in deep link
  invited_by_id   UUID NOT NULL REFERENCES users(id),
  invited_user_id UUID REFERENCES users(id),                         -- who specifically (if known); else any holder of code can claim
  expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
  claimed_at      TIMESTAMPTZ,
  claimed_by_id   UUID REFERENCES users(id),
  revoked_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invites_workspace      ON invites (workspace_id) WHERE claimed_at IS NULL AND revoked_at IS NULL;
CREATE INDEX idx_invites_email_pending  ON invites (email) WHERE claimed_at IS NULL AND revoked_at IS NULL AND email IS NOT NULL;
```

---

## Subscriptions (billing — manual at MVP, prep for V1.5)

```sql
CREATE TABLE subscriptions (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  plan            VARCHAR(20) NOT NULL,                           -- mirrors workspaces.plan
  status          VARCHAR(20) NOT NULL                             -- 'trial' | 'active' | 'past_due' | 'cancelled'
                  CHECK (status IN ('trial', 'active', 'past_due', 'cancelled')),
  current_period_start TIMESTAMPTZ,
  current_period_end   TIMESTAMPTZ,
  cancel_at       TIMESTAMPTZ,
  external_provider VARCHAR(50),                                  -- 'stripe' | 'xendit' | NULL (manual)
  external_id     VARCHAR(255),                                   -- provider's subscription ID
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON subscriptions (workspace_id);
```

At MVP: manual invoicing. Insert row with `external_provider = NULL`, status updated by admin.

---

## Audit log (security & debugging)

```sql
CREATE TABLE audit_log (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
  workspace_id  UUID REFERENCES workspaces(id) ON DELETE SET NULL,
  user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
  action        VARCHAR(80) NOT NULL,                             -- 'workspace.created', 'invite.claimed', 'assessment.created'
  entity_type   VARCHAR(50),
  entity_id     UUID,
  metadata      JSONB,
  ip_address    INET,
  user_agent    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_workspace ON audit_log (workspace_id, created_at DESC);
CREATE INDEX idx_audit_user      ON audit_log (user_id, created_at DESC);
CREATE INDEX idx_audit_entity    ON audit_log (entity_type, entity_id);
```

---

## Row Level Security (RLS)

Enable RLS on **every** tenant-scoped table. The pattern: API middleware sets `app.current_workspace_id` per request from JWT. RLS policies filter rows by this setting.

### Setup helper

```sql
-- Helper to get current workspace from session config
CREATE OR REPLACE FUNCTION current_workspace_id() RETURNS UUID AS $$
  SELECT NULLIF(current_setting('app.current_workspace_id', TRUE), '')::UUID
$$ LANGUAGE SQL STABLE;
```

### Per-table policies

```sql
-- Workspaces: visible if user is a member (handled at app layer; RLS enforces direct queries)
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY workspace_self_access ON workspaces
  USING (id = current_workspace_id() OR current_workspace_id() IS NULL);

-- Memberships: only see your workspace's memberships
ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY;
CREATE POLICY membership_workspace_access ON workspace_memberships
  USING (workspace_id = current_workspace_id());

-- Athletes
ALTER TABLE athletes ENABLE ROW LEVEL SECURITY;
CREATE POLICY athlete_workspace_access ON athletes
  USING (workspace_id = current_workspace_id());

-- Sessions
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY session_workspace_access ON sessions
  USING (workspace_id = current_workspace_id());

-- Assessments
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
CREATE POLICY assessment_workspace_access ON assessments
  USING (workspace_id = current_workspace_id());

-- Reports
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY report_workspace_access ON reports
  USING (workspace_id = current_workspace_id());

-- Invites
ALTER TABLE invites ENABLE ROW LEVEL SECURITY;
CREATE POLICY invite_workspace_access ON invites
  USING (workspace_id = current_workspace_id());

-- Subscriptions
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY subscription_workspace_access ON subscriptions
  USING (workspace_id = current_workspace_id());

-- Skills, descriptors, tiers, tier_requirements: scoped to platform OR current workspace
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
CREATE POLICY skills_platform_or_workspace ON skills
  USING (workspace_id IS NULL OR workspace_id = current_workspace_id());

ALTER TABLE skill_level_descriptors ENABLE ROW LEVEL SECURITY;
CREATE POLICY descriptors_platform_or_workspace ON skill_level_descriptors
  USING (workspace_id IS NULL OR workspace_id = current_workspace_id());

ALTER TABLE tiers ENABLE ROW LEVEL SECURITY;
CREATE POLICY tiers_platform_or_workspace ON tiers
  USING (workspace_id IS NULL OR workspace_id = current_workspace_id());

ALTER TABLE curricula ENABLE ROW LEVEL SECURITY;
CREATE POLICY curricula_platform_or_workspace ON curricula
  USING (workspace_id IS NULL OR workspace_id = current_workspace_id());

-- Audit log: only see your workspace's events
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_workspace_access ON audit_log
  USING (workspace_id = current_workspace_id() OR workspace_id IS NULL);

-- Sports: public read (no RLS)
-- Users: cross-workspace (no RLS); app layer enforces visibility
-- user_guardians: cross-workspace (no RLS); app layer enforces
```

### App layer pattern (FastAPI middleware)

```python
@app.middleware("http")
async def set_workspace_context(request: Request, call_next):
    token = decode_jwt(request)
    if token and token.active_workspace_id:
        async with get_db() as conn:
            await conn.execute(
                text("SET LOCAL app.current_workspace_id = :wid"),
                {"wid": str(token.active_workspace_id)}
            )
    return await call_next(request)
```

This means: every DB query inside the request context auto-filters by workspace. Even if a developer writes `SELECT * FROM athletes` without a WHERE clause, RLS enforces tenant isolation.

### Bypass for admin operations

For platform-level operations (seeding, migrations, system jobs), use a SUPERUSER connection or set `app.current_workspace_id = ''` and rely on `current_workspace_id() IS NULL` policies. Document carefully.

---

## Key derived calculations

### Tier of an athlete

```python
def calculate_tier(athlete_id: UUID, workspace_id: UUID) -> TierResult:
    """
    Highest tier where ALL requirements are met by latest assessment per skill.
    """
    # Get latest assessment per skill for this athlete
    latest_scores = await db.fetch_all("""
        SELECT DISTINCT ON (skill_id) skill_id, level
        FROM assessments
        WHERE workspace_id = :wid AND athlete_id = :aid
        ORDER BY skill_id, recorded_at DESC
    """, {"wid": workspace_id, "aid": athlete_id})
    
    scores = {row["skill_id"]: row["level"] for row in latest_scores}
    
    # Walk tiers from Diamond down to Beginner; first tier where all reqs met = current
    tiers = await db.fetch_all("""
        SELECT t.id, t.code, t.display_order, t.name_game_en, t.name_skill_en
        FROM tiers t
        WHERE t.curriculum_id = :cid OR t.curriculum_id IS NULL
        ORDER BY t.display_order DESC
    """, {"cid": current_curriculum_id})
    
    for tier in tiers:
        reqs = await get_tier_requirements(tier["id"])
        if all(scores.get(r.skill_id, 0) >= r.min_level for r in reqs):
            return tier
    
    return BEGINNER_TIER
```

### Progress to next tier

```python
def progress_to_next_tier(athlete_id: UUID) -> ProgressResult:
    current = calculate_tier(athlete_id, workspace_id)
    next_tier = get_next_tier(current)
    if not next_tier:
        return {"status": "max_tier"}
    
    reqs = await get_tier_requirements(next_tier.id)
    scores = await get_latest_scores(athlete_id, workspace_id)
    
    met = [r for r in reqs if scores.get(r.skill_id, 0) >= r.min_level]
    blocking = [r for r in reqs if scores.get(r.skill_id, 0) < r.min_level]
    
    return {
        "current_tier": current,
        "next_tier": next_tier,
        "progress_pct": round(len(met) / len(reqs) * 100, 1),
        "blocking_skills": sorted(blocking, key=lambda r: r.min_level - scores.get(r.skill_id, 0), reverse=True)[:5]
    }
```

### Skill category averages (for radar chart)

```sql
SELECT 
  s.category,
  AVG(latest.level)::NUMERIC(3,1) AS avg_level,
  COUNT(*) AS skills_rated
FROM (
  SELECT DISTINCT ON (skill_id) skill_id, level
  FROM assessments
  WHERE workspace_id = $1 AND athlete_id = $2
  ORDER BY skill_id, recorded_at DESC
) latest
JOIN skills s ON s.id = latest.skill_id
GROUP BY s.category;
```

### Recent gains (level-ups)

```sql
WITH skill_history AS (
  SELECT 
    skill_id,
    level,
    recorded_at,
    LAG(level) OVER (PARTITION BY skill_id ORDER BY recorded_at) AS previous_level
  FROM assessments
  WHERE workspace_id = $1 AND athlete_id = $2
)
SELECT 
  skill_id,
  previous_level,
  level AS current_level,
  recorded_at
FROM skill_history
WHERE previous_level IS NOT NULL
  AND level > previous_level
ORDER BY recorded_at DESC
LIMIT 5;
```

---

## Migration order (Alembic)

Generate in this order to avoid FK conflicts:

1. Extensions
2. `sports`
3. `users`, `user_guardians`
4. `curricula`
5. `workspaces` (FK to sports, users, curricula)
6. `workspace_memberships`
7. `athletes`
8. `skills`
9. `skill_level_descriptors`
10. `tiers`
11. `tier_requirements`
12. `sessions`
13. `assessments`
14. `reports`
15. `invites`
16. `subscriptions`
17. `audit_log`
18. RLS policies (separate migration, after all tables exist)
19. Helper functions

---

## Seed data (apps/api/scripts/seed.py)

Seeds at startup if database is empty:

1. `sports` — padel (active), tennis (inactive)
2. `curricula` — `padel-default-appa` (sport=padel, workspace_id=NULL)
3. `skills` — 27 padel skills with codes from `padel-skill-framework-v0.md`
4. `skill_level_descriptors` — 135 descriptors (27 × 5 levels) in EN + ID
5. `tiers` — 7 tiers (Beginner → Diamond) with Game and Skill style labels
6. `tier_requirements` — per `padel-skill-framework-v0.md` § 6

Idempotent: safe to run multiple times. Uses `INSERT ... ON CONFLICT DO NOTHING`.

---

## Performance notes

- Most queries scope by `workspace_id` first — RLS already does this; ensure indexes lead with `workspace_id`
- Assessments are append-only and grow fast. Consider partitioning by month at >1M rows.
- Tier calculation is O(skills × tiers) — at 27 skills × 7 tiers = trivial. Can cache result on athlete row if needed.
- Use `DISTINCT ON` for "latest per group" queries (Postgres-specific, fast)
- Avoid N+1 — use joins or `IN` clauses for batch fetches

---

## Open questions for advisor / pilot validation

1. Should we track historical tier transitions in a separate `tier_transitions` table for analytics? (V1.5 — yes, for parent-facing "tier journey" visual)
2. How to handle a workspace switching `tier_style` from 'game' to 'skill' mid-flight? (App layer renders different label, data unchanged)
3. Should `assessments` have a "private vs shareable" flag for note? (V1.5 — for now, all notes are coach-only; summary is customer-facing)
4. Multi-workspace athlete: when a trainee moves clubs, do we copy assessment history? (Policy decision: no auto-transfer, but enable explicit "request history transfer" flow in V1.5)

---

## Related

- `padel-skill-framework-v0.md` — canonical skill list, level descriptors, tier thresholds
- `06-workspace-settings.md` — UI for tier_style, brand_color, curriculum_id
- `04-coach-assessment.md` — UI that writes to `assessments`
- `08-pdf-report.md` — UI that reads from `reports`
- `13-docker-setup.md` — local dev DB setup
