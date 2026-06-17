"""Optional coach note attached at report-generation time.

When a coach generates a report, they can now write a fresh, parent-facing
note that lands as the hero quote of the PDF.  If left blank, the renderer
falls back to the most recent session summary (the prior behaviour).

Idempotent; column added with default NULL so existing rows are untouched.

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS coach_note TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS coach_note")


# Reference sa so unused-import linters are quiet — Alembic imports it
# routinely even when this migration uses only op.execute.
_ = sa
