"""Assessment v2 — restructure assessments + feedbacks + audit trail.

This migration is destructive for the row-per-skill ``assessments`` data.
Per the team decision (29 rows, 0 completed sessions in dev — nothing real
to preserve), we drop the old shape and create the parent + child + audit
+ feedback tables fresh.  Production has no users yet.

Changes:
- Drop ``assessments`` (row-per-skill).
- Recreate ``assessments`` as the parent (one per session).
- Add ``assessment_scores`` (child, one per skill scored).
- Add ``assessment_edits`` (audit trail).
- Add ``feedbacks`` with anonymity flag.
- RLS: coach reads workspace, trainee/parent reads only published/edited
  for their own athlete.  Feedback: submitter sees their own; coach sees
  rows for assessments they own (the API strips identity).

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-14
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Drop old assessment shape ───────────────────────────────────
    op.execute("DROP TABLE IF EXISTS assessments CASCADE")

    # ── Parent table — one row per session ──────────────────────────
    op.execute(
        """
        CREATE TABLE assessments (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            session_id      UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
            athlete_id      UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            coach_id        UUID NOT NULL REFERENCES users(id),
            status          VARCHAR(16) NOT NULL DEFAULT 'draft'
                              CHECK (status IN ('draft','published','edited','withdrawn')),
            summary         TEXT,
            internal_notes  TEXT,
            saved_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            published_at    TIMESTAMPTZ,
            edited_at       TIMESTAMPTZ,
            withdrawn_at    TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_assessments_athlete "
        "ON assessments (workspace_id, athlete_id, published_at DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX idx_assessments_coach_drafts "
        "ON assessments (coach_id, status) WHERE status = 'draft'"
    )

    # ── Child table — one row per skill scored in this assessment ───
    op.execute(
        """
        CREATE TABLE assessment_scores (
            id               UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            assessment_id    UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
            skill_id         UUID NOT NULL REFERENCES skills(id),
            level            SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 5),
            note             TEXT,
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_assessment_scores UNIQUE (assessment_id, skill_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_assessment_scores_skill "
        "ON assessment_scores (skill_id)"
    )

    # ── Audit trail of edits ────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE assessment_edits (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            assessment_id   UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
            edited_by_id    UUID NOT NULL REFERENCES users(id),
            edited_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            changes_jsonb   JSONB NOT NULL,
            reason          TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_assessment_edits "
        "ON assessment_edits (assessment_id, edited_at DESC)"
    )

    # ── Trainee feedback ────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE feedbacks (
            id                     UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id           UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assessment_id          UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
            submitted_by_user_id   UUID NOT NULL REFERENCES users(id),
            submitter_role         VARCHAR(16) NOT NULL CHECK (submitter_role IN ('trainee','parent')),
            is_anonymous           BOOLEAN NOT NULL DEFAULT FALSE,
            rating_overall         SMALLINT NOT NULL CHECK (rating_overall BETWEEN 1 AND 5),
            rating_fairness        SMALLINT CHECK (rating_fairness BETWEEN 1 AND 5),
            comment                TEXT,
            submitted_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            edited_at              TIMESTAMPTZ,
            withdrawn_at           TIMESTAMPTZ,
            read_at                TIMESTAMPTZ,
            flagged_at             TIMESTAMPTZ,
            flagged_reason         TEXT
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_feedback_one_per_role "
        "ON feedbacks (assessment_id, submitted_by_user_id, submitter_role) "
        "WHERE withdrawn_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_feedbacks_assessment "
        "ON feedbacks (assessment_id)"
    )
    op.execute(
        "CREATE INDEX idx_feedbacks_workspace_unread "
        "ON feedbacks (workspace_id, submitted_at DESC) "
        "WHERE read_at IS NULL AND withdrawn_at IS NULL"
    )

    # ── Grants for the runtime app role ─────────────────────────────
    # Wrapped in a DO block so the GRANT is silently skipped on managed
    # Postgres hosts (Railway, Render) where coachito_api doesn't exist.
    # Local dev (Docker init script creates the role) still picks it up.
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'coachito_api') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON
              assessments, assessment_scores, assessment_edits, feedbacks
            TO coachito_api;
          END IF;
        END $$
        """
    )

    # ── RLS ─────────────────────────────────────────────────────────
    op.execute("ALTER TABLE assessments       ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessments       FORCE  ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_scores ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_scores FORCE  ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_edits  ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessment_edits  FORCE  ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedbacks         ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedbacks         FORCE  ROW LEVEL SECURITY")

    # assessments: coaches see workspace rows; trainee/parent see only
    # published/edited for their own athlete.
    op.execute(
        """
        CREATE POLICY assessment_workspace_access ON assessments
            USING (
                workspace_id = current_workspace_id()
                AND (
                    COALESCE(current_workspace_role(), '') NOT IN ('trainee', 'parent')
                    OR (
                        status IN ('published','edited')
                        AND athlete_id IN (
                            SELECT id FROM athletes WHERE user_id = current_user_id()
                        )
                    )
                )
            )
            WITH CHECK (workspace_id = current_workspace_id())
        """
    )

    # assessment_scores: inherit visibility from parent.
    op.execute(
        """
        CREATE POLICY assessment_scores_inherit_parent ON assessment_scores
            USING (
                assessment_id IN (SELECT id FROM assessments)
            )
            WITH CHECK (
                assessment_id IN (SELECT id FROM assessments)
            )
        """
    )

    # assessment_edits: visible whenever the parent is.
    op.execute(
        """
        CREATE POLICY assessment_edits_inherit_parent ON assessment_edits
            USING (
                assessment_id IN (SELECT id FROM assessments)
            )
            WITH CHECK (
                assessment_id IN (SELECT id FROM assessments)
            )
        """
    )

    # feedbacks: coaches see workspace rows for their own assessments;
    # trainees/parents see rows they submitted.  Admin moderation goes
    # through a privileged path that bypasses RLS.
    op.execute(
        """
        CREATE POLICY feedback_access ON feedbacks
            USING (
                workspace_id = current_workspace_id()
                AND (
                    submitted_by_user_id = current_user_id()
                    OR (
                        COALESCE(current_workspace_role(), '') NOT IN ('trainee','parent')
                        AND assessment_id IN (
                            SELECT id FROM assessments
                            WHERE coach_id = current_user_id()
                               OR COALESCE(current_workspace_role(),'') = 'club_admin'
                        )
                    )
                )
            )
            WITH CHECK (
                workspace_id = current_workspace_id()
                AND submitted_by_user_id = current_user_id()
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feedbacks         CASCADE")
    op.execute("DROP TABLE IF EXISTS assessment_edits  CASCADE")
    op.execute("DROP TABLE IF EXISTS assessment_scores CASCADE")
    op.execute("DROP TABLE IF EXISTS assessments       CASCADE")

    # Restore the row-per-skill table (matches migrations 0003 + 0014).
    op.execute(
        """
        CREATE TABLE assessments (
            id                    UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id          UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            athlete_id            UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            coach_id              UUID NOT NULL REFERENCES users(id),
            session_id            UUID REFERENCES sessions(id) ON DELETE SET NULL,
            skill_id              UUID NOT NULL REFERENCES skills(id),
            level                 SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 5),
            note                  TEXT,
            recorded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            client_recorded_at    TIMESTAMPTZ,
            client_assessment_id  UUID,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_assessments_client_id ON assessments "
        "(client_assessment_id) WHERE client_assessment_id IS NOT NULL"
    )
