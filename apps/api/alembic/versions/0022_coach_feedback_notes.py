"""Coach-to-admin feedback notes about curriculum.

A simple inbox: coach sends a note (optionally tied to a skill), admin
reads it.  No threading — if admin wants to respond, they do it out of
band.  Workspace-scoped with the same RLS shape as feedbacks.

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-16
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE coach_feedback_notes (
            id               UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id     UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            author_user_id   UUID NOT NULL REFERENCES users(id),
            subject_skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
            body             TEXT NOT NULL CHECK (length(body) > 0 AND length(body) <= 2000),
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            read_at          TIMESTAMPTZ
        )
        """
    )

    # Inbox query: unread first, then newest.
    op.execute(
        "CREATE INDEX idx_coach_feedback_inbox "
        "ON coach_feedback_notes (workspace_id, (read_at IS NULL) DESC, created_at DESC)"
    )

    # Per-skill lookup (when admin opens a skill and sees prior feedback about it).
    op.execute(
        "CREATE INDEX idx_coach_feedback_by_skill "
        "ON coach_feedback_notes (workspace_id, subject_skill_id) "
        "WHERE subject_skill_id IS NOT NULL"
    )

    # Grant DML to the runtime app role — skip silently if role absent (Railway).
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'coachito_api') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON coach_feedback_notes TO coachito_api;
          END IF;
        END $$
        """
    )

    # RLS — workspace tenant isolation, mirroring feedbacks.
    op.execute("ALTER TABLE coach_feedback_notes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE coach_feedback_notes FORCE  ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY coach_feedback_notes_tenant ON coach_feedback_notes
            USING (workspace_id = current_workspace_id())
            WITH CHECK (workspace_id = current_workspace_id())
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS coach_feedback_notes CASCADE")
