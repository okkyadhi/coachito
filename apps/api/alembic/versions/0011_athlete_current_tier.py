"""Cache the trainee's computed current tier on the athlete row.

Tier is derived from latest assessments per skill matched against
tier_requirements (docs/12 § Performance notes).  Recomputing it on every
read is fine at MVP scale but unnecessary — we update it whenever a new
assessment lands, and read endpoints just join.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-13
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE athletes ADD COLUMN current_tier_id UUID REFERENCES tiers(id)"
    )
    op.execute(
        "CREATE INDEX idx_athletes_current_tier ON athletes(current_tier_id) "
        "WHERE current_tier_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_athletes_current_tier")
    op.execute("ALTER TABLE athletes DROP COLUMN IF EXISTS current_tier_id")
