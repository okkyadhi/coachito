"""Add sessions.court — short text label shown in 'Up next' (e.g. 'Court 2').

The data-model originally omitted it; the coach-today screen needs it.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-13
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sessions ADD COLUMN court VARCHAR(50)")


def downgrade() -> None:
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS court")
