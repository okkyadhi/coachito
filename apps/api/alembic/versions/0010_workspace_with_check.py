"""Add WITH CHECK clauses to workspace + membership policies so users can
create workspaces while already scoped to another one.

Without WITH CHECK, Postgres reuses USING for INSERT validation, so inserting
a new workspace W2 from a session scoped to workspace W1 fails the
``id = current_workspace_id()`` check.  The fix: USING controls visibility;
WITH CHECK enforces ownership.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-12
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── workspaces ─────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS workspace_self_access ON workspaces")
    op.execute("""
        CREATE POLICY workspace_self_access ON workspaces
            USING (
                id = current_workspace_id()
                OR owner_user_id = current_user_id()
                OR current_workspace_id() IS NULL
            )
            WITH CHECK (
                owner_user_id = current_user_id()
                OR current_user_id() IS NULL
            )
    """)

    # ── workspace_memberships ──────────────────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS membership_self_or_workspace_access ON workspace_memberships"
    )
    op.execute("""
        CREATE POLICY membership_self_or_workspace_access ON workspace_memberships
            USING (
                user_id = current_user_id()
                OR workspace_id = current_workspace_id()
            )
            WITH CHECK (
                user_id = current_user_id()
                OR workspace_id = current_workspace_id()
                OR current_user_id() IS NULL
            )
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS membership_self_or_workspace_access ON workspace_memberships"
    )
    op.execute("""
        CREATE POLICY membership_self_or_workspace_access ON workspace_memberships
            USING (
                user_id = current_user_id()
                OR workspace_id = current_workspace_id()
            )
    """)
    op.execute("DROP POLICY IF EXISTS workspace_self_access ON workspaces")
    op.execute("""
        CREATE POLICY workspace_self_access ON workspaces
            USING (id = current_workspace_id() OR current_workspace_id() IS NULL)
    """)
