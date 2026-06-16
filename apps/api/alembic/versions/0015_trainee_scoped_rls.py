"""Trainee-scoped RLS: a user signed in as `trainee`/`parent` can only see
their own athlete row + their own assessments + their own sessions, even
when their JWT puts them in the workspace context.

Mechanism: a STABLE function `current_workspace_role()` resolves the caller's
role for the current workspace; policies AND in a self-scope clause when the
role is trainee/parent.

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-14
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION current_workspace_role() RETURNS TEXT AS $$
            SELECT role::TEXT
            FROM workspace_memberships
            WHERE user_id = current_user_id()
              AND workspace_id = current_workspace_id()
              AND status = 'active'
            LIMIT 1
        $$ LANGUAGE SQL STABLE
    """)

    # athletes — trainees/parents only see their own row.
    op.execute("DROP POLICY IF EXISTS athlete_workspace_access ON athletes")
    op.execute("""
        CREATE POLICY athlete_workspace_access ON athletes
            USING (
                workspace_id = current_workspace_id()
                AND (
                    COALESCE(current_workspace_role(), '') NOT IN ('trainee', 'parent')
                    OR user_id = current_user_id()
                )
            )
            WITH CHECK (workspace_id = current_workspace_id())
    """)

    # assessments — trainees only see assessments tied to their own athlete row.
    op.execute("DROP POLICY IF EXISTS assessment_workspace_access ON assessments")
    op.execute("""
        CREATE POLICY assessment_workspace_access ON assessments
            USING (
                workspace_id = current_workspace_id()
                AND (
                    COALESCE(current_workspace_role(), '') NOT IN ('trainee', 'parent')
                    OR athlete_id IN (
                        SELECT id FROM athletes
                        WHERE user_id = current_user_id()
                          AND workspace_id = current_workspace_id()
                    )
                )
            )
            WITH CHECK (workspace_id = current_workspace_id())
    """)

    # sessions — same pattern.
    op.execute("DROP POLICY IF EXISTS session_workspace_access ON sessions")
    op.execute("""
        CREATE POLICY session_workspace_access ON sessions
            USING (
                workspace_id = current_workspace_id()
                AND (
                    COALESCE(current_workspace_role(), '') NOT IN ('trainee', 'parent')
                    OR athlete_id IN (
                        SELECT id FROM athletes
                        WHERE user_id = current_user_id()
                          AND workspace_id = current_workspace_id()
                    )
                )
            )
            WITH CHECK (workspace_id = current_workspace_id())
    """)


def downgrade() -> None:
    # Restore the broader workspace-only policies.
    op.execute("DROP POLICY IF EXISTS athlete_workspace_access ON athletes")
    op.execute("""
        CREATE POLICY athlete_workspace_access ON athletes
            USING (workspace_id = current_workspace_id())
            WITH CHECK (workspace_id = current_workspace_id())
    """)
    op.execute("DROP POLICY IF EXISTS assessment_workspace_access ON assessments")
    op.execute("""
        CREATE POLICY assessment_workspace_access ON assessments
            USING (workspace_id = current_workspace_id())
            WITH CHECK (workspace_id = current_workspace_id())
    """)
    op.execute("DROP POLICY IF EXISTS session_workspace_access ON sessions")
    op.execute("""
        CREATE POLICY session_workspace_access ON sessions
            USING (workspace_id = current_workspace_id())
            WITH CHECK (workspace_id = current_workspace_id())
    """)
    op.execute("DROP FUNCTION IF EXISTS current_workspace_role()")
