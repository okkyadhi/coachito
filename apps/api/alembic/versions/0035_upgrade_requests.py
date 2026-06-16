"""Track in-app upgrade requests from coaches.

Coachito doesn't have in-app payments at MVP — the plan picker in
Settings used to deep-link to WhatsApp, which scattered intent across
chats and made it impossible to see at a glance "who is asking to
upgrade".  This table collects those intents so the platform admin
sees a single queue on the admin overview and can reach back out
manually (the workspace owner's email is on the workspace row;
WhatsApp isn't stored anywhere yet).

Schema:
  - id              uuid PK
  - workspace_id    -> workspaces.id (CASCADE delete)
  - requested_plan  varchar(30) — FE plan code, e.g. 'club_pro' or
                    'solo_coach_unlimited'.  Not constrained against
                    an enum so adding a new FE-only display tier
                    doesn't require another migration.
  - requester_user_id -> users.id (SET NULL if the requester is
                    deleted later — we still want the queue intact)
  - status          varchar(20), default 'pending', currently one of
                    {pending, resolved, dismissed}
  - note            text — optional admin scratch note added on
                    resolution
  - created_at      timestamptz, default now()
  - resolved_at     timestamptz, nullable
  - resolved_by_user_id -> users.id (SET NULL on user delete)

Indexes:
  - (status, created_at desc) so the admin overview's "pending"
    filter is index-only.
  - workspace_id so dedup checks ("does this workspace already have
    a pending request?") are cheap.

No RLS — all writes go through workspace-scoped POST that sets
workspace_id from the JWT, all reads happen via the admin guard
which already runs with the admin DSN that bypasses RLS.

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upgrade_requests",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_plan", sa.String(30), nullable=False),
        sa.Column(
            "requester_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_upgrade_requests_status_created_at",
        "upgrade_requests",
        ["status", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_upgrade_requests_workspace_id",
        "upgrade_requests",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_upgrade_requests_workspace_id", table_name="upgrade_requests")
    op.drop_index(
        "ix_upgrade_requests_status_created_at", table_name="upgrade_requests"
    )
    op.drop_table("upgrade_requests")
