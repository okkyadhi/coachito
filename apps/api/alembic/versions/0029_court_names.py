"""Match Maker — host-editable court names.

The default is ``Court 1``, ``Court 2``…  Hosts can rename to "Center
Court" / "Side Court" / venue-specific labels.  Stored as a JSONB array
indexed by court_number-1 — sparse arrays are OK; a missing entry means
the default label applies.

Revision ID: 0029
Revises: 0028
Create Date: 2026-05-21
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE match_events "
        "ADD COLUMN court_names JSONB NOT NULL DEFAULT '[]'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE match_events DROP COLUMN IF EXISTS court_names")
