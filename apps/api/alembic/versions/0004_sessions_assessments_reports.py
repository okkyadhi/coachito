"""Sessions, assessments (append-only scores), and reports (PDF).

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-11
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE session_focus AS ENUM (
            'drilling', 'match_play', 'conditioning',
            'mental_training', 'technique_focus', 'general'
        )
    """)

    op.execute("""
        CREATE TABLE sessions (
            id             UUID         PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id   UUID         NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            athlete_id     UUID         NOT NULL REFERENCES athletes(id)   ON DELETE CASCADE,
            coach_id       UUID         NOT NULL REFERENCES users(id),
            scheduled_at   TIMESTAMPTZ  NOT NULL,
            duration_min   INTEGER      NOT NULL DEFAULT 60,
            focus          session_focus,
            summary        TEXT,
            internal_notes TEXT,
            status         VARCHAR(20)  NOT NULL DEFAULT 'scheduled'
                           CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show')),
            completed_at   TIMESTAMPTZ,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_sessions_workspace_athlete ON sessions (workspace_id, athlete_id, scheduled_at DESC)")
    op.execute("CREATE INDEX idx_sessions_workspace_coach   ON sessions (workspace_id, coach_id,   scheduled_at DESC)")
    op.execute("CREATE INDEX idx_sessions_workspace_today   ON sessions (workspace_id, scheduled_at) WHERE status = 'scheduled'")

    op.execute("""
        CREATE TABLE assessments (
            id                 UUID      PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id       UUID      NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            athlete_id         UUID      NOT NULL REFERENCES athletes(id)   ON DELETE CASCADE,
            coach_id           UUID      NOT NULL REFERENCES users(id),
            session_id         UUID      REFERENCES sessions(id) ON DELETE SET NULL,
            skill_id           UUID      NOT NULL REFERENCES skills(id),
            level              SMALLINT  NOT NULL CHECK (level BETWEEN 1 AND 5),
            note               TEXT,
            recorded_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            client_recorded_at TIMESTAMPTZ,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_assessments_athlete_skill_recent ON assessments (workspace_id, athlete_id, skill_id, recorded_at DESC)")
    op.execute("CREATE INDEX idx_assessments_session              ON assessments (session_id) WHERE session_id IS NOT NULL")
    op.execute("CREATE INDEX idx_assessments_athlete_recent       ON assessments (workspace_id, athlete_id, recorded_at DESC)")

    op.execute("""
        CREATE TABLE reports (
            id               UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            athlete_id       UUID        NOT NULL REFERENCES athletes(id)   ON DELETE CASCADE,
            coach_id         UUID        NOT NULL REFERENCES users(id),
            period_start     DATE        NOT NULL,
            period_end       DATE        NOT NULL,
            generated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            pdf_url          TEXT,
            pdf_size_bytes   INTEGER,
            generation_type  VARCHAR(20) NOT NULL DEFAULT 'auto'
                             CHECK (generation_type IN ('auto', 'manual')),
            generated_by_id  UUID        REFERENCES users(id),
            shared_at        TIMESTAMPTZ,
            view_count       INTEGER     NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX idx_reports_workspace_athlete ON reports (workspace_id, athlete_id, period_end DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reports")
    op.execute("DROP TABLE IF EXISTS assessments")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TYPE  IF EXISTS session_focus")
