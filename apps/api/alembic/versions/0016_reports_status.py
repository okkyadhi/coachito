"""Add status + error_message to reports so PDF generation can be tracked
asynchronously (RQ job → completed / failed) and the FE can poll.

Existing rows have a pdf_url already, so we default them to 'completed'.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-14
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE report_status AS ENUM ('pending', 'generating', 'completed', 'failed')"
    )
    op.execute(
        "ALTER TABLE reports ADD COLUMN status report_status NOT NULL DEFAULT 'completed'"
    )
    op.execute("ALTER TABLE reports ADD COLUMN error_message TEXT")
    op.execute(
        "CREATE INDEX idx_reports_status ON reports(status) WHERE status IN ('pending','generating')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_reports_status")
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS error_message")
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS status")
    op.execute("DROP TYPE IF EXISTS report_status")
