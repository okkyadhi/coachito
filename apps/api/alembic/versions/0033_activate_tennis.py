"""Multi-sport — M5: activate tennis as a platform sport.

tennis-skill-framework-v0.1 §10.2.  The tennis curriculum (skills,
descriptors, tiers, requirements) is already seeded by scripts/seed.py; this
just flips ``sports.is_active`` so workspaces can enable tennis from the
Sports settings panel.  No workspace gets tennis automatically — enabling is
an explicit per-workspace action (POST /workspaces/me/sports).

Idempotent and reversible.

Revision ID: 0033
Revises: 0032
Create Date: 2026-05-21
"""

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE sports SET is_active = TRUE WHERE code = 'tennis'")


def downgrade() -> None:
    # Only re-gate tennis if no workspace has opted into it, so we never strand
    # live workspace data behind an inactive sport.
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
