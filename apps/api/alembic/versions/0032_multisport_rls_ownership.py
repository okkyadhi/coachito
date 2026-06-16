"""Multi-sport — refine join-table RLS to allow workspace creation.

The M1 join tables (workspace_sports, athlete_sports, membership_sports,
athlete_sport_tiers) shipped with the strict ``workspace_id = GUC``
tenant_isolation policy.  That breaks workspace *creation*: the dual-write of
the workspace_sports / membership_sports rows happens before
``app.current_workspace_id`` points at the new workspace, so the WITH CHECK
fails.

Fix mirrors the workspaces / workspace_memberships policies (migration 0010):
add an ownership escape — a row is visible/insertable if the caller owns the
workspace it belongs to, or the GUC matches, or no workspace is active yet
(first-workspace creation).  Reads also allow any active member of the
workspace, so ``GET /workspaces/mine`` can surface ``sports[]`` for every
workspace a user belongs to (not just the active one).  Normal in-workspace
writes still go through ``workspace_id = current_workspace_id()``.

Revision ID: 0032
Revises: 0031
Create Date: 2026-05-21
"""

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

_TABLES = (
    "workspace_sports",
    "athlete_sports",
    "membership_sports",
    "athlete_sport_tiers",
)


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                workspace_id = current_workspace_id()
                OR EXISTS (
                    SELECT 1 FROM workspaces w
                    WHERE w.id = {table}.workspace_id
                      AND w.owner_user_id = current_user_id()
                )
                OR EXISTS (
                    SELECT 1 FROM workspace_memberships m
                    WHERE m.workspace_id = {table}.workspace_id
                      AND m.user_id = current_user_id()
                      AND m.archived_at IS NULL
                )
            )
            WITH CHECK (
                workspace_id = current_workspace_id()
                OR current_workspace_id() IS NULL
                OR EXISTS (
                    SELECT 1 FROM workspaces w
                    WHERE w.id = {table}.workspace_id
                      AND w.owner_user_id = current_user_id()
                )
            )
            """
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                workspace_id = NULLIF(
                    current_setting('app.current_workspace_id', true), ''
                )::uuid
            )
            WITH CHECK (
                workspace_id = NULLIF(
                    current_setting('app.current_workspace_id', true), ''
                )::uuid
            )
            """
        )
