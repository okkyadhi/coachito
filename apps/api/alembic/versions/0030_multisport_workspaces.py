"""Multi-sport workspaces — M1 (additive foundation).

First step of the multi-sport refactor (tennis-skill-framework-v0.1 §3).
Additive only: new join tables + backfill + new sport_id columns on
sessions and assessments.  The old single-sport columns
(``workspaces.sport_id``, ``workspaces.curriculum_id``) are **kept** — they
are dropped in a later migration (doc M4) once the API reads from the new
tables.  This is the dual-write rollback window, so M1 is safe to ship and
roll back on its own.

Deviations from the doc's raw SQL, adapted to this repo:
- ``workspace_sports.curriculum_id`` is NULLABLE.  ``workspaces.curriculum_id``
  is already nullable (a missing curriculum falls back to the platform default
  at query time); we preserve that semantics rather than inventing a value.
- ``athlete_sports`` / ``membership_sports`` / ``athlete_sport_tiers`` carry a
  denormalized ``workspace_id``.  The doc omitted it, but every tenant table in
  this codebase uses the same ``tenant_isolation`` RLS policy keyed on a direct
  ``workspace_id`` column.  workspace_id is immutable for an athlete/membership,
  so there is no drift.  Sport filtering itself stays an app-layer concern
  (doc §3.4) — RLS remains sport-agnostic.
- Assessments have no ``skill_id`` (the v2 model stores scores in
  ``assessment_scores``).  Backfill derives sport from the workspace, which is
  single-sport today, so it is exact.
- ``sessions.sport_id`` / ``assessments.sport_id`` are added NULLABLE and
  backfilled, but **not** promoted to NOT NULL here (the doc promotes
  immediately).  The running API does not write sport_id yet, so a NOT NULL
  column with no default would fail every new INSERT the moment M1 deploys.
  The NOT NULL promotion moves to a follow-up migration after the API
  dual-writes sport_id (doc M2/M3).  This keeps M1 safe to ship and roll back
  on its own.

Revision ID: 0030
Revises: 0029
Create Date: 2026-05-21
"""

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

_NEW_TABLES = (
    "workspace_sports",
    "athlete_sports",
    "membership_sports",
    "athlete_sport_tiers",
)


def upgrade() -> None:
    # ── workspace_sports ─────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE workspace_sports (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            sport_id      UUID NOT NULL REFERENCES sports(id),
            curriculum_id UUID REFERENCES curricula(id),
            is_active     BOOLEAN NOT NULL DEFAULT TRUE,
            enabled_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archived_at   TIMESTAMPTZ,
            UNIQUE (workspace_id, sport_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_workspace_sports_workspace "
        "ON workspace_sports (workspace_id) WHERE is_active = TRUE"
    )
    op.execute(
        """
        INSERT INTO workspace_sports (workspace_id, sport_id, curriculum_id, is_active)
        SELECT id, sport_id, curriculum_id, TRUE
        FROM workspaces
        WHERE archived_at IS NULL
        """
    )

    # ── athlete_sports ───────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE athlete_sports (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            athlete_id      UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            sport_id        UUID NOT NULL REFERENCES sports(id),
            joined_sport_at DATE NOT NULL DEFAULT CURRENT_DATE,
            archived_at     TIMESTAMPTZ,
            UNIQUE (athlete_id, sport_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_athlete_sports_athlete "
        "ON athlete_sports (athlete_id) WHERE archived_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_athlete_sports_sport "
        "ON athlete_sports (sport_id) WHERE archived_at IS NULL"
    )
    op.execute(
        """
        INSERT INTO athlete_sports (workspace_id, athlete_id, sport_id, joined_sport_at)
        SELECT a.workspace_id, a.id, w.sport_id, a.joined_at
        FROM athletes a
        JOIN workspaces w ON w.id = a.workspace_id
        WHERE a.archived_at IS NULL
        """
    )

    # ── membership_sports ────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE membership_sports (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            membership_id UUID NOT NULL
                          REFERENCES workspace_memberships(id) ON DELETE CASCADE,
            sport_id      UUID NOT NULL REFERENCES sports(id),
            certification VARCHAR(120),
            certified_at  DATE,
            UNIQUE (membership_id, sport_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_membership_sports_membership "
        "ON membership_sports (membership_id)"
    )
    op.execute(
        """
        INSERT INTO membership_sports (workspace_id, membership_id, sport_id)
        SELECT m.workspace_id, m.id, w.sport_id
        FROM workspace_memberships m
        JOIN workspaces w ON w.id = m.workspace_id
        WHERE m.archived_at IS NULL
        """
    )

    # ── athlete_sport_tiers (denormalized current tier per sport) ─
    op.execute(
        """
        CREATE TABLE athlete_sport_tiers (
            id           UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            athlete_id   UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            sport_id     UUID NOT NULL REFERENCES sports(id),
            tier_id      UUID NOT NULL REFERENCES tiers(id),
            promoted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (athlete_id, sport_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_athlete_sport_tiers_athlete "
        "ON athlete_sport_tiers (athlete_id)"
    )
    op.execute(
        """
        INSERT INTO athlete_sport_tiers (workspace_id, athlete_id, sport_id, tier_id)
        SELECT a.workspace_id, a.id, w.sport_id, a.current_tier_id
        FROM athletes a
        JOIN workspaces w ON w.id = a.workspace_id
        WHERE a.archived_at IS NULL AND a.current_tier_id IS NOT NULL
        """
    )

    # ── sessions.sport_id ────────────────────────────────────────
    op.execute("ALTER TABLE sessions ADD COLUMN sport_id UUID REFERENCES sports(id)")
    op.execute(
        """
        UPDATE sessions s
        SET sport_id = w.sport_id
        FROM workspaces w
        WHERE w.id = s.workspace_id
        """
    )
    # NOT NULL deferred until the API writes sport_id (see module docstring).
    op.execute(
        "CREATE INDEX idx_sessions_workspace_sport_date "
        "ON sessions (workspace_id, sport_id, scheduled_at)"
    )

    # ── assessments.sport_id (denormalized for query speed) ──────
    op.execute("ALTER TABLE assessments ADD COLUMN sport_id UUID REFERENCES sports(id)")
    op.execute(
        """
        UPDATE assessments a
        SET sport_id = w.sport_id
        FROM workspaces w
        WHERE w.id = a.workspace_id
        """
    )
    # NOT NULL deferred until the API writes sport_id (see module docstring).
    op.execute(
        "CREATE INDEX idx_assessments_athlete_sport_date "
        "ON assessments (athlete_id, sport_id, saved_at DESC)"
    )

    # ── RLS — standard workspace-scoped tenant_isolation ─────────
    for table in _NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                workspace_id = NULLIF(
                    current_setting('app.current_workspace_id', true), ''
                )::uuid
            )
            WITH CHECK (
                workspace_id = NULLIF(
                    current_setting('app.current_workspace_id', true), ''
                )::uuid
            )
            """
        )
        op.execute(
            f"""
            DO $$ BEGIN
              IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'coachito_api') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO coachito_api;
              END IF;
            END $$
            """
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_assessments_athlete_sport_date")
    op.execute("ALTER TABLE assessments DROP COLUMN IF EXISTS sport_id")
    op.execute("DROP INDEX IF EXISTS idx_sessions_workspace_sport_date")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS sport_id")
    for table in reversed(_NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
