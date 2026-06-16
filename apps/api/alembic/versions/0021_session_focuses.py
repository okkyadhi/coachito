"""Multi-focus per session via a join table.

Sessions can have 0–4 focuses, stored ordered.  Existing `sessions.focus`
column is kept (nullable) and backfilled into the join table.  The column
is deprecated and will be dropped in a later release once all readers
move off it.

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-16
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE session_focuses (
            session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            focus        TEXT NOT NULL,
            ordinal      SMALLINT NOT NULL DEFAULT 0,
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            PRIMARY KEY (session_id, focus)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_session_focuses_workspace "
        "ON session_focuses (workspace_id, focus)"
    )

    # Grant DML to the runtime app role (migration owner is coachito).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON session_focuses TO coachito_api"
    )

    # RLS — same tenant-isolation shape as the other tables in this codebase.
    op.execute("ALTER TABLE session_focuses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE session_focuses FORCE  ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY session_focuses_tenant ON session_focuses
            USING (workspace_id = current_workspace_id())
            WITH CHECK (workspace_id = current_workspace_id())
        """
    )

    # Backfill: one row per existing session that has a focus.
    op.execute(
        """
        INSERT INTO session_focuses (session_id, focus, ordinal, workspace_id)
        SELECT id, focus::text, 0, workspace_id
        FROM sessions
        WHERE focus IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS session_focuses CASCADE")
