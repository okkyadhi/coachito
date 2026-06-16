"""Athletes, skills, skill_level_descriptors, tiers, tier_requirements.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-11
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Athletes ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE athletes (
            id             UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id   UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id        UUID        REFERENCES users(id) ON DELETE SET NULL,
            display_name   VARCHAR(120) NOT NULL,
            date_of_birth  DATE,
            is_minor       BOOLEAN     NOT NULL DEFAULT FALSE,
            joined_at      DATE        NOT NULL DEFAULT CURRENT_DATE,
            notes          TEXT,
            archived_at    TIMESTAMPTZ,
            created_by_id  UUID        NOT NULL REFERENCES users(id),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_athletes_workspace_active ON athletes (workspace_id) WHERE archived_at IS NULL")
    op.execute("CREATE INDEX idx_athletes_user             ON athletes (user_id)       WHERE user_id IS NOT NULL")
    # GIN for fuzzy name search; workspace_id filter uses the B-tree index above
    op.execute("CREATE INDEX idx_athletes_name_trgm ON athletes USING GIN (display_name gin_trgm_ops)")

    # ── Skill category enum + skills ───────────────────────────────
    op.execute("CREATE TYPE skill_category AS ENUM ('technical', 'tactical', 'physical', 'mental')")

    op.execute("""
        CREATE TABLE skills (
            id            UUID           PRIMARY KEY DEFAULT uuid_generate_v7(),
            sport_id      UUID           NOT NULL REFERENCES sports(id),
            curriculum_id UUID           REFERENCES curricula(id) ON DELETE CASCADE,
            workspace_id  UUID           REFERENCES workspaces(id) ON DELETE CASCADE,
            code          VARCHAR(80)    NOT NULL,
            category      skill_category NOT NULL,
            name_en       VARCHAR(120)   NOT NULL,
            name_id       VARCHAR(120)   NOT NULL,
            description_en TEXT,
            description_id TEXT,
            display_order INTEGER        NOT NULL DEFAULT 0,
            is_enabled    BOOLEAN        NOT NULL DEFAULT TRUE,
            created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            UNIQUE (sport_id, workspace_id, code)
        )
    """)
    op.execute("CREATE INDEX idx_skills_sport_platform ON skills (sport_id, category, display_order) WHERE workspace_id IS NULL AND is_enabled = TRUE")
    op.execute("CREATE INDEX idx_skills_workspace      ON skills (workspace_id)                       WHERE workspace_id IS NOT NULL")

    # ── Skill level descriptors ────────────────────────────────────
    op.execute("""
        CREATE TABLE skill_level_descriptors (
            id             UUID      PRIMARY KEY DEFAULT uuid_generate_v7(),
            skill_id       UUID      NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            workspace_id   UUID      REFERENCES workspaces(id) ON DELETE CASCADE,
            level          SMALLINT  NOT NULL CHECK (level BETWEEN 1 AND 5),
            description_en TEXT      NOT NULL,
            description_id TEXT      NOT NULL,
            UNIQUE (skill_id, workspace_id, level)
        )
    """)
    op.execute("CREATE INDEX idx_descriptors_skill     ON skill_level_descriptors (skill_id, level)              WHERE workspace_id IS NULL")
    op.execute("CREATE INDEX idx_descriptors_workspace ON skill_level_descriptors (workspace_id, skill_id, level) WHERE workspace_id IS NOT NULL")

    # ── Tiers ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE tiers (
            id             UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            sport_id       UUID        NOT NULL REFERENCES sports(id),
            curriculum_id  UUID        REFERENCES curricula(id) ON DELETE CASCADE,
            workspace_id   UUID        REFERENCES workspaces(id) ON DELETE CASCADE,
            code           VARCHAR(20) NOT NULL,
            display_order  INTEGER     NOT NULL,
            name_game_en   VARCHAR(50) NOT NULL,
            name_game_id   VARCHAR(50) NOT NULL,
            name_skill_en  VARCHAR(50) NOT NULL,
            name_skill_id  VARCHAR(50) NOT NULL,
            name_custom_en VARCHAR(50),
            name_custom_id VARCHAR(50),
            color_hex      VARCHAR(7),
            icon_name      VARCHAR(50),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (curriculum_id, workspace_id, code)
        )
    """)
    op.execute("CREATE INDEX idx_tiers_sport      ON tiers (sport_id, display_order)")
    op.execute("CREATE INDEX idx_tiers_curriculum ON tiers (curriculum_id, display_order) WHERE curriculum_id IS NOT NULL")

    # ── Tier requirements ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE tier_requirements (
            id        UUID     PRIMARY KEY DEFAULT uuid_generate_v7(),
            tier_id   UUID     NOT NULL REFERENCES tiers(id) ON DELETE CASCADE,
            skill_id  UUID     NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            min_level SMALLINT NOT NULL CHECK (min_level BETWEEN 1 AND 5),
            UNIQUE (tier_id, skill_id)
        )
    """)
    op.execute("CREATE INDEX idx_tier_requirements_tier ON tier_requirements (tier_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tier_requirements")
    op.execute("DROP TABLE IF EXISTS tiers")
    op.execute("DROP TABLE IF EXISTS skill_level_descriptors")
    op.execute("DROP TABLE IF EXISTS skills")
    op.execute("DROP TYPE  IF EXISTS skill_category")
    op.execute("DROP TABLE IF EXISTS athletes")
