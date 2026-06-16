"""DB helper functions: latest score per skill, tier calculation support.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-11
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convenience view: latest assessment level per (workspace, athlete, skill)
    op.execute("""
        CREATE OR REPLACE VIEW latest_scores AS
        SELECT DISTINCT ON (workspace_id, athlete_id, skill_id)
            workspace_id,
            athlete_id,
            skill_id,
            level,
            recorded_at,
            coach_id,
            session_id
        FROM assessments
        ORDER BY workspace_id, athlete_id, skill_id, recorded_at DESC
    """)

    # Scalar helper: set workspace context within a transaction
    op.execute("""
        CREATE OR REPLACE FUNCTION set_workspace_context(p_workspace_id UUID)
        RETURNS VOID LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM set_config('app.current_workspace_id', p_workspace_id::TEXT, TRUE);
        END;
        $$
    """)

    # Scalar helper: clear workspace context (for admin/seed operations)
    op.execute("""
        CREATE OR REPLACE FUNCTION clear_workspace_context()
        RETURNS VOID LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM set_config('app.current_workspace_id', '', TRUE);
        END;
        $$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS clear_workspace_context()")
    op.execute("DROP FUNCTION IF EXISTS set_workspace_context(UUID)")
    op.execute("DROP VIEW   IF EXISTS latest_scores")
