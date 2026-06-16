"""Add app.current_user_id GUC + relaxed membership policy.

Listing the workspaces a user belongs to is a cross-workspace operation, so the
strict workspace_id-only policy on workspace_memberships blocks the natural
"GET /workspaces/mine" query.  We add a current_user_id() helper, set it in
the RLS dependency alongside current_workspace_id(), and replace the
membership policy with one that also allows a user to see their own rows.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-12
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION current_user_id() RETURNS UUID AS $$
            SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::UUID
        $$ LANGUAGE SQL STABLE
    """)

    # Replace the strict membership policy with one that also allows
    # self-access (any membership row belonging to the calling user).
    op.execute("DROP POLICY IF EXISTS membership_workspace_access ON workspace_memberships")
    op.execute("""
        CREATE POLICY membership_self_or_workspace_access ON workspace_memberships
            USING (
                user_id = current_user_id()
                OR workspace_id = current_workspace_id()
            )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS membership_self_or_workspace_access ON workspace_memberships")
    op.execute("""
        CREATE POLICY membership_workspace_access ON workspace_memberships
            USING (workspace_id = current_workspace_id())
    """)
    op.execute("DROP FUNCTION IF EXISTS current_user_id()")
