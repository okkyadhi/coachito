"""Add client_assessment_id for offline-queue idempotency.

The FE generates a UUID per assessment row before save.  Retries from the
sync queue carry the same UUID so the server can upsert.  Unique globally —
UUID collision across workspaces is not a realistic concern.

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-13
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE assessments ADD COLUMN client_assessment_id UUID"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_assessments_client_id "
        "ON assessments(client_assessment_id) "
        "WHERE client_assessment_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_assessments_client_id")
    op.execute("ALTER TABLE assessments DROP COLUMN IF EXISTS client_assessment_id")
