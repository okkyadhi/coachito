"""User notification preferences.

Adds a small per-user prefs table behind the trainee's Profile screen
notification toggles.  Two boolean knobs at MVP:
  - session_reminders: 24h reminder before a scheduled session
  - monthly_report:    notify when the monthly PDF is generated

Row is created lazily on first PATCH /users/me — absent row == defaults.

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-16
"""

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_notification_prefs (
            user_id            UUID PRIMARY KEY
                                 REFERENCES users(id) ON DELETE CASCADE,
            session_reminders  BOOLEAN NOT NULL DEFAULT TRUE,
            monthly_report     BOOLEAN NOT NULL DEFAULT TRUE,
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    # RLS — user can read/write only their own prefs.  Policies key off the
    # current_user_id() GUC set by the RLS middleware.
    op.execute("ALTER TABLE user_notification_prefs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_prefs_self ON user_notification_prefs
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        WITH CHECK (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'coachito_api') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON user_notification_prefs TO coachito_api;
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_notification_prefs")
