"""Per-session reports — add ``session_id`` so a report can be scoped to a
single coaching session instead of a calendar period.

The column is nullable: monthly auto-reports keep ``session_id=NULL`` and use
``period_start/end`` as before.

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-14
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reports ADD COLUMN session_id UUID REFERENCES sessions(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX idx_reports_session ON reports(session_id) WHERE session_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_reports_session")
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS session_id")
