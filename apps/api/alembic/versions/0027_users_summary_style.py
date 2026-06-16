"""Coach preference: AI draft voice on users.

Adds ``summary_style`` ∈ {'encouraging','direct','warm'} to ``users``.  Every
user gets ``encouraging`` by default; trainees/parents never use it but the
column is cheap.  See docs/18 for product context.

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-17
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
          ADD COLUMN summary_style VARCHAR(20) NOT NULL DEFAULT 'encouraging'
          CHECK (summary_style IN ('encouraging','direct','warm'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS summary_style")
