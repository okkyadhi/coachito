"""Ensure the tennis sport row exists and is active.

Background: seed.py was never run on the production database, so the
sports table only ever had the ``padel`` row that migration 0030 created
as part of multi-sport bootstrap.  Migration 0033 (activate tennis) was
``UPDATE``-only and silently no-op'd in production because there was no
tennis row to flip.  Result: GET /sports never lists tennis, the Sports
settings panel never offers an "+ Add Tennis" option, and the multi-sport
architecture is invisible in the pitch demo.

This migration is idempotent and self-healing: inserts the tennis row if
missing, flips ``is_active=TRUE`` either way.  Runs at every container
start via the ``alembic upgrade head`` step in Dockerfile.allinone, so
production self-corrects on the next deploy.

Note: this does NOT seed the tennis curriculum (skills, descriptors,
tiers).  enable_sport accepts a NULL curriculum_id, so the workspace can
add tennis to its catalog, but assessments against tennis skills are
out of scope until scripts/seed.py is run against production.

Revision ID: 0039
Revises: 0038
Create Date: 2026-06-17
"""

from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert tennis if it's not there yet (matches the row seed.py would
    # create, minus the activation gate — we want it on for production).
    op.execute(
        """
        INSERT INTO sports (code, name_en, name_id, is_active, display_order)
        VALUES ('tennis', 'Tennis', 'Tenis', TRUE, 2)
        ON CONFLICT (code) DO UPDATE
          SET is_active = TRUE
        """
    )


def downgrade() -> None:
    # Mirror 0033's safe downgrade: only re-gate tennis if no workspace has
    # opted in.  Never delete the row — a workspace_sports FK could exist.
    op.execute(
        """
        UPDATE sports SET is_active = FALSE
        WHERE code = 'tennis'
          AND NOT EXISTS (
              SELECT 1 FROM workspace_sports ws
              WHERE ws.sport_id = sports.id AND ws.is_active
          )
        """
    )
