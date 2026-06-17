"""Ensure users.phone_e164 exists.

Migration 0036_users_phone_e164 was never applied on production because
the alembic_version table already recorded "0036" from an earlier run of
0036_reports_pdf_bytes (before it was renumbered to 0037).  Alembic
treated 0036 as done and skipped the phone_e164 column add.

This migration re-applies the column with IF NOT EXISTS so it is safe
whether or not the column was added by a previous run.

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_e164 VARCHAR(20)")
    )


def downgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE users DROP COLUMN IF EXISTS phone_e164")
    )
