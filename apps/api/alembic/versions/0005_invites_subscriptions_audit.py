"""Invites, subscriptions (billing prep), and audit log.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-11
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE invites (
            id              UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            email           CITEXT,
            phone_e164      VARCHAR(20),
            role            workspace_role NOT NULL,
            athlete_id      UUID        REFERENCES athletes(id) ON DELETE CASCADE,
            invite_code     VARCHAR(40) UNIQUE NOT NULL,
            invited_by_id   UUID        NOT NULL REFERENCES users(id),
            invited_user_id UUID        REFERENCES users(id),
            expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
            claimed_at      TIMESTAMPTZ,
            claimed_by_id   UUID        REFERENCES users(id),
            revoked_at      TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_invites_workspace     ON invites (workspace_id) WHERE claimed_at IS NULL AND revoked_at IS NULL")
    op.execute("CREATE INDEX idx_invites_email_pending ON invites (email)        WHERE claimed_at IS NULL AND revoked_at IS NULL AND email IS NOT NULL")

    op.execute("""
        CREATE TABLE subscriptions (
            id                   UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id         UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            plan                 VARCHAR(20) NOT NULL,
            status               VARCHAR(20) NOT NULL
                                 CHECK (status IN ('trial', 'active', 'past_due', 'cancelled')),
            current_period_start TIMESTAMPTZ,
            current_period_end   TIMESTAMPTZ,
            cancel_at            TIMESTAMPTZ,
            external_provider    VARCHAR(50),
            external_id          VARCHAR(255),
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_subscriptions_workspace ON subscriptions (workspace_id)")

    op.execute("""
        CREATE TABLE audit_log (
            id           UUID        PRIMARY KEY DEFAULT uuid_generate_v7(),
            workspace_id UUID        REFERENCES workspaces(id) ON DELETE SET NULL,
            user_id      UUID        REFERENCES users(id)      ON DELETE SET NULL,
            action       VARCHAR(80) NOT NULL,
            entity_type  VARCHAR(50),
            entity_id    UUID,
            metadata     JSONB,
            ip_address   INET,
            user_agent   TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_audit_workspace ON audit_log (workspace_id, created_at DESC)")
    op.execute("CREATE INDEX idx_audit_user      ON audit_log (user_id,      created_at DESC)")
    op.execute("CREATE INDEX idx_audit_entity    ON audit_log (entity_type, entity_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS subscriptions")
    op.execute("DROP TABLE IF EXISTS invites")
