"""Trainee read-receipts on assessments.

Adds ``trainee_viewed_at`` on assessments — set the first time the trainee
opens the published assessment in the FE.  Coach surfaces it on the
status strip ("Trainee viewed 2h ago" / "Not viewed yet").

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-16
"""

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE assessments ADD COLUMN trainee_viewed_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE assessments DROP COLUMN IF EXISTS trainee_viewed_at"
    )
