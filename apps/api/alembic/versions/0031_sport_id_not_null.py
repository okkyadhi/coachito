"""Multi-sport — M2b: promote sessions/assessments sport_id to NOT NULL.

Follows the API dual-write deploy (multisport M2): every session and
assessment created by the running API now sets ``sport_id``, and M1 already
backfilled existing rows.  This migration hardens the columns.

A safety backfill repeats here (idempotent) so the constraint can't fail on
any straggler rows written between M1 and this deploy.

Revision ID: 0031
Revises: 0030
Create Date: 2026-05-21
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("sessions", "assessments"):
        op.execute(
            f"""
            UPDATE {table} t
            SET sport_id = w.sport_id
            FROM workspaces w
            WHERE w.id = t.workspace_id AND t.sport_id IS NULL
            """
        )
        op.execute(f"ALTER TABLE {table} ALTER COLUMN sport_id SET NOT NULL")


def downgrade() -> None:
    for table in ("sessions", "assessments"):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN sport_id DROP NOT NULL")
