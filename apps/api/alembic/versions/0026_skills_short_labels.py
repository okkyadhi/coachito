"""Short labels on skills.

Adds ``short_label_en`` and ``short_label_id`` to ``skills`` for the radar
visualization on the trainee Progress page.  Falls back to truncated
``name_*`` on backfill so existing rows are never null.

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-17
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE skills ADD COLUMN short_label_en VARCHAR(20)")
    op.execute("ALTER TABLE skills ADD COLUMN short_label_id VARCHAR(20)")
    # Backfill with truncated full label so the columns are never null after
    # the migration; seed.py will overwrite with hand-curated short forms.
    op.execute(
        """
        UPDATE skills
           SET short_label_en = COALESCE(short_label_en, LEFT(name_en, 12)),
               short_label_id = COALESCE(short_label_id, LEFT(name_id, 12))
         WHERE short_label_en IS NULL OR short_label_id IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE skills DROP COLUMN IF EXISTS short_label_en")
    op.execute("ALTER TABLE skills DROP COLUMN IF EXISTS short_label_id")
