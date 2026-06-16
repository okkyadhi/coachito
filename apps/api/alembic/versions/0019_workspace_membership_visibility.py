"""Let active members see workspaces they belong to via RLS.

The previous policy (migration 0010) only allowed visibility when
``id = current_workspace_id()`` or the caller owned the row.  That breaks
the workspace switcher for hybrid users: once they switch into one
workspace, the others disappear from ``GET /workspaces/mine`` and there's
no way to switch back without signing out.

Fix: also expose any workspace where the caller has a membership row.
The membership policy already allows the user to see their own rows, so
the extra subquery is bounded by the same identity check.

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-14
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workspace_self_access ON workspaces")
    op.execute("""
        CREATE POLICY workspace_self_access ON workspaces
            USING (
                id = current_workspace_id()
                OR owner_user_id = current_user_id()
                OR current_workspace_id() IS NULL
                OR id IN (
                    SELECT workspace_id FROM workspace_memberships
                    WHERE user_id = current_user_id()
                      AND status = 'active'
                )
            )
            WITH CHECK (
                id = current_workspace_id()
                OR owner_user_id = current_user_id()
            )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workspace_self_access ON workspaces")
    op.execute("""
        CREATE POLICY workspace_self_access ON workspaces
            USING (
                id = current_workspace_id()
                OR owner_user_id = current_user_id()
                OR current_workspace_id() IS NULL
            )
            WITH CHECK (
                id = current_workspace_id()
                OR owner_user_id = current_user_id()
            )
    """)
