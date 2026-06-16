"""Allow INSERTing invites + athletes in workspace-scoped context.

Both tables already have `USING (workspace_id = current_workspace_id())`
which doubles as WITH CHECK for INSERTs by default — that's actually fine
as long as the calling session has the right workspace context (which the
db_with_rls dep sets from the JWT).  But the *workspaces* table needs an
explicit WITH CHECK because creating-a-workspace happens from a session
that's scoped to a *different* workspace (the user's previous one).

The athlete + invite flows happen entirely within the target workspace's
context so the existing USING-as-WITH-CHECK behavior is OK.  This migration
exists to keep the WITH CHECK story explicit for future readers — and adds
WITH CHECK clauses to athletes/sessions/assessments so future endpoints that
INSERT from a different context won't trip the same trap as workspaces did.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-13
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


_TABLES_NEEDING_WITH_CHECK = [
    ("athletes",      "athlete_workspace_access"),
    ("sessions",      "session_workspace_access"),
    ("assessments",   "assessment_workspace_access"),
    ("reports",       "report_workspace_access"),
    ("invites",       "invite_workspace_access"),
    ("subscriptions", "subscription_workspace_access"),
]


def upgrade() -> None:
    for table, policy in _TABLES_NEEDING_WITH_CHECK:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"""
            CREATE POLICY {policy} ON {table}
                USING (workspace_id = current_workspace_id())
                WITH CHECK (workspace_id = current_workspace_id())
        """)


def downgrade() -> None:
    for table, policy in _TABLES_NEEDING_WITH_CHECK:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"""
            CREATE POLICY {policy} ON {table}
                USING (workspace_id = current_workspace_id())
        """)
