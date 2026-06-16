"""Partial unique indexes for platform-level rows (workspace_id IS NULL).

Standard UNIQUE constraints treat NULL != NULL, so (sport_id, NULL, code)
allows duplicates. Partial unique indexes close that gap for seeded rows.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-11
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # curricula: unique code per sport for platform defaults
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_curricula_platform_code
            ON curricula (sport_id, code)
            WHERE workspace_id IS NULL
    """)

    # skills: unique code per sport for platform skills
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_skills_platform_code
            ON skills (sport_id, code)
            WHERE workspace_id IS NULL
    """)

    # skill_level_descriptors: unique level per skill for platform descriptors
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_descriptors_platform_level
            ON skill_level_descriptors (skill_id, level)
            WHERE workspace_id IS NULL
    """)

    # tiers: unique code per (sport, curriculum) for platform tiers
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tiers_platform_code
            ON tiers (sport_id, curriculum_id, code)
            WHERE workspace_id IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_tiers_platform_code")
    op.execute("DROP INDEX IF EXISTS uq_descriptors_platform_level")
    op.execute("DROP INDEX IF EXISTS uq_skills_platform_code")
    op.execute("DROP INDEX IF EXISTS uq_curricula_platform_code")
