"""Coach bio JSONB on workspace_memberships.

Adds a coach-self-presentation JSON blob keyed by membership row, so a coach
can present differently per workspace.  Default `{}` so existing rows
upgrade cleanly.  Bio absence is not an error — the FE renders a minimal
card when the object is empty.

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-16
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE workspace_memberships "
        "ADD COLUMN bio JSONB NOT NULL DEFAULT '{}'::jsonb"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE workspace_memberships DROP COLUMN IF EXISTS bio"
    )
