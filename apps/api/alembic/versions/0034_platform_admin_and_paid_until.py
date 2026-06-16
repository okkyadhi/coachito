"""Root admin dashboard — P0 foundation.

Adds:
  - ``users.is_platform_admin`` (bool, default false) — cross-tenant flag
    that grants access to the /admin/* endpoints.  Not exposed via signup
    or any self-service path; must be flipped by a DBA/operator.
  - ``workspaces.paid_until`` (timestamptz, nullable) — until this date
    the workspace is paid up.  Manually advanced by a platform admin via
    PATCH /admin/workspaces/{id} after each off-platform invoice payment.
    NULL means "no paid period recorded" (either pure trial or lapsed).

No backfill required; both defaults are correct for existing rows.

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-15
"""

import sqlalchemy as sa

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_platform_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column("paid_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "paid_until")
    op.drop_column("users", "is_platform_admin")
