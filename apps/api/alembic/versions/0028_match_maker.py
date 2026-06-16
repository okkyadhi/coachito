"""Match Maker — foundation (docs/20 §10).

Adds 5 new tables, 5 new enum types, and the ``'play'`` value to the
``workspaces.type`` CHECK constraint.  RLS on every new table follows the
existing workspace-scoped pattern (writes filtered by
``current_workspace_id()`` GUC).  Public-read role for shareable standings
URLs is deferred to Phase 2 — at draft state nothing is publicly visible.

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-19
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New enum types ───────────────────────────────────────────
    op.execute(
        """
        CREATE TYPE match_event_status AS ENUM (
            'draft','active','completed','cancelled'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE match_event_format AS ENUM (
            'americano','team_americano','mix_americano',
            'mexicano','team_mexicano','mixicano',
            'koth','team_koth'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE match_scoring_mode AS ENUM (
            'point','normal_first_to','normal_total','normal_first_to_tiebreak'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE match_mexicano_pairing AS ENUM ('1_3_vs_2_4','1_4_vs_2_3')
        """
    )
    op.execute(
        """
        CREATE TYPE match_leaderboard_sort AS ENUM ('points','wins')
        """
    )

    # ── 'play' workspace type ───────────────────────────────────
    # The ``workspaces.type`` column is a VARCHAR + CHECK, not an enum
    # (see migration 0002).  Drop + re-add the constraint to include 'play'.
    op.execute(
        "ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_type_check"
    )
    op.execute(
        """
        ALTER TABLE workspaces
          ADD CONSTRAINT workspaces_type_check
          CHECK (type IN ('club','personal','play'))
        """
    )

    # ── match_events ─────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE match_events (
            id                  UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id        UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            title               VARCHAR(120) NOT NULL,
            venue               VARCHAR(200),
            format              match_event_format NOT NULL,
            scoring_mode        match_scoring_mode NOT NULL,
            scoring_target      INTEGER,
            round_timer_seconds INTEGER,
            court_count         INTEGER NOT NULL CHECK (court_count >= 1),
            mexicano_pairing    match_mexicano_pairing,
            leaderboard_sort    match_leaderboard_sort NOT NULL DEFAULT 'points',
            total_rounds        INTEGER NOT NULL DEFAULT 0,
            current_round       INTEGER NOT NULL DEFAULT 0,
            status              match_event_status NOT NULL DEFAULT 'draft',
            is_public           BOOLEAN NOT NULL DEFAULT TRUE,
            public_slug         VARCHAR(20),
            starts_at           TIMESTAMPTZ,
            completed_at        TIMESTAMPTZ,
            created_by_id       UUID NOT NULL REFERENCES users(id),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archived_at         TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_match_events_workspace_active "
        "ON match_events (workspace_id, status, starts_at DESC) "
        "WHERE archived_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_match_events_slug "
        "ON match_events (public_slug) WHERE public_slug IS NOT NULL"
    )

    # ── match_event_teams ────────────────────────────────────────
    # Created BEFORE participants because participants.team_id references it.
    op.execute(
        """
        CREATE TABLE match_event_teams (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_id      UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
            display_name  VARCHAR(120) NOT NULL,
            tag           VARCHAR(20),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_met_event ON match_event_teams (event_id)"
    )

    # ── match_event_participants ─────────────────────────────────
    op.execute(
        """
        CREATE TABLE match_event_participants (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_id        UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
            athlete_id      UUID REFERENCES athletes(id) ON DELETE SET NULL,
            claim_user_id   UUID REFERENCES users(id) ON DELETE SET NULL,
            display_name    VARCHAR(120) NOT NULL,
            team_id         UUID REFERENCES match_event_teams(id) ON DELETE SET NULL,
            tag             VARCHAR(20),
            initial_seed    INTEGER,
            joined_round    INTEGER NOT NULL DEFAULT 1,
            withdrew_round  INTEGER,
            replaced_by_id  UUID REFERENCES match_event_participants(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_mep_event_active "
        "ON match_event_participants (event_id, withdrew_round) "
        "WHERE withdrew_round IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_mep_claim_user "
        "ON match_event_participants (claim_user_id) "
        "WHERE claim_user_id IS NOT NULL"
    )

    # ── match_event_rounds ───────────────────────────────────────
    op.execute(
        """
        CREATE TABLE match_event_rounds (
            id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_id      UUID NOT NULL REFERENCES match_events(id) ON DELETE CASCADE,
            round_number  INTEGER NOT NULL,
            started_at    TIMESTAMPTZ,
            completed_at  TIMESTAMPTZ,
            UNIQUE (event_id, round_number)
        )
        """
    )

    # ── match_event_matches ──────────────────────────────────────
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_mem_round_court "
        "ON match_event_matches (round_id, court_number)"
    )

    # ── RLS ──────────────────────────────────────────────────────
    # Workspace-scoped writes follow the existing pattern (the
    # tenant_isolation policy used by sessions / assessments / etc.).
    for table in (
        "match_events",
        "match_event_teams",
        "match_event_participants",
        "match_event_rounds",
        "match_event_matches",
    ):
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
    for table in (
        "match_event_matches",
        "match_event_rounds",
        "match_event_participants",
        "match_event_teams",
        "match_events",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")

    op.execute("DROP TYPE IF EXISTS match_leaderboard_sort")
    op.execute("DROP TYPE IF EXISTS match_mexicano_pairing")
    op.execute("DROP TYPE IF EXISTS match_scoring_mode")
    op.execute("DROP TYPE IF EXISTS match_event_format")
    op.execute("DROP TYPE IF EXISTS match_event_status")

    op.execute(
        "ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_type_check"
    )
    op.execute(
        """
        ALTER TABLE workspaces
          ADD CONSTRAINT workspaces_type_check
          CHECK (type IN ('club','personal'))
        """
    )
