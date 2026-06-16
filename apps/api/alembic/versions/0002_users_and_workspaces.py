"""Users, user_guardians, curricula, workspaces, workspace_memberships.

Curricula is created first (no workspace FK yet) so workspaces can reference it.
The FK from curricula → workspaces is added at the end of this migration.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            email               CITEXT      UNIQUE,
            google_sub          VARCHAR(255) UNIQUE,
            display_name        VARCHAR(120) NOT NULL,
            avatar_url          TEXT,
            preferred_locale    VARCHAR(5)  NOT NULL DEFAULT 'id',
            is_minor            BOOLEAN     NOT NULL DEFAULT FALSE,
            date_of_birth       DATE,
            primary_guardian_id UUID        REFERENCES users(id) ON DELETE SET NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen_at        TIMESTAMPTZ,
            CONSTRAINT users_has_identity CHECK (email IS NOT NULL OR google_sub IS NOT NULL)
        )
    """)
    op.execute("CREATE INDEX idx_users_email      ON users (email)               WHERE email IS NOT NULL")
    op.execute("CREATE INDEX idx_users_google_sub ON users (google_sub)          WHERE google_sub IS NOT NULL")
    op.execute("CREATE INDEX idx_users_guardian   ON users (primary_guardian_id) WHERE primary_guardian_id IS NOT NULL")

    op.execute("""
        CREATE TABLE user_guardians (
            id           UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            guardian_id  UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            relationship VARCHAR(50),
            is_primary   BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, guardian_id)
        )
    """)
    op.execute("CREATE INDEX idx_user_guardians_user     ON user_guardians (user_id)")
    op.execute("CREATE INDEX idx_user_guardians_guardian ON user_guardians (guardian_id)")

    # ── Curricula (skeleton — workspace FK added at end) ───────────
    op.execute("""
        CREATE TABLE curricula (
            id             UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            sport_id       UUID        NOT NULL REFERENCES sports(id),
            workspace_id   UUID,
            code           VARCHAR(50) NOT NULL,
            name_en        VARCHAR(120) NOT NULL,
            name_id        VARCHAR(120) NOT NULL,
            description_en TEXT,
            description_id TEXT,
            parent_id      UUID        REFERENCES curricula(id),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (sport_id, workspace_id, code)
        )
    """)
    op.execute("CREATE INDEX idx_curricula_sport_default ON curricula (sport_id) WHERE workspace_id IS NULL")
    op.execute("CREATE INDEX idx_curricula_workspace     ON curricula (workspace_id) WHERE workspace_id IS NOT NULL")

    # ── Workspace role / membership enums ──────────────────────────
    op.execute("""
        CREATE TYPE workspace_role AS ENUM (
            'club_admin', 'head_coach', 'coach', 'trainee', 'parent'
        )
    """)
    op.execute("""
        CREATE TYPE membership_status AS ENUM ('active', 'invited', 'archived')
    """)

    # ── Workspaces ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE workspaces (
            id                    UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            sport_id              UUID        NOT NULL REFERENCES sports(id),
            type                  VARCHAR(20) NOT NULL CHECK (type IN ('club', 'personal')),
            name                  VARCHAR(120) NOT NULL,
            slug                  VARCHAR(60) UNIQUE,
            city                  VARCHAR(100),
            brand_color           VARCHAR(7),
            logo_url              TEXT,
            tier_style            VARCHAR(20) NOT NULL DEFAULT 'game'
                                  CHECK (tier_style IN ('game', 'skill', 'custom')),
            primary_locale        VARCHAR(5)  NOT NULL DEFAULT 'id',
            curriculum_id         UUID        REFERENCES curricula(id),
            plan                  VARCHAR(20) NOT NULL DEFAULT 'free_trial'
                                  CHECK (plan IN ('free_trial', 'solo_coach', 'club_starter', 'club_pro')),
            trial_ends_at         TIMESTAMPTZ,
            active_trainee_quota  INTEGER     NOT NULL DEFAULT 20,
            allow_coach_overrides BOOLEAN     NOT NULL DEFAULT FALSE,
            owner_user_id         UUID        NOT NULL REFERENCES users(id),
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archived_at           TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX idx_workspaces_owner      ON workspaces (owner_user_id)")
    op.execute("CREATE INDEX idx_workspaces_sport_type ON workspaces (sport_id, type)")
    op.execute("CREATE INDEX idx_workspaces_active     ON workspaces (id) WHERE archived_at IS NULL")

    # ── Workspace memberships ──────────────────────────────────────
    op.execute("""
        CREATE TABLE workspace_memberships (
            id            UUID             PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id  UUID             NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id       UUID             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role          workspace_role   NOT NULL,
            status        membership_status NOT NULL DEFAULT 'invited',
            invited_at    TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
            joined_at     TIMESTAMPTZ,
            archived_at   TIMESTAMPTZ,
            invited_by_id UUID             REFERENCES users(id),
            UNIQUE (workspace_id, user_id, role)
        )
    """)
    op.execute("CREATE INDEX idx_memberships_workspace_user ON workspace_memberships (workspace_id, user_id)")
    op.execute("CREATE INDEX idx_memberships_user           ON workspace_memberships (user_id)               WHERE status = 'active'")
    op.execute("CREATE INDEX idx_memberships_workspace_role ON workspace_memberships (workspace_id, role)    WHERE status = 'active'")

    # ── Add workspace FK to curricula (circular FK resolved) ───────
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT fk_curricula_workspace
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE curricula DROP CONSTRAINT IF EXISTS fk_curricula_workspace")
    op.execute("DROP TABLE IF EXISTS workspace_memberships")
    op.execute("DROP TABLE IF EXISTS workspaces")
    op.execute("DROP TABLE IF EXISTS curricula")
    op.execute("DROP TYPE  IF EXISTS membership_status")
    op.execute("DROP TYPE  IF EXISTS workspace_role")
    op.execute("DROP TABLE IF EXISTS user_guardians")
    op.execute("DROP TABLE IF EXISTS users")
